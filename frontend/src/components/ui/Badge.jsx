import React from "react";

export default function Badge({
  children,
  variant = "neutral",
  size = "sm",
  dot = false,
  pulse = false,
  className = "",
}) {
  const variantClasses = {
    neutral: "bg-slate-100 text-slate-700 border-slate-200",
    slate: "bg-slate-800 text-slate-100 border-slate-700",
    success: "bg-emerald-50 text-emerald-700 border-emerald-200",
    warning: "bg-amber-50 text-amber-800 border-amber-200",
    danger: "bg-rose-50 text-rose-700 border-rose-200",
    info: "bg-blue-50 text-blue-700 border-blue-200",
    purple: "bg-purple-50 text-purple-700 border-purple-200",
    brand: "bg-indigo-50 text-indigo-700 border-indigo-200",
  };

  const dotColorClasses = {
    neutral: "bg-slate-500",
    slate: "bg-slate-300",
    success: "bg-emerald-500",
    warning: "bg-amber-500",
    danger: "bg-rose-500",
    info: "bg-blue-500",
    purple: "bg-purple-500",
    brand: "bg-indigo-500",
  };

  const sizeClasses = {
    xs: "text-[10px] px-1.5 py-0.5 font-medium gap-1",
    sm: "text-xs px-2.5 py-0.5 font-medium gap-1.5",
    md: "text-xs px-3 py-1 font-semibold gap-1.5",
  };

  return (
    <span
      className={`inline-flex items-center rounded-full border shadow-2xs tracking-wide shrink-0 ${variantClasses[variant] || variantClasses.neutral} ${sizeClasses[size] || sizeClasses.sm} ${className}`}
    >
      {dot && (
        <span className="relative flex h-2 w-2">
          {pulse && (
            <span
              className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${dotColorClasses[variant] || dotColorClasses.neutral}`}
            />
          )}
          <span
            className={`relative inline-flex rounded-full h-2 w-2 ${dotColorClasses[variant] || dotColorClasses.neutral}`}
          />
        </span>
      )}
      {children}
    </span>
  );
}
