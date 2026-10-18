"""
Battery-Aware Continue/Stop Reinforcement Learning Trainer
==========================================================

Self-contained Q-learning simulation that trains an agent to decide whether a
battery-powered edge pipeline should CONTINUE processing its remaining workload
or STOP gracefully, based on exactly two observations:

    Observation 1: how much battery is left   (0-100 %)
    Observation 2: how much work is left      (0-100 units, % of pipeline remaining)

Action space:
    0 = CONTINUE : run one more processing step (drains battery, completes work)
    1 = STOP     : graceful shutdown / checkpoint (keeps battery, abandons work)

Episode termination (stochastic simulation, one step = one work quantum):
    * work reaches 0      -> SUCCESS            (+100, all work finished)
    * battery reaches 0   -> BATTERY_DEATH      (-100, work is lost mid-flight)
    * agent chooses STOP  -> GRACEFUL_STOP      (credit for battery kept,
                                                 penalty for work abandoned)

Because step cost, battery drain and work progress are random, the learned
policy is robust to realistic uncertainty in discharge rate and throughput.

Outputs (written next to this script):
    battery_rl_policy.json          trained Q-table + greedy policy + metadata
    battery_rl_training_curve.png   training diagnostics (if matplotlib available)

The saved JSON policy is consumed at runtime by backend/services/power_governor.py
to make the live continue/stop gating decision from battery % and remaining work;
delete the JSON to fall back to the rule-based heuristic.

Usage:
    python train_battery_rl.py
    python train_battery_rl.py --episodes 20000 --eval-episodes 2000 --seed 7
"""

from __future__ import annotations

import argparse
import json
import random
from collections import deque
from pathlib import Path

# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #

# Training
RANDOM_SEED = 42
EPISODES = 60_000
EVAL_EPISODES = 5_000
MAX_STEPS_PER_EPISODE = 400  # safety guard against pathological episodes
HISTORY_EVERY = 1_000        # record a history point every N episodes

# Discretisation: continuous observations are bucketed into a compact tabular
# state space so plain Q-learning converges fast and stays inspectable.
BATTERY_BIN_SIZE = 5.0                 # % per bin   -> 20 bins
WORK_BIN_SIZE = 5.0                    # units/bin   -> 20 bins
N_BATTERY_BINS = 20
N_WORK_BINS = 20

# Q-learning hyperparameters
ALPHA = 0.08            # learning rate
GAMMA = 0.99            # discount factor (long-horizon: success must not be
                        # discounted away just because it is several steps out)
EPSILON_START = 1.0     # initial exploration
EPSILON_MIN = 0.07      # exploration floor (keeps boundary cells well sampled)
EPSILON_DECAY = 0.9995  # per-episode multiplicative decay

# Lazy Q-table initialization. Q(continue) starts optimistic: its true value
# requires long backup chains from the +100 terminal reward, while Q(stop) is a
# single-step estimate that converges immediately. Without optimism the agent
# greedily stops early and starves itself of the trajectories it needs to learn
# when continuing is actually feasible.
Q_INIT_CONTINUE = 100.0
Q_INIT_STOP = 0.0

# Dyna-Q style experience replay: rare catastrophic transitions (battery death)
# are replayed a few extra times per step so their negative signal propagates
# back through the value chain quickly instead of waiting thousands of episodes.
REPLAY_BUFFER_SIZE = 4_000
REPLAY_UPDATES_PER_STEP = 6

# Rewards
SUCCESS_REWARD = 100.0          # finished all work before battery died
BATTERY_DEATH_PENALTY = -100.0  # battery died with work remaining (work lost)
STEP_COST = -0.5                # operational cost charged per processing step
STOP_CREDIT_PER_BATTERY_PCT = 1.0   # graceful stop preserves battery   -> credit
STOP_PENALTY_PER_WORK_UNIT = 0.5    # graceful stop must resume work later -> penalty
# Rationale for the stop weights: a graceful stop keeps ALL remaining battery
# for other tasks / a safe shutdown, while unfinished work can be resumed or
# re-done after charging. Battery death, by contrast, is catastrophic. The
# credit must exceed the marginal work value that 1% of battery can buy
# (~2.15 units * penalty/unit = ~1.08), otherwise the agent learns to burn the
# battery down to 0% instead of stopping early. Tuned against an exact
# value-iteration solution of this MDP; yields a diagonal stop boundary where
# success probability is no longer high.

