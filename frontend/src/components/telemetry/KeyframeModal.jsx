import React from "react";
import Modal from "../ui/Modal";
import Badge from "../ui/Badge";
import Button from "../ui/Button";

export default function KeyframeModal({ snapshot, isOpen, onClose }) {
  if (!snapshot) return null;

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={`Keyframe #${snapshot.keyframe_id} Details`}
      subtitle={`Captured at ${snapshot.timestamp_s?.toFixed(1) || 0}s • Visual Delta: ${(snapshot.delta_percent || 0).toFixed(1)}%`}
      maxWidth="max-w-3xl"
      footer={
        <Button variant="secondary" size="sm" onClick={onClose}>
          Close Inspector
        </Button>
      }
    >
      <div className="space-y-5">
        {/* Rendered Slide Image */}
        {snapshot.image_b64 ? (
          <div className="rounded-xl overflow-hidden border border-slate-200 bg-slate-900 flex items-center justify-center max-h-96 shadow-inner">
            <img
              src={`data:image/jpeg;base64,${snapshot.image_b64}`}
              alt={`Keyframe ${snapshot.keyframe_id}`}
              className="max-h-96 w-auto object-contain"
            />
          </div>
        ) : (
          <div className="h-48 rounded-xl bg-slate-100 flex items-center justify-center text-slate-400 text-xs">
            No image data available
          </div>
        )}

        {/* Detected Visual Regions */}
        <div>
          <h4 className="text-xs font-bold text-slate-700 uppercase tracking-wider mb-2">
            Detected Visual Regions ({snapshot.detected_regions?.length || 0})
          </h4>
          <div className="flex flex-wrap gap-1.5 max-h-24 overflow-y-auto">
            {(snapshot.detected_regions || []).map((r, i) => (
              <Badge
                key={i}
                variant={
                  r.type === "diagram_figure"
                    ? "warning"
                    : r.type === "formula_column"
                    ? "purple"
                    : "success"
                }
                size="xs"
              >
                {r.type}: {r.bbox?.[2]}x{r.bbox?.[3]}px @ [{r.bbox?.[0]},{r.bbox?.[1]}]
              </Badge>
            ))}
          </div>
        </div>

        {/* Extracted Frame Buffer OCR Text */}
        <div>
          <h4 className="text-xs font-bold text-slate-700 uppercase tracking-wider mb-2">
            Frame Buffer OCR Extraction
          </h4>
          <div className="p-3 bg-slate-900 text-slate-100 rounded-xl font-mono text-xs max-h-36 overflow-y-auto leading-relaxed border border-slate-800">
            {snapshot.ocr_text || "No legible text detected on this frame buffer slide."}
          </div>
        </div>
      </div>
    </Modal>
  );
}
