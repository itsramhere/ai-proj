import React, { useState } from "react";
import Card from "../ui/Card";
import Badge from "../ui/Badge";
import MetricChip from "../ui/MetricChip";
import ProgressBar from "../ui/ProgressBar";
import Button from "../ui/Button";
import { useToast } from "../../hooks/useToast";
import api from "../../api/client";

export default function PowerGovernor({ power, onRefresh }) {
  const [loading, setLoading] = useState(false);
  const { showToast } = useToast();

  if (!power) return null;

  const isCritical = power.power_mode === "POWER_MODE_GATED" || (power.battery_percent && power.battery_percent < 20);

  const toggleDischarge = async () => {
    setLoading(true);
    const newState = !power.simulated;
    try {
      await api.post("/system/power/simulate-discharge", { simulate: newState });
      showToast(
        newState ? "Battery discharge simulation enabled (14% on battery, core power-gated)" : "Battery discharge simulation disabled",
        newState ? "warning" : "info"
      );
      await new Promise((r) => setTimeout(r, 60));
      onRefresh?.();
    } catch (err) {
      console.error(err);
      showToast("Failed to toggle simulated discharge.", "error");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card
      variant="default"
      padding="md"
      className={`transition-all duration-300 border-2 ${
        isCritical
          ? "border-amber-300 bg-amber-50/30"
          : "border-slate-200 hover:border-slate-300 bg-white"
      }`}
    >
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2.5 pb-3 border-b border-slate-100">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-lg">🔋</span>
          <h3 className="font-bold text-slate-900 text-sm tracking-wide">
            Battery & Core Affinity Governor (Option #8)
          </h3>
          <Badge
            variant={isCritical ? "warning" : "success"}
            size="xs"
            dot
            pulse={isCritical}
          >
            {power.power_mode || "AC_MAINS_OPTIMAL"}
          </Badge>
          {power.allow_heavy_ocr === false && (
            <Badge variant="danger" size="xs">
              Vision Power-Gated
            </Badge>
          )}
        </div>

        <span className="text-[11px] text-slate-400 font-mono">
          Affinity: {power.active_core_mask ? `Cores [${power.active_core_mask.join(",")}]` : "All Cores"}
        </span>
      </div>

      <p className="text-xs text-slate-500 mt-2.5 mb-3 leading-relaxed">
        Pins compute workloads to energy-efficient CPU silicon cores and gates heavy slide vision on low battery to guarantee quiz downloads before power loss.
      </p>

      {/* Battery Gauge */}
      <div className="mb-4 bg-slate-50 p-3 rounded-xl border border-slate-100">
        <ProgressBar
          value={power.battery_percent ?? 100}
          min={0}
          max={100}
          variant="battery"
          showLabels
          labelMin="0% Critical"
          labelMid={power.power_plugged ? "⚡ AC Connected" : "🔋 Discharging on Battery"}
          labelMax="100% Full"
        />
      </div>

      {/* Metrics Row */}
      <div className="flex flex-wrap items-center gap-2 mb-4">
        <MetricChip
          label="Battery Level"
          value={power.battery_percent !== null ? `${power.battery_percent}%` : "AC Power"}
          variant={isCritical ? "danger" : "success"}
        />
        <MetricChip
          label="Power Source"
          value={power.power_plugged ? "AC Wall Mains" : "Internal Battery"}
          variant="neutral"
        />
        <MetricChip
          label="Silicon Affinity"
          value={power.active_core_mask ? `${power.active_core_mask.length} Cores` : "All Cores"}
          variant="brand"
        />
        {power.rl_policy_loaded && (
          <MetricChip
            label="RL Governor"
            value={`Q-learning · ${power.rl_policy_states} states`}
            variant="brand"
          />
        )}
      </div>

      {/* Action Button */}
      <div className="flex items-center gap-2 pt-3 border-t border-slate-100">
        <Button
          variant={power.simulated ? "warning" : "secondary"}
          size="xs"
          loading={loading}
          onClick={toggleDischarge}
        >
          {power.simulated ? "⚡ Restore AC Mains Power" : "🔋 Simulate Battery Discharge (<15%)"}
        </Button>
      </div>
    </Card>
  );
}
