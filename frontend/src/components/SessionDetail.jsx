"use client";

import { memo } from "react";
import useSWR from "swr";
import {
Activity,
Calendar,
Cpu,
Hash,
RefreshCw,
User,
Film,
Mic,
MessageSquare,
Clock,
} from "lucide-react";

import {
Dialog,
DialogContent,
DialogTitle,
} from "@/components/Dialog";
import Pipeline from "@/components/Pipeline";
import {
StatusBadge,
Badge,
} from "@/components/Badge";
import { Shimmer } from "@/components/Shimmer";
import { useAppStore } from "@/lib/store";
import {
formatDate,
riskColor,
formatRelative,
} from "@/lib/utils";
import { MomentTimeline } from "@/hooks/useMomentTracking";

function SessionDetailImpl({
sessionId,
onClose,
}) {
const token = useAppStore(
(state) => state.token
);

const open = sessionId !== null;

const {
data,
error,
isLoading,
mutate,
} = useSWR(
open && token
? `/session-status/${sessionId}`
: null,
{
refreshInterval: 2000,
}
);

const { data: momentsData } = useSWR(
open && token
? `/moments/${sessionId}`
: null,
{
refreshInterval: 5000,
}
);

return (
<Dialog
open={open}
onOpenChange={(isOpen) => {
if (!isOpen) {
onClose();
}
}}
> <DialogContent
     onClose={onClose}
     className="max-w-2xl"
   >
{/* ===================================================
HEADER
=================================================== */}


    <div className="border-b border-border px-5 py-4">
      <div className="flex items-center justify-between gap-4">
        <div className="min-w-0">
          <DialogTitle>
            Session detail
          </DialogTitle>

          <p className="mt-0.5 truncate font-mono text-xs text-muted">
            {sessionId}
          </p>
        </div>

        <div className="flex shrink-0 items-center gap-2">
          {data && (
            <StatusBadge
              status={data.status}
            />
          )}

          <button
            type="button"
            onClick={() => mutate()}
            className="rounded-md border border-border bg-bg-card p-1.5 text-muted transition-colors hover:border-accent/40 hover:bg-bg-panel hover:text-zinc-900 dark:hover:text-zinc-100"
            aria-label="Refresh session details"
            title="Refresh session details"
          >
            <RefreshCw
              size={12}
              aria-hidden="true"
            />
          </button>
        </div>
      </div>
    </div>

    {/* ===================================================
        CONTENT
        =================================================== */}

    <div className="p-5">
      {/* Error state */}

      {error && (
        <div
          role="alert"
          className="rounded-md border border-rose-500/30 bg-rose-500/10 p-3 text-sm text-rose-700 dark:text-rose-300"
        >
          Failed to load session
        </div>
      )}

      {/* Loading state */}

      {isLoading && !data && (
        <div className="space-y-3">
          <Shimmer className="h-12 w-full" />
          <Shimmer className="h-12 w-full" />
          <Shimmer className="h-20 w-full" />
        </div>
      )}

      {/* Session data */}

      {data && (
        <div className="space-y-5">
          {/* =============================================
              PIPELINE
              ============================================= */}

          <div>
            <SectionTitle>
              Pipeline
            </SectionTitle>

            <div className="mt-2 rounded-md border border-border bg-bg-card p-3">
              <Pipeline
                current={data.status}
              />
            </div>
          </div>

          {/* =============================================
              SESSION INFORMATION
              ============================================= */}

          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <Field
              label="Candidate"
              value={
                data.candidate_id ?? "—"
              }
              icon={User}
            />

            <Field
              label="Assigned worker"
              value={
                data.assigned_node ?? "—"
              }
              icon={Cpu}
            />

            <Field
              label="Created"
              value={formatDate(
                data.created_at ??
                  data.updated_at
              )}
              icon={Calendar}
            />

            <Field
              label="Started"
              value={formatRelative(
                data.start_time
              )}
              icon={Activity}
            />

            <Field
              label="Ended"
              value={formatRelative(
                data.end_time
              )}
              icon={Activity}
            />

            <Field
              label="Risk score"
              value={
                data.risk_score != null ? (
                  <Badge
                    variant={riskColor(
                      data.risk_score
                    )}
                  >
                    {data.risk_score.toFixed(
                      3
                    )}
                  </Badge>
                ) : (
                  "—"
                )
              }
              icon={Hash}
            />
          </div>

          {/* =============================================
              VIDEO ANALYSIS
              ============================================= */}

          {data.video_analysis && (
            <div>
              <SectionTitle>
                Video Analysis
              </SectionTitle>

              <div className="mt-2 grid grid-cols-1 gap-3 sm:grid-cols-2">
                {data.video_analysis
                  .confidence_score !=
                  null && (
                  <AnalysisField
                    label="Confidence"
                    icon={Film}
                  >
                    {(
                      data.video_analysis
                        .confidence_score *
                      100
                    ).toFixed(1)}
                    %
                  </AnalysisField>
                )}

                {data.video_analysis
                  .facial_expressions && (
                  <AnalysisField
                    label="Expression"
                    icon={Film}
                  >
                    {Object.entries(
                      data.video_analysis
                        .facial_expressions
                    )
                      .sort(
                        ([, a], [, b]) =>
                          b - a
                      )
                      .slice(0, 3)
                      .map(([key]) => key)
                      .join(", ") || "—"}
                  </AnalysisField>
                )}
              </div>
            </div>
          )}

          {/* =============================================
              AUDIO ANALYSIS
              ============================================= */}

          {data.audio_analysis && (
            <div>
              <SectionTitle>
                Audio Analysis
              </SectionTitle>

              <div className="mt-2 grid grid-cols-1 gap-3 sm:grid-cols-2">
                {data.audio_analysis
                  .sentiment && (
                  <AnalysisField
                    label="Sentiment"
                    icon={Mic}
                    className="capitalize"
                  >
                    {
                      data.audio_analysis
                        .sentiment
                    }
                  </AnalysisField>
                )}

                {data.audio_analysis
                  .clarity_score != null && (
                  <AnalysisField
                    label="Clarity"
                    icon={Mic}
                  >
                    {(
                      data.audio_analysis
                        .clarity_score *
                      100
                    ).toFixed(1)}
                    %
                  </AnalysisField>
                )}

                {data.audio_analysis
                  .speech_pace != null && (
                  <AnalysisField
                    label="Speech pace"
                    icon={Mic}
                  >
                    {
                      data.audio_analysis
                        .speech_pace
                    }{" "}
                    wpm
                  </AnalysisField>
                )}

                {data.audio_analysis
                  .filler_words != null && (
                  <AnalysisField
                    label="Filler words"
                    icon={Mic}
                  >
                    {
                      data.audio_analysis
                        .filler_words
                    }
                  </AnalysisField>
                )}
              </div>
            </div>
          )}

          {/* =============================================
              AI FEEDBACK
              ============================================= */}

          {data.ai_feedback && (
            <div>
              <SectionTitle>
                AI Feedback
              </SectionTitle>

              <div className="mt-2 rounded-md border border-border bg-bg-card px-3 py-2.5">
                <div className="flex items-start gap-2">
                  <MessageSquare
                    size={12}
                    aria-hidden="true"
                    className="mt-0.5 shrink-0 text-accent"
                  />

                  <p className="text-sm leading-relaxed text-zinc-700 dark:text-zinc-300">
                    {data.ai_feedback}
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* =============================================
              MOMENT TIMELINE
              ============================================= */}

          {momentsData?.moments
            ?.length > 0 && (
            <div>
              <h3 className="flex items-center gap-1.5 text-xs font-medium uppercase tracking-wide text-muted">
                <Clock
                  size={10}
                  aria-hidden="true"
                />

                <span>
                  Moment Timeline
                </span>
              </h3>

              <div className="mt-2 rounded-md border border-border bg-bg-card p-3">
                <MomentTimeline
                  moments={
                    momentsData.moments
                  }
                />
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  </DialogContent>
</Dialog>


);
}

/* =========================================================
SHARED SECTION TITLE
========================================================= */

function SectionTitle({ children }) {
return ( <h3 className="text-xs font-medium uppercase tracking-wide text-muted">
{children} </h3>
);
}

/* =========================================================
SESSION INFORMATION FIELD
========================================================= */

function Field({
label,
value,
icon: Icon,
}) {
return ( <div className="rounded-md border border-border bg-bg-card px-3 py-2.5 transition-colors duration-200"> <div className="flex items-center gap-1.5 text-[10px] uppercase tracking-wide text-muted"> <Icon
       size={10}
       aria-hidden="true"
     />

```
    <span>
      {label}
    </span>
  </div>

  <div className="mt-1 break-words text-sm text-zinc-800 dark:text-zinc-200">
    {value}
  </div>
</div>

);
}

/* =========================================================
VIDEO / AUDIO ANALYSIS FIELD
========================================================= */

function AnalysisField({
label,
icon: Icon,
children,
className = "",
}) {
return ( <div className="rounded-md border border-border bg-bg-card px-3 py-2.5 transition-colors duration-200"> <div className="flex items-center gap-1.5 text-[10px] uppercase tracking-wide text-muted"> <Icon
       size={10}
       aria-hidden="true"
     />

    <span>
      {label}
    </span>
  </div>

  <div
    className={`mt-1 text-sm text-zinc-800 dark:text-zinc-200 ${className}`}
  >
    {children}
  </div>
</div>


);
}

const SessionDetail = memo(
SessionDetailImpl
);

export default SessionDetail;
