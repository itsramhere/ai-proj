import React, { useState, useEffect, useCallback } from "react";
import PageHeader from "../components/layout/PageHeader";
import SectionHeader from "../components/layout/SectionHeader";
import VideoSubmitForm from "../components/lectures/VideoSubmitForm";
import LectureList from "../components/lectures/LectureList";
import ThermalGovernor from "../components/telemetry/ThermalGovernor";
import PowerGovernor from "../components/telemetry/PowerGovernor";
import FrameGrabber from "../components/telemetry/FrameGrabber";
import Badge from "../components/ui/Badge";
import { useTelemetry } from "../hooks/useTelemetry";
import api from "../api/client";

export default function Dashboard() {
  const [lectures, setLectures] = useState([]);
  const [lecturesLoading, setLecturesLoading] = useState(true);
  const [telemetryCollapsed, setTelemetryCollapsed] = useState(false);

  // Unified telemetry hook for thermal, battery, and framebuffer telemetry
  const { thermal, power, framebuffer, snapshots, refresh: refreshTelemetry } = useTelemetry(1500);

  const fetchLectures = useCallback(async () => {
    try {
      const res = await api.get("/lectures");
      setLectures(res.data || []);
    } catch (err) {
      console.error("Failed to fetch lectures:", err);
    } finally {
      setLecturesLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchLectures();
    // Poll lectures every 4s in case background analysis is underway
    const timer = setInterval(fetchLectures, 4000);
    return () => clearInterval(timer);
  }, [fetchLectures]);

  const activeGovernorsCount = [
    thermal?.telemetry?.simulated || thermal?.telemetry?.physical_stress_active,
    power?.simulated,
    framebuffer?.status === "STREAMING_ACTIVE",
  ].filter(Boolean).length;

  return (
    <div>
      {/* Top Page Header */}
      <PageHeader
        title="Dashboard"
        subtitle="Submit lecture recordings for on-device transcription, structured notes, visual diagrams, and adaptive quizzes."
        badge={
          <Badge variant="brand" size="sm" dot pulse>
            Local Engine Active
          </Badge>
        }
      />

      {/* 1. Core Feature: Lecture Ingestion Hero */}
      <VideoSubmitForm onSubmitted={fetchLectures} />

      {/* 2. Processed Lectures Section */}
      <LectureList
        lectures={lectures}
        loading={lecturesLoading}
        onRefresh={fetchLectures}
      />

      {/* 3. Edge Hardware Governors & Telemetry (Collapsible Section) */}
      <div className="pt-6 border-t border-slate-200/80">
        <SectionHeader
          title="Edge Hardware Governors & Real-Time Telemetry"
          subtitle="Physical ACPI thermal monitoring, battery core-pinning, and smart-board display frame buffer grabber."
          badge={
            activeGovernorsCount > 0 ? (
              <Badge variant="warning" size="xs" dot pulse>
                {activeGovernorsCount} Simulation Active
              </Badge>
            ) : (
              <Badge variant="success" size="xs">
                All Systems Normal
              </Badge>
            )
          }
          collapsible
          isCollapsed={telemetryCollapsed}
          onToggle={() => setTelemetryCollapsed((prev) => !prev)}
          className="mb-4 cursor-pointer select-none p-2 -mx-2 rounded-xl hover:bg-slate-100/60 transition-colors"
        />

        {!telemetryCollapsed && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-5 animate-in fade-in duration-200">
            <ThermalGovernor thermal={thermal} onRefresh={refreshTelemetry} />
            <PowerGovernor power={power} onRefresh={refreshTelemetry} />
            <FrameGrabber
              framebuffer={framebuffer}
              snapshots={snapshots}
              onRefresh={refreshTelemetry}
            />
          </div>
        )}
      </div>
    </div>
  );
}
