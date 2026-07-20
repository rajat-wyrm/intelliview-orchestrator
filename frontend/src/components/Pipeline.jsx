"use client";

import { memo } from "react";
import {
CheckCircle2,
Clock,
AlertCircle,
Loader2,
Film,
Mic,
BarChart3,
} from "lucide-react";

import { cn } from "@/lib/utils";

const STAGES = [
{
status: "QUEUED",
label: "Queued",
icon: Clock,
},
{
status: "VIDEO_PROCESSING",
label: "Video",
icon: Film,
},
{
status: "AUDIO_PROCESSING",
label: "Audio",
icon: Mic,
},
{
status: "EVALUATING",
label: "Evaluate",
icon: BarChart3,
},
{
status: "COMPLETED",
label: "Done",
icon: CheckCircle2,
},
];

function stageIndex(status) {
if (status === "CREATED") {
return -1;
}

if (status === "QUEUED") {
return 0;
}

if (
status === "VIDEO_PROCESSING" ||
status === "PROCESSING"
) {
return 1;
}

if (status === "AUDIO_PROCESSING") {
return 2;
}

if (status === "EVALUATING") {
return 3;
}

if (status === "COMPLETED") {
return 4;
}

return -2;
}

function Pipeline({
current,
className,
}) {
const currentIndex = stageIndex(current);

const isFailed =
current === "FAILED" ||
current === "TIMEOUT" ||
current === "CANCELLED";

return (
<div
className={cn(
"flex items-center gap-1.5",
className
)}
role="list"
aria-label="Session processing progress"
>
{STAGES.map((stage, index) => {
const reached =
index <= currentIndex;

    const active =
      index === currentIndex &&
      !isFailed;

    /*
     * Failed statuses do not map directly to one of the
     * normal pipeline stages. When possible, mark the
     * current processing position as failed.
     */
    const isCurrentFailed =
      isFailed &&
      index === Math.max(
        currentIndex,
        0
      );

    const Icon = isCurrentFailed
      ? AlertCircle
      : active
        ? Loader2
        : stage.icon;

    let stateLabel = "Pending";

    if (isCurrentFailed) {
      stateLabel = "Failed";
    } else if (active) {
      stateLabel =
        current === "COMPLETED"
          ? "Completed"
          : "In progress";
    } else if (reached) {
      stateLabel = "Completed";
    }

    return (
      <div
        key={stage.status}
        className="flex items-center gap-1.5"
        role="listitem"
      >
        <div
          className={cn(
            "flex h-6 w-6 items-center justify-center",
            "rounded-full",
            "transition-colors duration-200",

            isCurrentFailed &&
              [
                "bg-rose-500/15",
                "text-rose-700",
                "ring-1 ring-rose-500/30",
                "dark:text-rose-400",
              ],

            active &&
              !isCurrentFailed &&
              [
                "bg-indigo-500/15",
                "text-indigo-700",
                "ring-1 ring-indigo-500/30",
                "dark:text-indigo-400",
              ],

            !reached &&
              !active &&
              !isCurrentFailed &&
              [
                "bg-bg-card",
                "text-zinc-500",
                "dark:text-zinc-400",
              ],

            reached &&
              !active &&
              !isCurrentFailed &&
              [
                "bg-emerald-500/15",
                "text-emerald-700",
                "dark:text-emerald-400",
              ]
          )}
          title={`${stage.label}: ${stateLabel}`}
          aria-label={`${stage.label}: ${stateLabel}`}
        >
          <Icon
            size={12}
            aria-hidden="true"
            className={
              active &&
              current !== "COMPLETED"
                ? "animate-spin"
                : ""
            }
          />
        </div>

        {index <
          STAGES.length - 1 && (
          <div
            aria-hidden="true"
            className={cn(
              "h-px w-6 transition-colors duration-200",
              index < currentIndex
                ? "bg-emerald-500/50 dark:bg-emerald-500/40"
                : "bg-border"
            )}
          />
        )}
      </div>
    );
  })}
</div>

);
}

export default memo(Pipeline);
