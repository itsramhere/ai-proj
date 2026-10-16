import { useState, useEffect, useCallback } from "react";
import api from "../api/client";

export function useTelemetry(intervalMs = 1500) {
  const [thermal, setThermal] = useState(null);
  const [power, setPower] = useState(null);
  const [framebuffer, setFramebuffer] = useState(null);
  const [snapshots, setSnapshots] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchAll = useCallback(async () => {
    try {
      const [thermRes, pwrRes, fbRes] = await Promise.all([
        api.get("/system/thermal"),
        api.get("/system/power"),
        api.get("/system/framebuffer"),
      ]);

      setThermal(thermRes.data);
      setPower(pwrRes.data);
      setFramebuffer(fbRes.data);

      if (fbRes.data?.status === "STREAMING_ACTIVE" || (fbRes.data?.changes_detected_count || 0) > 0) {
        const snapRes = await api.get("/system/framebuffer/snapshots");
        setSnapshots(snapRes.data || []);
      }
    } catch (err) {
      console.error("Telemetry fetch error:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAll();
    const timer = setInterval(fetchAll, intervalMs);
    return () => clearInterval(timer);
  }, [fetchAll, intervalMs]);

  return {
    thermal,
    power,
    framebuffer,
    snapshots,
    loading,
    refresh: fetchAll,
  };
}
