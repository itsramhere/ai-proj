import React, { useState } from "react";
import Card from "../ui/Card";
import Badge from "../ui/Badge";
import MetricChip from "../ui/MetricChip";
import Button from "../ui/Button";
import KeyframeModal from "./KeyframeModal";
import { useToast } from "../../hooks/useToast";
import api from "../../api/client";

export default function FrameGrabber({ framebuffer, snapshots = [], onRefresh }) {
  const [loading, setLoading] = useState(false);
  const [selectedSnapshot, setSelectedSnapshot] = useState(null);
  const { showToast } = useToast();

  if (!framebuffer) return null;

  const isActive = framebuffer.status === "STREAMING_ACTIVE";

  const handleToggleCapture = async () => {
    setLoading(true);
    try {
      if (isActive) {
        await api.post("/system/framebuffer/stop");
        showToast("Frame buffer grabber stopped.", "info");
      } else {
        await api.post("/system/framebuffer/start");
        showToast("Display frame buffer grabber active (simulating smart whiteboard stream)", "success");
      }
      await new Promise((r) => setTimeout(r, 60));
      onRefresh?.();
    } catch (err) {
      console.error(err);
      showToast("Failed to toggle frame grabber.", "error");
    } finally {
      setLoading(false);
    }
  };

  const handleNextSlide = async () => {
    try {
      await api.post("/system/framebuffer/next-slide");
      showToast("Slide advanced! New keyframe captured.", "info");
      setTimeout(onRefresh, 300);
    } catch (err) {
      console.error(err);
      showToast("Failed to advance slide.", "error");
    }
  };

  return (
    <>
      <Card variant="default" padding="md" className="border-2 border-slate-200 hover:border-slate-300 bg-white">
        {/* Top Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2.5 pb-3 border-b border-slate-100">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-lg">📺</span>
            <h3 className="font-bold text-slate-900 text-sm tracking-wide">
              Display Frame Buffer Grabber (Option #5)
            </h3>
            <Badge
              variant={isActive ? "success" : "neutral"}
              size="xs"
              dot
              pulse={isActive}
            >
              {framebuffer.status || "IDLE_STANDBY"}
            </Badge>
          </div>

          <span className="text-[11px] text-slate-400 font-mono">
            {framebuffer.resolution || "1280x720"} @ {framebuffer.frame_rate_fps || 30} FPS
          </span>
        </div>

        <p className="text-xs text-slate-500 mt-2.5 mb-3 leading-relaxed">
          Simulates hardware display frame buffer capture from projector/smart whiteboard HDMI registers, detecting slide changes and extracting visual bounding boxes without external cameras.
        </p>

        {/* Metrics Row */}
        <div className="flex flex-wrap items-center gap-2 mb-4">
          <MetricChip
            label="Bus Bandwidth"
            value={framebuffer.bus_bandwidth_mb_s?.toFixed(1) ?? "--"}
            unit="MB/s"
            variant={isActive ? "success" : "neutral"}
          />
          <MetricChip
            label="Grab Latency"
            value={framebuffer.frame_grab_latency_ms?.toFixed(1) ?? "--"}
            unit="ms"
            variant="neutral"
          />
          <MetricChip
            label="Keyframes"
            value={framebuffer.changes_detected_count ?? snapshots.length}
            variant="brand"
          />
        </div>

        {/* Action Controls */}
        <div className="flex flex-wrap items-center gap-2 pt-3 border-t border-slate-100">
          <Button
            variant={isActive ? "danger" : "primary"}
            size="xs"
            loading={loading}
            onClick={handleToggleCapture}
          >
            {isActive ? "⏹️ Stop Frame Buffer Capture" : "▶️ Start Live Frame Buffer Capture"}
          </Button>

          {isActive && (
            <Button
              variant="outline"
              size="xs"
              onClick={handleNextSlide}
              title="Simulates advancing to the next slide"
            >
              ⏭️ Advance Projector Slide
            </Button>
          )}
        </div>

        {/* Horizontal Filmstrip of Captured Keyframes */}
        {snapshots.length > 0 && (
          <div className="mt-4 pt-3 border-t border-slate-100">
            <div className="flex items-center justify-between text-xs text-slate-500 font-semibold mb-2">
              <span>Captured Keyframe Filmstrip ({snapshots.length})</span>
              <span className="text-[10px] text-slate-400">Click slide to inspect OCR & regions</span>
            </div>

            <div className="flex gap-3 overflow-x-auto pb-2 pt-1">
              {snapshots.map((snap) => (
                <div
                  key={snap.keyframe_id}
                  onClick={() => setSelectedSnapshot(snap)}
                  className="w-44 shrink-0 bg-slate-900 rounded-xl overflow-hidden border border-slate-200 hover:border-indigo-500 hover:shadow-md transition-all cursor-pointer group"
                >
                  <div className="relative aspect-video flex items-center justify-center bg-slate-950 overflow-hidden">
                    {snap.image_b64 ? (
                      <img
                        src={`data:image/jpeg;base64,${snap.image_b64}`}
                        alt={`Slide ${snap.keyframe_id}`}
                        className="w-full h-full object-cover group-hover:scale-105 transition-transform"
                      />
                    ) : (
                      <span className="text-slate-500 text-xs">No preview</span>
                    )}
                    <span className="absolute top-1 left-1 text-[9px] font-mono px-1.5 py-0.5 rounded bg-black/70 text-white backdrop-blur-xs">
                      #{snap.keyframe_id}
                    </span>
                    <span className="absolute top-1 right-1 text-[9px] font-mono px-1 py-0.5 rounded bg-indigo-600/90 text-white">
                      {snap.delta_percent?.toFixed(0)}% Δ
                    </span>
                  </div>

                  <div className="p-2 bg-white">
                    <p className="text-[11px] font-medium text-slate-800 truncate">
                      {snap.ocr_text || `Slide #${snap.keyframe_id}`}
                    </p>
                    <p className="text-[10px] text-slate-400 mt-0.5">
                      {snap.detected_regions?.length || 0} regions detected
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </Card>

      {/* Detail Modal */}
      <KeyframeModal
        snapshot={selectedSnapshot}
        isOpen={Boolean(selectedSnapshot)}
        onClose={() => setSelectedSnapshot(null)}
      />
    </>
  );
}
