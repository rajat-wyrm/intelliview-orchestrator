import { onCLS, onFCP, onINP, onLCP, onTTFB } from "web-vitals";

export function reportWebVitals() {
  const logMetric = (metric) => {
    if (process.env.NODE_ENV === 'development') {
      console.log("Web Vital:", {
        name: metric.name,
        value: metric.value,
        rating: metric.rating,
        id: metric.id,
      });
    }

    // Optional: Send to backend API
    /*
    fetch("/api/web-vitals", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(metric),
    });
    */
  };

  onCLS(logMetric);
  onFCP(logMetric);
  onINP(logMetric);
  onLCP(logMetric);
  onTTFB(logMetric);
}