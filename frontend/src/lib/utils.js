import { clsx } from "clsx";
function cn(...inputs) {
  return clsx(inputs);
}
function formatDate(iso) {
  if (!iso) return "\u2014";
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}
function formatRelative(iso) {
  if (!iso) return "\u2014";
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return iso;
  const diff = Date.now() - then;
  const abs = Math.abs(diff);
  const sec = Math.round(abs / 1e3);
  if (sec < 60) return diff >= 0 ? `${sec}s ago` : `in ${sec}s`;
  const min = Math.round(sec / 60);
  if (min < 60) return diff >= 0 ? `${min}m ago` : `in ${min}m`;
  const hr = Math.round(min / 60);
  if (hr < 24) return diff >= 0 ? `${hr}h ago` : `in ${hr}h`;
  const day = Math.round(hr / 24);
  return diff >= 0 ? `${day}d ago` : `in ${day}d`;
}
function formatPercent(n, digits = 1) {
  if (!Number.isFinite(n)) return "\u2014";
  return `${n.toFixed(digits)}%`;
}
function statusColor(status) {
  if (!status) return "muted";

  const s = status.toUpperCase();

  if (["SAFE", "COMPLETED", "HEALTHY"].includes(s))
    return "success";

  if (["LOW"].includes(s))
    return "accent";

  if (["WARNING", "CANCELLED", "DEGRADED"].includes(s))
    return "warn";

  if (["FLAGGED"].includes(s))
    return "warn";

  if (["HIGH", "FAILED", "TIMEOUT", "CRITICAL", "UNHEALTHY"].includes(s))
    return "danger";

  return "muted";
}

function riskColor(score) {
  if (score == null) return "muted";
  if (score >= 0.8) return "danger";
  if (score >= 0.6) return "warn";
  if (score >= 0.3) return "warn";
  return "success";
}
export {
  cn,
  formatDate,
  formatPercent,
  formatRelative,
  riskColor,
  statusColor
};
