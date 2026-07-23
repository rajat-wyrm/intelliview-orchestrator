"use client";
import { Skeleton } from "@/components/States";

function DashboardSkeleton() {
  return (
    <div className="space-y-3 rounded-xl border border-border bg-bg-panel p-4">
      <Skeleton className="h-10 w-full" />
      <Skeleton className="h-10 w-full" />
      <Skeleton className="h-10 w-full" />
      <Skeleton className="h-10 w-3/4" />
    </div>
  );
}

export default DashboardSkeleton;