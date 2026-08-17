"use client";

import { MetricsDashboard } from "@/components/analytics/MetricsDashboard";
import { ErrorBoundary } from "@/components/ErrorBoundary";

export default function Page() {
  return (
    <ErrorBoundary>
      <MetricsDashboard />
    </ErrorBoundary>
  );
}