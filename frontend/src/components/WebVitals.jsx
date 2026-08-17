"use client";

import { useEffect } from "react";
import { reportWebVitals } from "@/lib/webVitals";

export default function WebVitals() {
  useEffect(() => {
    reportWebVitals();
  }, []);

  return null;
}