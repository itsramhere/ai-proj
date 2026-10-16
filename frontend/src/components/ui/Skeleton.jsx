import React from "react";

export default function Skeleton({ className = "", variant = "rect" }) {
  const variantClasses = {
    rect: "rounded-lg",
    card: "rounded-2xl",
    circle: "rounded-full",
    text: "rounded h-4 w-full",
  };

  return (
    <div
      className={`animate-pulse bg-slate-200/80 ${variantClasses[variant] || variantClasses.rect} ${className}`}
    />
  );
}

export function LectureCardSkeleton() {
  return (
    <div className="bg-white rounded-2xl border border-slate-200/80 p-5 shadow-xs space-y-3">
      <div className="flex items-center justify-between">
        <Skeleton className="w-16 h-5" variant="rect" />
        <Skeleton className="w-20 h-5" variant="rect" />
      </div>
      <Skeleton className="w-3/4 h-6" variant="rect" />
      <Skeleton className="w-full h-4" variant="text" />
      <div className="flex items-center gap-2 pt-2 border-t border-slate-100">
        <Skeleton className="w-24 h-8" variant="rect" />
        <Skeleton className="w-24 h-8" variant="rect" />
        <Skeleton className="w-20 h-8" variant="rect" />
      </div>
    </div>
  );
}
