import React from "react";

export default function Spinner({ size = "md", className = "", light = false }) {
  const sizeClasses = {
    xs: "w-3.5 h-3.5 border-2",
    sm: "w-4 h-4 border-2",
    md: "w-5 h-5 border-2",
    lg: "w-8 h-8 border-3",
  };

  const colorClasses = light
    ? "border-white/30 border-t-white"
    : "border-indigo-200 border-t-indigo-600";

  return (
    <div
      role="status"
      aria-label="Loading"
      className={`inline-block rounded-full animate-spin ${sizeClasses[size] || sizeClasses.md} ${colorClasses} ${className}`}
    />
  );
}
