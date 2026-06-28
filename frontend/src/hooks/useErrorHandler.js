"use client";
import { useCallback, useRef } from "react";
import { toast } from "@/lib/toast";

export function useErrorHandler() {
  const errorCountRef = useRef(new Map());

  const handleError = useCallback((error, context = {}) => {
    const { component, action, silent = false } = context;
    const errorKey = `${component || "unknown"}:${error?.message || "unknown"}`;

    const count = (errorCountRef.current.get(errorKey) || 0) + 1;
    errorCountRef.current.set(errorKey, count);

    if (count > 3) {
      return;
    }

    if (silent) {
      return;
    }

    const message = error?.message || String(error);
    const title = action ? `Failed to ${action}` : "Error";

    if (count === 1) {
      toast.error(title, message);
    } else if (count === 2) {
      toast.warn(title, `${message} (retrying)`);
    }

    if (process.env.NODE_ENV === "development") {
      console.error(`[ErrorBoundary] ${component || "unknown"}:`, error);
    }
  }, []);

  const clearErrors = useCallback(() => {
    errorCountRef.current.clear();
  }, []);

  return { handleError, clearErrors };
}

export function withErrorHandler(fn, context) {
  return async (...args) => {
    try {
      return await fn(...args);
    } catch (error) {
      const { handleError } = useErrorHandler.getState();
      handleError(error, context);
      throw error;
    }
  };
}
