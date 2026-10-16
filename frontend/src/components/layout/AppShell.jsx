import React, { useState, useEffect } from "react";
import { Link, NavLink } from "react-router-dom";
import api from "../../api/client";

export default function AppShell({ children }) {
  const [backendOnline, setBackendOnline] = useState(true);

  useEffect(() => {
    const checkHealth = async () => {
      try {
        await api.get("/system/thermal");
        setBackendOnline(true);
      } catch (err) {
        setBackendOnline(false);
      }
    };
    checkHealth();
    const timer = setInterval(checkHealth, 8000);
    return () => clearInterval(timer);
  }, []);

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col font-sans">
      {/* Sticky Glassmorphic Header */}
      <header className="sticky top-0 z-40 bg-white/90 backdrop-blur-md border-b border-slate-200/80 shadow-2xs">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between gap-4">
          {/* Logo & Brand */}
          <Link to="/" className="flex items-center gap-3 group shrink-0">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-indigo-600 to-indigo-500 text-white flex items-center justify-center shadow-sm shadow-indigo-600/30 group-hover:scale-105 transition-transform">
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-extrabold text-slate-900 tracking-tight text-base sm:text-lg">
                  AI Lecture Analyzer
                </span>
                <span className="hidden sm:inline-flex text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded-md bg-indigo-50 text-indigo-700 border border-indigo-200/60">
                  Edge AI
                </span>
              </div>
              <p className="text-[11px] text-slate-400 font-medium hidden md:block">
                On-Device Speech ASR • RL Thermal Governor • Biometric Quiz
              </p>
            </div>
          </Link>

          {/* Nav Items & System Health Status */}
          <div className="flex items-center gap-3 sm:gap-6">
            <nav className="flex items-center gap-1 sm:gap-2">
              <NavLink
                to="/"
                end
                className={({ isActive }) =>
                  `px-3 py-1.5 rounded-lg text-xs sm:text-sm font-semibold transition-all ${
                    isActive
                      ? "bg-indigo-50 text-indigo-700 font-bold"
                      : "text-slate-600 hover:text-slate-900 hover:bg-slate-100"
                  }`
                }
              >
                Dashboard
              </NavLink>
            </nav>

            {/* Live Backend Connection Indicator */}
            <div className="flex items-center gap-1.5 pl-3 border-l border-slate-200">
              <span className="relative flex h-2.5 w-2.5">
                {backendOnline && (
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
                )}
                <span
                  className={`relative inline-flex rounded-full h-2.5 w-2.5 ${
                    backendOnline ? "bg-emerald-500" : "bg-rose-500"
                  }`}
                />
              </span>
              <span className="text-[11px] font-semibold text-slate-500 hidden sm:inline">
                {backendOnline ? "FastAPI 8000" : "Offline"}
              </span>
            </div>
          </div>
        </div>
      </header>

      {/* Main View Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 sm:py-8">
        {children}
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-200 bg-white/60 py-6 text-center text-xs text-slate-500 font-medium">
        <div className="max-w-7xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-2">
          <span>AI Lecture Video Analyzer &copy; {new Date().getFullYear()}</span>
          <span className="text-slate-400 text-[11px]">
            Whisper ASR • LM Studio LLM • FAISS RAG • ACPI Thermal RL Governor
          </span>
        </div>
      </footer>
    </div>
  );
}
