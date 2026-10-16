import React, { useState } from "react";
import LectureCard from "./LectureCard";
import { LectureCardSkeleton } from "../ui/Skeleton";
import EmptyState from "../ui/EmptyState";
import Badge from "../ui/Badge";
import Button from "../ui/Button";

export default function LectureList({ lectures = [], loading = false, onRefresh }) {
  const [searchTerm, setSearchTerm] = useState("");

  const filteredLectures = lectures.filter((l) =>
    (l.title || "").toLowerCase().includes(searchTerm.toLowerCase()) ||
    (l.source_url || "").toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="mb-10">
      {/* Section Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-5 pb-3 border-b border-slate-200/80">
        <div className="flex items-center gap-2.5">
          <h2 className="text-lg font-bold text-slate-900 tracking-tight">Analyzed Lectures</h2>
          <Badge variant="neutral" size="sm">
            {lectures.length} Total
          </Badge>
        </div>

        <div className="flex items-center gap-2.5 w-full sm:w-auto">
          {/* Search filter if more than 3 lectures */}
          {lectures.length > 2 && (
            <div className="relative flex-1 sm:w-60">
              <input
                type="text"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                placeholder="Search lectures..."
                className="w-full pl-8 pr-3 py-1.5 text-xs bg-white border border-slate-200 rounded-lg text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
              <svg className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-2.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
            </div>
          )}

          {onRefresh && (
            <Button variant="ghost" size="sm" onClick={onRefresh} className="shrink-0 text-slate-600">
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
              Refresh
            </Button>
          )}
        </div>
      </div>

      {/* Content Grid */}
      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          <LectureCardSkeleton />
          <LectureCardSkeleton />
          <LectureCardSkeleton />
        </div>
      ) : filteredLectures.length === 0 ? (
        <EmptyState
          title={searchTerm ? "No matching lectures found" : "No lectures analyzed yet"}
          description={
            searchTerm
              ? `No lectures match "${searchTerm}". Try searching with a different keyword.`
              : "Paste a lecture URL into the form above to transcribe, generate notes, and create your first practice quiz."
          }
          actionText={searchTerm ? "Clear Search" : undefined}
          onAction={searchTerm ? () => setSearchTerm("") : undefined}
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {filteredLectures.map((lecture) => (
            <LectureCard key={lecture.id} lecture={lecture} />
          ))}
        </div>
      )}
    </div>
  );
}
