"use client";
import { memo, useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Users, Clock, CheckCircle2, Zap } from "lucide-react";
import { cn } from "@/lib/utils";

/* ── Mock Data ──────────────────────────────────────────────────── */
const MOCK_STATS = {
  totalCandidates: 1248,
  pendingReview: 56,
  completed: 892,
  activeNow: 24,
};

/* ── Animated Counter ───────────────────────────────────────────── */
function useAnimatedCount(target, duration = 1200) {
  const [count, setCount] = useState(0);

  useEffect(() => {
    if (target === 0) {
      setCount(0);
      return;
    }

    let start = 0;
    const startTime = performance.now();

    function step(now) {
      const elapsed = now - startTime;
      const progress = Math.min(elapsed / duration, 1);
      // Ease-out cubic for satisfying deceleration
      const eased = 1 - Math.pow(1 - progress, 3);
      const current = Math.round(eased * target);

      setCount(current);
      if (progress < 1) {
        requestAnimationFrame(step);
      }
    }

    requestAnimationFrame(step);
  }, [target, duration]);

  return count;
}

/* ── Card Configuration ─────────────────────────────────────────── */
const CARD_CONFIG = [
  {
    key: "totalCandidates",
    label: "Total Candidates",
    icon: Users,
    // Blue theme
    gradient: "from-blue-500/20 via-blue-600/10 to-transparent",
    borderColor: "border-blue-500/20",
    iconBg: "bg-blue-500/15",
    iconColor: "text-blue-400",
    valueColor: "text-blue-50",
    glowColor: "rgba(59, 130, 246, 0.15)",
    accentDot: "bg-blue-400",
    tagline: "All registered candidates",
    emptyLabel: "No candidates yet",
  },
  {
    key: "pendingReview",
    label: "Pending Review",
    icon: Clock,
    // Amber / Yellow theme
    gradient: "from-amber-500/20 via-amber-600/10 to-transparent",
    borderColor: "border-amber-500/20",
    iconBg: "bg-amber-500/15",
    iconColor: "text-amber-400",
    valueColor: "text-amber-50",
    glowColor: "rgba(245, 158, 11, 0.15)",
    accentDot: "bg-amber-400",
    tagline: "Awaiting assessment",
    emptyLabel: "All reviewed!",
  },
  {
    key: "completed",
    label: "Completed",
    icon: CheckCircle2,
    // Green theme
    gradient: "from-emerald-500/20 via-emerald-600/10 to-transparent",
    borderColor: "border-emerald-500/20",
    iconBg: "bg-emerald-500/15",
    iconColor: "text-emerald-400",
    valueColor: "text-emerald-50",
    glowColor: "rgba(16, 185, 129, 0.15)",
    accentDot: "bg-emerald-400",
    tagline: "Successfully evaluated",
    emptyLabel: "None completed",
  },
  {
    key: "activeNow",
    label: "Active Now",
    icon: Zap,
    // Purple theme
    gradient: "from-violet-500/20 via-violet-600/10 to-transparent",
    borderColor: "border-violet-500/20",
    iconBg: "bg-violet-500/15",
    iconColor: "text-violet-400",
    valueColor: "text-violet-50",
    glowColor: "rgba(139, 92, 246, 0.15)",
    accentDot: "bg-violet-400",
    tagline: "Currently in interview",
    emptyLabel: "No active sessions",
  },
];

/* ── Single Stat Card ──────────────────────────────────────────── */
const containerVariants = {
  hidden: {},
  show: {
    transition: { staggerChildren: 0.08 },
  },
};

const cardVariants = {
  hidden: { opacity: 0, y: 24, scale: 0.96 },
  show: {
    opacity: 1,
    y: 0,
    scale: 1,
    transition: { type: "spring", stiffness: 260, damping: 24 },
  },
};

function StatCard({ config, value }) {
  const {
    label,
    icon: Icon,
    gradient,
    borderColor,
    iconBg,
    iconColor,
    valueColor,
    glowColor,
    accentDot,
    tagline,
    emptyLabel,
  } = config;

  const animatedValue = useAnimatedCount(value);
  const isZero = value === 0;
  const formattedValue = animatedValue.toLocaleString();

  return (
    <motion.div
      variants={cardVariants}
      whileHover={{ y: -4, scale: 1.02 }}
      whileTap={{ scale: 0.98 }}
      className="group relative"
    >
      {/* Glow effect on hover */}
      <div
        className="pointer-events-none absolute -inset-px rounded-xl opacity-0 blur-xl transition-opacity duration-500 group-hover:opacity-100"
        style={{ background: glowColor }}
      />

      <div
        className={cn(
          "relative overflow-hidden rounded-xl border bg-white/[0.03] backdrop-blur-xl",
          "p-5 transition-all duration-300",
          "hover:bg-white/[0.06] hover:shadow-lg",
          borderColor
        )}
      >
        {/* Background gradient accent */}
        <div
          className={cn(
            "pointer-events-none absolute inset-0 bg-gradient-to-br opacity-60",
            gradient
          )}
        />

        {/* Large faded icon watermark */}
        <div className="pointer-events-none absolute -bottom-3 -right-3 opacity-[0.04]">
          <Icon size={96} strokeWidth={1} />
        </div>

        {/* Content */}
        <div className="relative z-10">
          {/* Header row: icon + label */}
          <div className="flex items-center gap-3">
            <div
              className={cn(
                "flex h-10 w-10 items-center justify-center rounded-lg transition-transform duration-300 group-hover:scale-110",
                iconBg
              )}
            >
              <Icon size={20} className={cn(iconColor, "transition-colors")} />
            </div>
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-1.5">
                <div
                  className={cn(
                    "h-1.5 w-1.5 rounded-full",
                    accentDot,
                    config.key === "activeNow" && !isZero && "animate-pulse"
                  )}
                />
                <span className="text-xs font-medium uppercase tracking-wider text-zinc-400">
                  {label}
                </span>
              </div>
            </div>
          </div>

          {/* Value */}
          <div className="mt-4 flex items-baseline gap-2">
            <span
              className={cn(
                "text-3xl font-bold tabular-nums tracking-tight transition-colors",
                isZero ? "text-zinc-500" : valueColor
              )}
            >
              {formattedValue}
            </span>
          </div>

          {/* Tagline / Empty state */}
          <div className="mt-1.5">
            <span
              className={cn(
                "text-xs",
                isZero ? "text-zinc-600 italic" : "text-zinc-500"
              )}
            >
              {isZero ? emptyLabel : tagline}
            </span>
          </div>
        </div>
      </div>
    </motion.div>
  );
}

/* ── StatsCards Grid ────────────────────────────────────────────── */
function StatsCards({ data = MOCK_STATS, className }) {
  return (
    <motion.div
      variants={containerVariants}
      initial="hidden"
      animate="show"
      className={cn(
        "grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4",
        className
      )}
    >
      {CARD_CONFIG.map((config) => (
        <StatCard
          key={config.key}
          config={config}
          value={data[config.key] ?? 0}
        />
      ))}
    </motion.div>
  );
}

export default memo(StatsCards);
