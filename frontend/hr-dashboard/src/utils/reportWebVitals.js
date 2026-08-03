// frontend/hr-dashboard/src/utils/reportWebVitals.js
//
// Captures the 4 core web vitals (CLS, INP, LCP, TTFB) on page load and logs
// each metric as a structured JSON object.
//
// NOTE: There is no real backend ingestion endpoint yet. For now we log to
// the console in a parseable JSON format so metrics are visible in dev tools
// / can be scraped from log output. Swap the `logMetric` body for a
// `fetch('/api/metrics', ...)` call once a real endpoint exists — the rest
// of this file will not need to change.

import { onCLS, onINP, onLCP, onTTFB } from "web-vitals";

function logMetric(metric) {
  const payload = {
    type: "web-vital",
    name: metric.name, // 'CLS' | 'INP' | 'LCP' | 'TTFB'
    value: metric.value,
    rating: metric.rating, // 'good' | 'needs-improvement' | 'poor'
    id: metric.id,
    delta: metric.delta,
    navigationType: metric.navigationType,
    url: typeof window !== "undefined" ? window.location.href : undefined,
    timestamp: Date.now(),
  };

  // TODO: replace with a real ingestion call once the backend endpoint
  // exists, e.g.:
  //   fetch('/api/metrics', {
  //     method: 'POST',
  //     headers: { 'Content-Type': 'application/json' },
  //     body: JSON.stringify(payload),
  //     keepalive: true,
  //   }).catch(() => {});
  // eslint-disable-next-line no-console
  console.log(JSON.stringify(payload));
}

function reportWebVitals(onReport) {
  const handleMetric = (metric) => {
    logMetric(metric);
    if (typeof onReport === "function") {
      onReport(metric);
    }
  };

  onCLS(handleMetric);
  onINP(handleMetric);
  onLCP(handleMetric);
  onTTFB(handleMetric);
}

export default reportWebVitals;