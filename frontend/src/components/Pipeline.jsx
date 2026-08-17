"use client";
import { memo } from "react";
import { CheckCircle2, Clock, AlertCircle, Loader2, Film, Mic, BarChart3 } from "lucide-react";
import { cn } from "@/lib/utils";

const STAGES = [
  { status: "QUEUED", label: "Queued", icon: Clock },
  { status: "VIDEO_PROCESSING", label: "Video", icon: Film },
  { status: "AUDIO_PROCESSING", label: "Audio", icon: Mic },
  { status: "EVALUATING", label: "Evaluate", icon: BarChart3 },
  { status: "COMPLETED", label: "Done", icon: CheckCircle2 },
];

function stageIndex(s) {
  if (s === "CREATED") return -1;
  if (s === "QUEUED") return 0;
  if (s === "VIDEO_PROCESSING" || s === "PROCESSING") return 1;
  if (s === "AUDIO_PROCESSING") return 2;
  if (s === "EVALUATING") return 3;
  if (s === "COMPLETED") return 4;
  return -2;
}

function Pipeline({ current, className }) {
  const idx = stageIndex(current);
  const isFailed = current === "FAILED" || current === "TIMEOUT" || current === "CANCELLED";
  return (
    <div className={cn("flex items-center gap-1.5", className)}>
      {STAGES.map((stage, i) => {
        const reached = i <= idx;
        const active = i === idx && !isFailed;
        const isCurrentFailed = isFailed && i === idx;
        const Icon = isCurrentFailed ? AlertCircle : active ? Loader2 : stage.icon;
        return (
          <div key={stage.status} className="flex items-center gap-1.5">
            <div
              className={cn(
                "flex h-6 w-6 items-center justify-center rounded-full transition-colors",
                isCurrentFailed && "bg-rose-500/15 text-rose-400 ring-1 ring-rose-500/30",
                active && "bg-indigo-500/15 text-indigo-400 ring-1 ring-indigo-500/30",
                !reached && !active && !isCurrentFailed && "bg-bg-card text-muted",
                reached && !active && !isCurrentFailed && "bg-emerald-500/15 text-emerald-400",
              )}
            >
              <Icon size={12} className={active ? "animate-spin" : ""} />
            </div>
            {i < STAGES.length - 1 && (
              <div className={cn("h-px w-6 transition-colors", i < idx ? "bg-emerald-500/40" : "bg-border")} />
            )}
          </div>
        );
      })}
    </div>
  );
}

export default memo(Pipeline);
