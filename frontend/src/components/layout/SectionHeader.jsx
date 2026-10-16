import React from "react";

export default function SectionHeader({
  icon: Icon,
  title,
  subtitle,
  badge,
  action,
  collapsible = false,
  isCollapsed = false,
  onToggle,
  className = "",
}) {
  return (
    <div
      className={`flex items-center justify-between gap-3 ${className}`}
      onClick={collapsible && onToggle ? onToggle : undefined}
    >
      <div className="flex items-center gap-2.5">
        {Icon && (
          <div className="w-8 h-8 rounded-xl bg-slate-100 flex items-center justify-center text-slate-700 shrink-0">
            {typeof Icon === "function" ? <Icon /> : Icon}
          </div>
        )}
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-base sm:text-lg font-bold text-slate-900 tracking-tight">{title}</h2>
            {badge && <div className="shrink-0">{badge}</div>}
          </div>
          {subtitle && <p className="text-xs text-slate-500 mt-0.5">{subtitle}</p>}
        </div>
      </div>

      <div className="flex items-center gap-2 shrink-0">
        {action}
        {collapsible && (
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              onToggle?.();
            }}
            className="p-1 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-colors cursor-pointer"
            aria-label={isCollapsed ? "Expand section" : "Collapse section"}
          >
            <svg
              className={`w-5 h-5 transition-transform duration-200 ${isCollapsed ? "-rotate-90" : "rotate-0"}`}
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </button>
        )}
      </div>
    </div>
  );
}
