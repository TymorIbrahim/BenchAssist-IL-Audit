"use client";

import { Suspense, useEffect, useState } from "react";
import Dashboard from "@/components/Dashboard";
import DetentionDashboard from "@/components/DetentionDashboard";
import { loadDashboardData, fetchManifest } from "@/lib/data";
import { loadDetentionDashboardData, isDetentionUseCase } from "@/lib/detentionData";

function DashboardRouter() {
  const [mode, setMode] = useState<"loading" | "detention" | "housing">("loading");

  useEffect(() => {
    fetchManifest().then((manifest) => {
      setMode(isDetentionUseCase(manifest) ? "detention" : "housing");
    });
  }, []);

  if (mode === "loading") {
    return (
      <div className="loading-screen">
        <p>Loading dashboard…</p>
      </div>
    );
  }

  return mode === "detention" ? (
    <Suspense fallback={<div className="loading-screen"><p>Loading detention audit dashboard…</p></div>}>
      <DetentionDashboard />
    </Suspense>
  ) : (
    <Suspense fallback={<div className="loading-screen"><p>Loading dashboard…</p></div>}>
      <Dashboard />
    </Suspense>
  );
}

export default function HomePage() {
  return (
    <DashboardRouter />
  );
}
