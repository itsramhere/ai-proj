import React from "react";
import { Link } from "react-router-dom";
import Badge from "../ui/Badge";
import Button from "../ui/Button";

export default function LectureCard({ lecture }) {
  const formatDuration = (seconds) => {
    if (!seconds && seconds !== 0) return "--:--";
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}m ${secs.toString().padStart(2, "0")}s`;
  };

  const handleExportPDF = (e) => {
    e.preventDefault();
    window.open(`http://localhost:8000/lectures/${lecture.id}/export`, "_blank");
  };

  return (
    <div className="group bg-white rounded-2xl border border-slate-200/80 p-5 sm:p-6 shadow-xs hover:shadow-md hover:border-slate-300 transition-all duration-200 flex flex-col justify-between">
      <div>
        {/* Top meta tags */}
        <div className="flex items-center justify-between gap-2 mb-3">
          <Badge variant="brand" size="xs">
            Lecture #{lecture.id}
          </Badge>
          <div className="flex items-center gap-1.5 text-xs text-slate-500 font-medium">
            <svg className="w-3.5 h-3.5 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <span>{formatDuration(lecture.duration_sec)}</span>
          </div>
        </div>

        {/* Title */}
        <h3 className="text-base sm:text-lg font-bold text-slate-900 line-clamp-2 group-hover:text-indigo-600 transition-colors leading-snug">
          {lecture.title || "Untitled Lecture"}
        </h3>

        {/* Source link preview */}
        {lecture.source_url && (
          <p className="text-[11px] text-slate-400 truncate mt-1.5 max-w-full font-mono">
            {lecture.source_url}
          </p>
        )}
      </div>

      {/* Action Buttons Row */}
      <div className="mt-5 pt-4 border-t border-slate-100 flex items-center gap-2 flex-wrap">
        <Link to={`/lectures/${lecture.id}`} className="flex-1">
          <Button variant="primary" size="sm" className="w-full text-xs">
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
            </svg>
            View Notes
          </Button>
        </Link>

        <Link to={`/lectures/${lecture.id}/quiz`} className="flex-1">
          <Button variant="success" size="sm" className="w-full text-xs">
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
            </svg>
            Take Quiz
          </Button>
        </Link>

        <Button
          variant="outline"
          size="sm"
          onClick={handleExportPDF}
          title="Export PDF Notes"
          className="px-2.5 text-xs text-slate-600 hover:text-slate-900"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
          </svg>
        </Button>
      </div>
    </div>
  );
}
