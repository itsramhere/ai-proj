import React from "react";
import Spinner from "./Spinner";

export default function Button({
  children,
  variant = "primary",
  size = "md",
  loading = false,
  disabled = false,
  icon: Icon,
  iconPosition = "left",
  className = "",
  type = "button",
  onClick,
  ...props
}) {
  const baseClasses =
    "inline-flex items-center justify-center font-medium rounded-lg transition-all duration-150 cursor-pointer select-none focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-1 disabled:opacity-60 disabled:cursor-not-allowed disabled:pointer-events-none active:scale-[0.98]";

  const variantClasses = {
    primary:
      "bg-indigo-600 text-white hover:bg-indigo-700 shadow-sm shadow-indigo-600/20 focus-visible:ring-indigo-500 active:bg-indigo-800",
    secondary:
      "bg-slate-100 text-slate-800 hover:bg-slate-200 border border-slate-200 shadow-xs focus-visible:ring-slate-400 active:bg-slate-300",
    outline:
      "bg-transparent border border-slate-300 text-slate-700 hover:bg-slate-50 hover:border-slate-400 focus-visible:ring-slate-400",
    ghost:
      "bg-transparent text-slate-600 hover:bg-slate-100 hover:text-slate-900 focus-visible:ring-slate-400",
    danger:
      "bg-rose-600 text-white hover:bg-rose-700 shadow-sm shadow-rose-600/20 focus-visible:ring-rose-500 active:bg-rose-800",
    success:
      "bg-emerald-600 text-white hover:bg-emerald-700 shadow-sm shadow-emerald-600/20 focus-visible:ring-emerald-500 active:bg-emerald-800",
    warning:
      "bg-amber-500 text-white hover:bg-amber-600 shadow-sm shadow-amber-500/20 focus-visible:ring-amber-500 active:bg-amber-700",
  };

  const sizeClasses = {
    xs: "text-xs px-2.5 py-1 gap-1.5",
    sm: "text-xs px-3 py-1.5 gap-1.5",
    md: "text-sm px-4 py-2 gap-2",
    lg: "text-base px-5 py-2.5 gap-2.5 font-semibold",
  };

  const isLightSpinner = ["primary", "danger", "success", "warning"].includes(variant);

  return (
    <button
      type={type}
      disabled={disabled || loading}
      onClick={onClick}
      className={`${baseClasses} ${variantClasses[variant] || variantClasses.primary} ${sizeClasses[size] || sizeClasses.md} ${className}`}
      {...props}
    >
      {loading && <Spinner size={size === "lg" ? "md" : "xs"} light={isLightSpinner} />}
      {!loading && Icon && iconPosition === "left" && (
        <span className="shrink-0">{typeof Icon === "function" ? <Icon /> : Icon}</span>
      )}
      <span>{children}</span>
      {!loading && Icon && iconPosition === "right" && (
        <span className="shrink-0">{typeof Icon === "function" ? <Icon /> : Icon}</span>
      )}
    </button>
  );
}
