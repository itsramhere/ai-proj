import React, { useState } from "react";
import Card from "../ui/Card";
import Button from "../ui/Button";
import { useToast } from "../../hooks/useToast";
import api from "../../api/client";

export default function VideoSubmitForm({ onSubmitted }) {
  const [url, setUrl] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [pipelineStatus, setPipelineStatus] = useState("");
  const [isProcessing, setIsProcessing] = useState(false);
  const { showToast } = useToast();

  const handleSubmit = async (e) => {
    e.preventDefault();
    const trimmed = url.trim();
    if (!trimmed) {
      showToast("Please enter a valid YouTube or video URL.", "warning");
      return;
    }

    setSubmitting(true);
    setPipelineStatus("Submitting video for processing...");
    setIsProcessing(true);

    try {
      await api.post("/analyze", { url: trimmed });
      showToast("Video processing started! Transcription and notes are generating.", "success");
      setPipelineStatus("Processing started in background! Notes and quiz will appear once complete.");
      setUrl("");
      onSubmitted?.();
    } catch (err) {
      console.error(err);
      const detail = err.response?.data?.detail || err.message || "Failed to submit video.";
      setPipelineStatus(`Error: ${detail}`);
      showToast(detail, "error");
      setIsProcessing(false);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Card variant="raised" padding="lg" className="mb-8 border-indigo-100 bg-gradient-to-b from-white to-slate-50/50">
      <div className="max-w-3xl">
        <div className="flex items-center gap-2 text-indigo-600 font-semibold text-xs tracking-wider uppercase mb-1">
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          Lecture Video Ingestion
        </div>

        <h2 className="text-xl sm:text-2xl font-extrabold text-slate-900 tracking-tight">
          Analyze Any Lecture Recording
        </h2>
        <p className="text-xs sm:text-sm text-slate-500 mt-1 mb-5">
          Paste a YouTube URL or direct video link. The edge pipeline transcribes audio via Whisper, detects slides with EasyOCR, formats Markdown study notes, and generates adaptive quizzes.
        </p>

        <form onSubmit={handleSubmit} className="flex flex-col sm:flex-row gap-3">
          <div className="relative flex-1">
            <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.75} d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
              </svg>
            </div>
            <input
              type="url"
              required
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="https://www.youtube.com/watch?v=... or lecture link"
              className="w-full pl-11 pr-4 py-3 bg-white border border-slate-300 rounded-xl text-sm text-slate-900 placeholder:text-slate-400 shadow-2xs focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-all"
              disabled={submitting}
            />
          </div>

          <Button
            type="submit"
            variant="primary"
            size="lg"
            loading={submitting}
            className="sm:w-auto shrink-0 shadow-md shadow-indigo-600/20"
          >
            {submitting ? "Submitting..." : "Analyze Lecture"}
          </Button>
        </form>

        {/* Live Processing Pipeline Stepper / Status */}
        {pipelineStatus && (
          <div className="mt-4 p-3.5 rounded-xl bg-indigo-50/80 border border-indigo-200/70 text-indigo-950 text-xs flex items-center justify-between gap-3 animate-in fade-in duration-200">
            <div className="flex items-center gap-2">
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-indigo-400 opacity-75" />
                <span className="relative inline-flex rounded-full h-2 w-2 bg-indigo-600" />
              </span>
              <span className="font-medium">{pipelineStatus}</span>
            </div>
            {isProcessing && (
              <span className="text-[11px] text-indigo-700 font-semibold shrink-0">
                Background Task Active
              </span>
            )}
          </div>
        )}
      </div>
    </Card>
  );
}