# Simulated hardware dynamics (sampled fresh every CONTINUE step)
BATTERY_DRAIN_RANGE = (2.0, 4.5)    # % of battery consumed per step
WORK_PROGRESS_RANGE = (4.0, 10.0)   # work units completed per step

# Heuristic baseline mirroring PredictivePowerGovernor.evaluate_video_execution_budget:
# continue while estimated usable battery covers estimated remaining processing,
# including a small safety margin.
_AVG_DRAIN = sum(BATTERY_DRAIN_RANGE) / 2.0
_AVG_PROGRESS = sum(WORK_PROGRESS_RANGE) / 2.0
WORK_PER_BATTERY_PCT = _AVG_PROGRESS / _AVG_DRAIN  # ~2.15 work units per 1% battery
THRESHOLD_SAFETY_MARGIN = 1.15

# Actions
ACTION_CONTINUE = 0
ACTION_STOP = 1
ACTION_NAMES = {ACTION_CONTINUE: "continue", ACTION_STOP: "stop"}

SCRIPT_DIR = Path(__file__).resolve().parent
POLICY_PATH = SCRIPT_DIR / "battery_rl_policy.json"
PLOT_PATH = SCRIPT_DIR / "battery_rl_training_curve.png"


# --------------------------------------------------------------------------- #
# Observation discretisation
# --------------------------------------------------------------------------- #

