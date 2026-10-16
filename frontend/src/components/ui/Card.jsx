import React from "react";

export default function Card({
  children,
  className = "",
  variant = "default",
  padding = "md",
  onClick,
  ...props
}) {
  const variantClasses = {
    default: "bg-white border border-slate-200/80 shadow-xs",
    raised: "bg-white border border-slate-200/70 shadow-md shadow-slate-900/5",
    bordered: "bg-white border-2 border-slate-200",
    subtle: "bg-slate-50/70 border border-slate-200/60",
    interactive:
      "bg-white border border-slate-200/80 shadow-xs hover:shadow-md hover:border-slate-300 transition-all duration-200 cursor-pointer active:scale-[0.995]",
  };

  const paddingClasses = {
    none: "",
    sm: "p-3 sm:p-4",
    md: "p-4 sm:p-6",
    lg: "p-6 sm:p-8",
  };

  return (
    <div
      onClick={onClick}
      className={`rounded-2xl ${variantClasses[variant] || variantClasses.default} ${paddingClasses[padding]} ${className}`}
      {...props}
    >
      {children}
    </div>
  );
}

export function CardHeader({ title, subtitle, action, className = "" }) {
  return (
    <div className={`flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 mb-4 border-b border-slate-100 ${className}`}>
      <div>
        <h3 className="text-base sm:text-lg font-bold text-slate-900 tracking-tight">{title}</h3>
        {subtitle && <p className="text-xs text-slate-500 mt-0.5 leading-relaxed">{subtitle}</p>}
      </div>
      {action && <div className="shrink-0">{action}</div>}
    </div>
  );
}
