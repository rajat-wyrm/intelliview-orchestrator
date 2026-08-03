"use client";

import HRDashboard from "../../../../hr-dashboard/src/pages/HRDashboard";
import { ErrorBoundary } from "@/components/ErrorBoundary";

export default function Page() {
  return (
    <ErrorBoundary>
      <HRDashboard />
    </ErrorBoundary>
  );
}