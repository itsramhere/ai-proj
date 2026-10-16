import React from "react";

export default function MetricChip({
  label,
  value,
  unit = "",
  icon: Icon,
  variant = "neutral",
  size = "md",
  className = "",
}) {
  const variantTextClasses = {
    neutral: "text-slate-900 font-bold",
    success: "text-emerald-700 font-bold",
    warning: "text-amber-700 font-bold",
    danger: "text-rose-700 font-bold",
    info: "text-blue-700 font-bold",
    brand: "text-indigo-700 font-bold",
  };

  const sizeClasses = {
    sm: "px-2.5 py-1 text-xs",
    md: "px-3 py-1.5 text-xs sm:text-[13px]",
    lg: "px-3.5 py-2 text-sm",
  };

  return (
    <div
      className={`inline-flex items-center gap-2 bg-white/95 rounded-xl border border-slate-200/90 shadow-2xs font-sans ${sizeClasses[size]} ${className}`}
    >
      {Icon && (
        <span className="text-slate-400 shrink-0">
          {typeof Icon === "function" ? <Icon /> : Icon}
        </span>
      )}
      <span className="text-slate-500 font-medium">{label}:</span>
      <span className={`font-mono ${variantTextClasses[variant] || variantTextClasses.neutral}`}>
        {value}
        {unit && <span className="ml-0.5 text-slate-500 font-sans text-xs font-normal">{unit}</span>}
      </span>
    </div>
  );
}
