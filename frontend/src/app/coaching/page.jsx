"use client";

import { Suspense } from "react";
import { useSearchParams } from "next/navigation";
import CoachingReport from "@/components/coaching/CoachingReport";

function CoachingPageContent() {
  const searchParams = useSearchParams();
  const sessionId = searchParams.get("session");

  return (
    <div className="space-y-6 animate-fade-in">
      <div>
        <h1 className="text-2xl font-semibold text-zinc-50">Coaching</h1>
        <p className="text-sm text-muted">
          Your interview performance, strengths, and personalized recommendations.
        </p>
      </div>
      <CoachingReport sessionId={sessionId} />
    </div>
  );
}

export default function CoachingPage() {
  return (
    <Suspense fallback={null}>
      <CoachingPageContent />
    </Suspense>
  );
}