def battery_bin(battery_pct: float) -> int:
    """Bucket a battery reading (0-100 %) into its discrete bin index."""
    return max(0, min(int(battery_pct // BATTERY_BIN_SIZE), N_BATTERY_BINS - 1))


def work_bin(work_left: float) -> int:
    """Bucket a work-remaining reading (0-100 units) into its discrete bin index."""
    return max(0, min(int(work_left // WORK_BIN_SIZE), N_WORK_BINS - 1))


def battery_center(b: int) -> float:
    """Representative battery % for a bin index (used by heuristic baselines)."""
    return (b + 0.5) * BATTERY_BIN_SIZE


def work_center(w: int) -> float:
    """Representative work value for a bin index (used by heuristic baselines)."""
    return (w + 0.5) * WORK_BIN_SIZE


# --------------------------------------------------------------------------- #
# Environment
# --------------------------------------------------------------------------- #

class BatteryWorkEnv:
    """
    Stochastic simulation of a battery-powered workload.

    One step = one processing quantum (e.g. one minute of pipeline execution).
    Each CONTINUE step consumes a random amount of battery and completes a
    random amount of work; each STOP step ends the episode with a graceful
    shutdown whose value depends on how much battery was saved versus how
    much work had to be abandoned.
    """

    def __init__(self, rng: random.Random):
        self.rng = rng
        self.battery = 100.0
        self.work_left = 100.0

    def reset(self) -> tuple[int, int]:
        """Start a fresh random episode and return the initial discrete state."""
        self.battery = self.rng.uniform(15.0, 100.0)
        self.work_left = self.rng.uniform(20.0, 100.0)
        return self.observe()

    def observe(self) -> tuple[int, int]:
        """Return the discretised (battery_bin, work_bin) observation."""
        return (battery_bin(self.battery), work_bin(self.work_left))

    def step(self, action: int) -> tuple[tuple[int, int], float, bool, dict]:
        """Advance the simulation. Returns (state, reward, done, info)."""
        if action == ACTION_STOP:
            # Graceful shutdown: keep whatever battery is left, but the
            # unfinished work is lost (or must be re-done after charging).
            reward = (
                STOP_CREDIT_PER_BATTERY_PCT * self.battery
                - STOP_PENALTY_PER_WORK_UNIT * self.work_left
            )
            return self.observe(), reward, True, {"outcome": "graceful_stop"}

        # CONTINUE: pay battery, make progress.
        self.battery = max(0.0, self.battery - self.rng.uniform(*BATTERY_DRAIN_RANGE))
        self.work_left -= self.rng.uniform(*WORK_PROGRESS_RANGE)

        if self.work_left <= 0:
            # Work finished (checked first so a step that finishes the final
            # chunk still succeeds even if the battery hit zero alongside it).
            self.work_left = 0.0
            return self.observe(), SUCCESS_REWARD, True, {"outcome": "success"}

        if self.battery <= 0:
            # Battery died mid-work: worst case, unfinished work is lost.
            return self.observe(), BATTERY_DEATH_PENALTY, True, {"outcome": "battery_death"}

        return self.observe(), STEP_COST, False, {"outcome": "running"}


# --------------------------------------------------------------------------- #
# Q-learning agent
# --------------------------------------------------------------------------- #

class QLearningAgent:
    """
    Tabular Q-learning agent over the discretised (battery, work) state space.

    Q-table: state (b, w) -> [Q(continue), Q(stop)]
    """

    def __init__(self, rng: random.Random):
        self.rng = rng
        self.q_table: dict[tuple[int, int], list[float]] = {}

    def q_values(self, state: tuple[int, int]) -> list[float]:
        """Return (and lazily initialise) the Q-values for a state."""
        return self.q_table.setdefault(state, [Q_INIT_CONTINUE, Q_INIT_STOP])

    def greedy_action(self, state: tuple[int, int]) -> int:
        """Deterministic best action; ties resolve toward CONTINUE."""
        q_continue, q_stop = self.q_values(state)
        return ACTION_CONTINUE if q_continue >= q_stop else ACTION_STOP

    def choose_action(self, state: tuple[int, int], epsilon: float) -> int:
        """Epsilon-greedy exploration during training."""
        if self.rng.random() < epsilon:
            return ACTION_CONTINUE if self.rng.random() < 0.5 else ACTION_STOP
        q_continue, q_stop = self.q_values(state)
        if q_continue == q_stop:  # unresolved tie -> explore randomly
            return ACTION_CONTINUE if self.rng.random() < 0.5 else ACTION_STOP
        return ACTION_CONTINUE if q_continue > q_stop else ACTION_STOP

    def update(
        self,
        state: tuple[int, int],
        action: int,
        reward: float,
        next_state: tuple[int, int],
        done: bool,
    ) -> None:
        """Standard Q-learning update: Q(s,a) += alpha * (target - Q(s,a))."""
        q = self.q_values(state)
        if done:
            target = reward
        else:
            target = reward + GAMMA * max(self.q_values(next_state))
        q[action] += ALPHA * (target - q[action])


# --------------------------------------------------------------------------- #
# Episode runner & evaluation
# --------------------------------------------------------------------------- #

def run_episode(env: BatteryWorkEnv, choose_action) -> dict:
    """Run a single episode with the given policy; env must be pre-configured."""
    state = env.observe()
    total_reward = 0.0

    for step_count in range(1, MAX_STEPS_PER_EPISODE + 1):
        action = choose_action(state)
        state, reward, done, info = env.step(action)
        total_reward += reward
        if done:
            return {
                "outcome": info["outcome"],
                "reward": total_reward,
                "steps": step_count,
                "battery_left": env.battery,
                "work_left": max(0.0, env.work_left),
            }

    return {
        "outcome": "timeout",
        "reward": total_reward,
        "steps": MAX_STEPS_PER_EPISODE,
        "battery_left": env.battery,
        "work_left": max(0.0, env.work_left),
    }


def threshold_decision(state: tuple[int, int]) -> int:
    """
    Heuristic baseline (mirrors the current rule-based power governor):
    continue while the battery comfortably covers the estimated work remaining.
    """
    b, w = state
    required_battery = (work_center(w) / WORK_PER_BATTERY_PCT) * THRESHOLD_SAFETY_MARGIN
    return ACTION_CONTINUE if battery_center(b) >= required_battery else ACTION_STOP


def evaluate_policy(name: str, choose_action, scenarios: list[tuple[float, float]]) -> dict:
    """Evaluate a policy over a fixed list of (battery, work) start scenarios."""
    counts = {"success": 0, "battery_death": 0, "graceful_stop": 0, "timeout": 0}
    sum_reward = sum_battery = sum_work_left = sum_steps = 0.0

    for i, (start_battery, start_work) in enumerate(scenarios):
        env = BatteryWorkEnv(random.Random(900_000 + i))  # identical dynamics per scenario
        env.battery = start_battery
        env.work_left = start_work
        result = run_episode(env, choose_action)

        counts[result["outcome"]] += 1
        sum_reward += result["reward"]
        sum_battery += result["battery_left"]
        sum_work_left += result["work_left"]
        sum_steps += result["steps"]

    n = len(scenarios)
    return {
        "name": name,
        "success_rate": counts["success"] / n,
        "death_rate": counts["battery_death"] / n,
        "stop_rate": (counts["graceful_stop"] + counts["timeout"]) / n,
        "avg_battery_left": sum_battery / n,
        "avg_work_left": sum_work_left / n,
        "avg_reward": sum_reward / n,
        "avg_steps": sum_steps / n,
    }


# --------------------------------------------------------------------------- #
# Reporting & artifacts
# --------------------------------------------------------------------------- #

def print_policy_map(agent: QLearningAgent) -> None:
    """Print the learned greedy policy as an ASCII battery x work map."""
    print()
    print("Learned policy map (greedy):")
    print("Battery left (%) -> higher = healthier")
    print("      " + "".join(f"{b * int(BATTERY_BIN_SIZE):>3d}" for b in range(N_BATTERY_BINS)))
    for w in reversed(range(N_WORK_BINS)):
        row = f"{w * int(WORK_BIN_SIZE):>4d} |"
        for b in range(N_BATTERY_BINS):
            action = agent.greedy_action((b, w))
            row += "  C" if action == ACTION_CONTINUE else "  S"
        print(row)
    print("Legend: C = CONTINUE processing | S = STOP (graceful shutdown + checkpoint)")
    print("Rows: work left (%), top row = most work remaining")


def print_sample_decisions(agent: QLearningAgent) -> None:
    """Show side-by-side decisions of the trained agent vs the heuristic rule."""
    samples = [
        (95.0, 30.0),
        (80.0, 60.0),
        (60.0, 95.0),
        (45.0, 80.0),
        (35.0, 70.0),
        (25.0, 60.0),
        (18.0, 85.0),
        (12.0, 50.0),
    ]
    print()
    print("Sample decisions (trained agent vs rule-based heuristic):")
    for battery, work in samples:
        state = (battery_bin(battery), work_bin(work))
        rl_action = agent.greedy_action(state)
        heur_action = threshold_decision(state)
        agree = "same" if rl_action == heur_action else "DIFFER"
        print(
            f"  battery {battery:5.1f}% | work {work:5.1f} left  ->  "
            f"RL: {ACTION_NAMES[rl_action].upper():8s} | "
            f"heuristic: {ACTION_NAMES[heur_action].upper():8s} ({agree})"
        )


def print_evaluation(results: list[dict]) -> None:
    """Print the comparison table of trained agent vs baselines."""
    print()
    print("Evaluation over identical random scenarios:")
    print(
        f"  {'Policy':<26} {'Success':>8} {'Stop':>8} {'BattDeath':>10} "
        f"{'AvgBatt':>8} {'AvgWorkLeft':>12} {'AvgReward':>10} {'AvgSteps':>9}"
    )
    print("  " + "-" * 106)
    for r in results:
        print(
            f"  {r['name']:<26} {100 * r['success_rate']:>7.1f}% {100 * r['stop_rate']:>7.1f}% "
            f"{100 * r['death_rate']:>9.1f}% {r['avg_battery_left']:>7.1f}% "
            f"{r['avg_work_left']:>11.1f} {r['avg_reward']:>10.1f} {r['avg_steps']:>9.1f}"
        )


def save_policy(agent: QLearningAgent, path: Path) -> None:
    """Persist the Q-table + greedy policy as JSON for later consumption."""
    policy = {}
    q_table = {}
    for (b, w), (q_continue, q_stop) in sorted(agent.q_table.items()):
        key = f"{b},{w}"
        policy[key] = agent.greedy_action((b, w))
        q_table[key] = [round(q_continue, 4), round(q_stop, 4)]

    payload = {
        "meta": {
            "description": "Q-learning policy: continue vs stop from (battery, work)",
            "actions": ACTION_NAMES,
            "battery_bin_size_pct": BATTERY_BIN_SIZE,
            "work_bin_size_units": WORK_BIN_SIZE,
            "n_battery_bins": N_BATTERY_BINS,
            "n_work_bins": N_WORK_BINS,
            "alpha": ALPHA,
            "gamma": GAMMA,
            "success_reward": SUCCESS_REWARD,
            "battery_death_penalty": BATTERY_DEATH_PENALTY,
            "step_cost": STEP_COST,
            "stop_credit_per_battery_pct": STOP_CREDIT_PER_BATTERY_PCT,
            "stop_penalty_per_work_unit": STOP_PENALTY_PER_WORK_UNIT,
            "battery_drain_range_pct_per_step": list(BATTERY_DRAIN_RANGE),
            "work_progress_range_units_per_step": list(WORK_PROGRESS_RANGE),
        },
        "policy": policy,
        "q_table": q_table,
    }
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)


def plot_training(history: dict, agent: QLearningAgent, path: Path) -> bool:
    """Save a training diagnostics figure. Returns False if matplotlib is unavailable."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import numpy as np
    except Exception:
        return False

    fig, axs = plt.subplots(1, 3, figsize=(16, 5), dpi=150)

    # (a) outcome rates over training
    ax = axs[0]
    ax.plot(history["episode"], [100 * s for s in history["success"]], label="Success", color="#10b981")
    ax.plot(history["episode"], [100 * d for d in history["death"]], label="Battery death", color="#e11d48")
    ax.plot(history["episode"], [100 * s for s in history["stop"]], label="Graceful stop", color="#f59e0b")
    ax.set_title("Outcome rates (2000-episode window)")
    ax.set_xlabel("Episode")
    ax.set_ylabel("%")
    ax.grid(True, linestyle="--", alpha=0.4)
    ax.legend(fontsize=8)

    # (b) epsilon decay
    ax = axs[1]
    ax.plot(history["episode"], history["epsilon"], color="#6366f1")
    ax.set_title("Exploration rate (epsilon)")
    ax.set_xlabel("Episode")
    ax.grid(True, linestyle="--", alpha=0.4)

    # (c) greedy policy heat map: Q(continue) - Q(stop)
    ax = axs[2]
    margins = np.zeros((N_WORK_BINS, N_BATTERY_BINS))
    for w in range(N_WORK_BINS):
        for b in range(N_BATTERY_BINS):
            q_continue, q_stop = agent.q_values((b, w))
            margins[w, b] = q_continue - q_stop
    im = ax.imshow(
        margins,
        origin="lower",
        cmap="coolwarm",
        extent=[0, 100, 0, 100],
        aspect="auto",
    )
    ax.set_title("Policy: Q(continue) - Q(stop)")
    ax.set_xlabel("Battery left (%)")
    ax.set_ylabel("Work left (units)")
    fig.colorbar(im, ax=ax, label="> 0 = continue | < 0 = stop")

    fig.suptitle("Battery/Work Q-Learning Training Diagnostics", fontweight="bold")
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    return True


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #

def train(episodes: int, seed: int) -> tuple[QLearningAgent, dict]:
    """Run epsilon-greedy Q-learning with replay; returns agent and history."""
    agent = QLearningAgent(random.Random(seed))
    env = BatteryWorkEnv(random.Random(seed + 1))
    epsilon = EPSILON_START

    recent_outcomes: deque = deque(maxlen=2_000)
    replay: deque = deque(maxlen=REPLAY_BUFFER_SIZE)
    history = {"episode": [], "success": [], "death": [], "stop": [], "epsilon": []}

    for episode in range(1, episodes + 1):
        state = env.reset()
        while True:
            action = agent.choose_action(state, epsilon)
            next_state, reward, done, info = env.step(action)

            # Real experience update...
            agent.update(state, action, reward, next_state, done)

            # ...plus Dyna-Q style replay of past transitions, which rapidly
            # propagates the rare battery-death penalty through the Q-table.
            replay.append((state, action, reward, next_state, done))
            for _ in range(REPLAY_UPDATES_PER_STEP):
                s, a, r, s2, d = replay[agent.rng.randrange(len(replay))]
                agent.update(s, a, r, s2, d)

            state = next_state
            if done:
                recent_outcomes.append(info["outcome"])
                break

        epsilon = max(EPSILON_MIN, epsilon * EPSILON_DECAY)

        if episode % HISTORY_EVERY == 0:
            n = len(recent_outcomes)
            history["episode"].append(episode)
            history["success"].append(sum(1 for o in recent_outcomes if o == "success") / n)
            history["death"].append(sum(1 for o in recent_outcomes if o == "battery_death") / n)
            history["stop"].append(sum(1 for o in recent_outcomes if o == "graceful_stop") / n)
            history["epsilon"].append(epsilon)

        if episode % 5_000 == 0:
            n = len(recent_outcomes)
            success_rate = 100 * sum(1 for o in recent_outcomes if o == "success") / n
            death_rate = 100 * sum(1 for o in recent_outcomes if o == "battery_death") / n
            print(
                f"[train] episode {episode:>6,} | epsilon {epsilon:.3f} | "
                f"success {success_rate:5.1f}% | battery-death {death_rate:5.1f}% (last {n} eps)",
                flush=True,
            )

    return agent, history


def main() -> None:
    parser = argparse.ArgumentParser(description="Train the battery/work continue-vs-stop RL agent.")
    parser.add_argument("--episodes", type=int, default=EPISODES, help="training episodes")
    parser.add_argument("--eval-episodes", type=int, default=EVAL_EPISODES, help="evaluation episodes")
    parser.add_argument("--seed", type=int, default=RANDOM_SEED, help="random seed")
    args = parser.parse_args()

    print("=" * 78)
    print(" Battery / Work Q-Learning Trainer (continue vs stop)")
    print("=" * 78)
    print(f" State space : {N_BATTERY_BINS} battery bins x {N_WORK_BINS} work bins "
          f"= {N_BATTERY_BINS * N_WORK_BINS} states")
    print(f" Actions     : continue / stop")
    print(f" Episodes    : {args.episodes:,} training | {args.eval_episodes:,} evaluation "
          f"| seed {args.seed}")
    print(f" Dynamics    : battery -{BATTERY_DRAIN_RANGE[0]}-{BATTERY_DRAIN_RANGE[1]}%/step, "
          f"work -{WORK_PROGRESS_RANGE[0]}-{WORK_PROGRESS_RANGE[1]} units/step")
    print("-" * 78)

    # 1. Train
    agent, history = train(args.episodes, args.seed)

    # 2. Inspect the learned policy
    print_policy_map(agent)
    print_sample_decisions(agent)

    # 3. Evaluate against baselines over identical scenarios
    eval_rng = random.Random(args.seed + 777)
    scenarios = [
        (eval_rng.uniform(15.0, 100.0), eval_rng.uniform(20.0, 100.0))
        for _ in range(args.eval_episodes)
    ]

    results = [
        evaluate_policy("Always continue (naive)", lambda s: ACTION_CONTINUE, scenarios),
        evaluate_policy("Rule-based heuristic", threshold_decision, scenarios),
        evaluate_policy("Q-Learning agent (trained)", agent.greedy_action, scenarios),
    ]
    print_evaluation(results)

    trained = results[-1]
    heuristic = results[1]
    print()
    print(
        f" Trained agent vs heuristic: success "
        f"{100 * (trained['success_rate'] - heuristic['success_rate']):+.1f} pp, "
        f"battery deaths {100 * (trained['death_rate'] - heuristic['death_rate']):+.1f} pp"
    )

    # 4. Persist artifacts
    save_policy(agent, POLICY_PATH)
    print(f"\nSaved policy -> {POLICY_PATH}")

    if plot_training(history, agent, PLOT_PATH):
        print(f"Saved training plot -> {PLOT_PATH}")
    else:
        print("matplotlib not available - skipped training plot.")


if __name__ == "__main__":
    main()
