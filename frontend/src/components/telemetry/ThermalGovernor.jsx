import React, { useState } from "react";
import Card from "../ui/Card";
import Badge from "../ui/Badge";
import MetricChip from "../ui/MetricChip";
import ProgressBar from "../ui/ProgressBar";
import Button from "../ui/Button";
import { useToast } from "../../hooks/useToast";
import api from "../../api/client";

export default function ThermalGovernor({ thermal, onRefresh }) {
  const [spikeLoading, setSpikeLoading] = useState(false);
  const [stressLoading, setStressLoading] = useState(false);
  const { showToast } = useToast();

  if (!thermal) return null;

  const telemetry = thermal.telemetry || {};
  const isThrottled = thermal.state_index === 2;
  const isWarm = thermal.state_index === 1;

  const toggleSpike = async () => {
    setSpikeLoading(true);
    const newState = !telemetry.simulated;
    try {
      await api.post("/system/thermal/simulate-spike", { simulate: newState });
      showToast(
        newState ? "Simulated thermal spike activated (82.5°C)" : "Simulated thermal spike deactivated",
        newState ? "warning" : "info"
      );
      await new Promise((r) => setTimeout(r, 60));
      onRefresh?.();
    } catch (err) {
      console.error(err);
      showToast("Failed to toggle thermal spike.", "error");
    } finally {
      setSpikeLoading(false);
    }
  };

  const toggleStress = async () => {
    setStressLoading(true);
    const newState = !telemetry.physical_stress_active;
    try {
      await api.post("/system/thermal/physical-stress", { enabled: newState });
      showToast(
        newState ? "Physical hardware CPU stress burn started!" : "Hardware CPU stress burn stopped.",
        newState ? "warning" : "info"
      );
      await new Promise((r) => setTimeout(r, 60));
      onRefresh?.();
    } catch (err) {
      console.error(err);
      showToast("Failed to toggle hardware CPU stress test.", "error");
    } finally {
      setStressLoading(false);
    }
  };

  return (
    <Card
      variant="default"
      padding="md"
      className={`transition-all duration-300 border-2 ${
        isThrottled
          ? "border-rose-400 bg-rose-50/40"
          : isWarm
          ? "border-amber-300 bg-amber-50/30"
          : "border-slate-200 hover:border-slate-300 bg-white"
      }`}
    >
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2.5 pb-3 border-b border-slate-100">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-lg">🌡️</span>
          <h3 className="font-bold text-slate-900 text-sm tracking-wide">
            Thermal RL Governor (Option #2)
          </h3>
          <Badge
            variant={isThrottled ? "danger" : isWarm ? "warning" : "success"}
            size="xs"
            dot
            pulse={isThrottled || telemetry.physical_stress_active}
          >
            {telemetry.throttling_risk || "OPTIMAL_SAFE"}
          </Badge>
          {telemetry.physical_stress_active && (
            <Badge variant="warning" size="xs" dot pulse>
              Physical Burn Active
            </Badge>
          )}
        </div>

        <span className="text-[11px] text-slate-400 font-mono">
          ACPI Zone: \_tz.core_acpi
        </span>
      </div>

      <p className="text-xs text-slate-500 mt-2.5 mb-3 leading-relaxed">
        Monitors physical ACPI temperature sensors. A Q-learning RL policy dynamically selects model quantization tiers to mitigate hardware thermal throttling.
      </p>

      {/* Temperature Gauge */}
      <div className="mb-4 bg-slate-50 p-3 rounded-xl border border-slate-100">
        <ProgressBar
          value={telemetry.primary_temp_c || 48}
          min={35}
          max={100}
          variant="thermal"
          showLabels
          labelMin="Ambient 35°C"
          labelMid="Safe Limit 60°C • Throttle 75°C"
          labelMax="100°C Max"
        />
      </div>

      {/* Metrics Row */}
      <div className="flex flex-wrap items-center gap-2 mb-4">
        <MetricChip
          label="Core Temp"
          value={telemetry.primary_temp_c ?? "--"}
          unit="°C"
          variant={isThrottled ? "danger" : isWarm ? "warning" : "success"}
        />
        <MetricChip
          label="CPU Load"
          value={telemetry.cpu_load_percent ?? "--"}
          unit="%"
          variant={telemetry.cpu_load_percent > 80 ? "danger" : "neutral"}
        />
        <MetricChip
          label="RL Model"
          value={thermal.model_tier || "Qwen 3B"}
          variant="brand"
        />
      </div>

      {/* Action Buttons */}
      <div className="flex flex-wrap items-center gap-2 pt-3 border-t border-slate-100">
        <Button
          variant={telemetry.simulated ? "danger" : "secondary"}
          size="xs"
          loading={spikeLoading}
          onClick={toggleSpike}
        >
          {telemetry.simulated ? "🔥 Disable Spike Simulation" : "⚡ Simulate Thermal Throttling Spike"}
        </Button>

        <Button
          variant={telemetry.physical_stress_active ? "warning" : "outline"}
          size="xs"
          loading={stressLoading}
          onClick={toggleStress}
          title="Spins unthrottled matrix operations across CPU cores to genuinely elevate hardware temperatures"
        >
          {telemetry.physical_stress_active ? "🛑 Stop Physical CPU Burn" : "⚙️ Run Real Hardware CPU Stress"}
        </Button>
      </div>
    </Card>
  );
}
