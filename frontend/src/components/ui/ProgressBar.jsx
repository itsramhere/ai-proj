import React from "react";

export default function ProgressBar({
  value = 0,
  max = 100,
  min = 0,
  variant = "brand",
  size = "md",
  showLabels = false,
  labelMin,
  labelMid,
  labelMax,
  className = "",
}) {
  const percentage = Math.min(100, Math.max(0, ((value - min) / (max - min)) * 100));

  const variantBarClasses = {
    brand: "bg-indigo-600",
    success: "bg-emerald-500",
    warning: "bg-amber-500",
    danger: "bg-rose-500",
    thermal: percentage > 60 ? (percentage > 80 ? "bg-rose-600" : "bg-amber-500") : "bg-emerald-500",
    battery: percentage < 20 ? "bg-rose-600 animate-pulse" : (percentage < 45 ? "bg-amber-500" : "bg-emerald-500"),
  };

  const sizeClasses = {
    sm: "h-1.5",
    md: "h-2.5",
    lg: "h-3.5",
  };

  return (
    <div className={`w-full ${className}`}>
      {showLabels && (
        <div className="flex justify-between text-[11px] font-medium text-slate-500 mb-1.5 select-none">
          <span>{labelMin || `${min}`}</span>
          {labelMid && <span className="font-semibold">{labelMid}</span>}
          <span>{labelMax || `${max}`}</span>
        </div>
      )}
      <div className={`w-full bg-slate-200/80 rounded-full overflow-hidden ${sizeClasses[size] || sizeClasses.md}`}>
        <div
          role="progressbar"
          aria-valuenow={value}
          aria-valuemin={min}
          aria-valuemax={max}
          style={{ width: `${percentage}%` }}
          className={`h-full rounded-full transition-all duration-300 ease-out ${variantBarClasses[variant] || variantBarClasses.brand}`}
        />
      </div>
    </div>
  );
}
