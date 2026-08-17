"use client";
import { useState, useEffect, useRef, useCallback } from "react";

export function useMomentTracking(sessionId) {
  const [moments, setMoments] = useState([]);
  const [isTracking, setIsTracking] = useState(false);
  const [currentMoment, setCurrentMoment] = useState(null);
  const intervalRef = useRef(null);
  const startTimeRef = useRef(null);

  const startTracking = useCallback(() => {
    setIsTracking(true);
    startTimeRef.current = Date.now();
    setCurrentMoment({
      id: `moment_${Date.now()}`,
      startTime: Date.now(),
      type: "session_start",
      metadata: { sessionId },
    });
  }, [sessionId]);

  const stopTracking = useCallback(() => {
    setIsTracking(false);
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    if (currentMoment) {
      const finalMoment = {
        ...currentMoment,
        endTime: Date.now(),
        duration: Date.now() - currentMoment.startTime,
      };
      setMoments((prev) => [...prev, finalMoment]);
      setCurrentMoment(null);
    }
  }, [currentMoment]);

  const trackMoment = useCallback((type, metadata = {}) => {
    const now = Date.now();
    const moment = {
      id: `moment_${now}`,
      startTime: now,
      type,
      metadata,
    };
    setMoments((prev) => [...prev, moment]);
    return moment;
  }, []);

  const trackEvent = useCallback((eventType, data = {}) => {
    const event = {
      id: `event_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      timestamp: Date.now(),
      type: eventType,
      data,
    };
    setMoments((prev) => [...prev, { ...event, startTime: event.timestamp, endTime: event.timestamp }]);
    return event;
  }, []);

  useEffect(() => {
    if (!isTracking || !sessionId) return;
    intervalRef.current = setInterval(() => {
      setCurrentMoment((prev) => {
        if (!prev) return prev;
        return {
          ...prev,
          duration: Date.now() - prev.startTime,
        };
      });
    }, 1000);
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [isTracking, sessionId]);

  useEffect(() => {
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, []);

  const getTotalDuration = useCallback(() => {
    if (!startTimeRef.current) return 0;
    const lastMoment = moments[moments.length - 1];
    const endTime = lastMoment?.endTime || Date.now();
    return endTime - startTimeRef.current;
  }, [moments]);

  const getMomentByType = useCallback((type) => {
    return moments.filter((m) => m.type === type);
  }, [moments]);

  const getTimeline = useCallback(() => {
    return moments
      .sort((a, b) => a.startTime - b.startTime)
      .map((m, i) => ({
        ...m,
        index: i,
        percentage: startTimeRef.current
          ? ((m.startTime - startTimeRef.current) / (getTotalDuration() || 1)) * 100
          : 0,
      }));
  }, [moments, getTotalDuration]);

  return {
    moments,
    isTracking,
    currentMoment,
    startTracking,
    stopTracking,
    trackMoment,
    trackEvent,
    getTotalDuration,
    getMomentByType,
    getTimeline,
  };
}

export function MomentTimeline({ moments, className = "" }) {
  if (!moments || moments.length === 0) return null;

  const sorted = [...moments].sort((a, b) => a.startTime - b.startTime);
  const totalDuration = sorted[sorted.length - 1]?.endTime - sorted[0]?.startTime || 1;

  const getMomentColor = (type) => {
    const colors = {
      session_start: "bg-emerald-500",
      question_asked: "bg-blue-500",
      answer_received: "bg-purple-500",
      risk_detected: "bg-rose-500",
      ai_feedback: "bg-amber-500",
      screen_share: "bg-cyan-500",
      recording_start: "bg-red-500",
      recording_stop: "bg-zinc-500",
    };
    return colors[type] || "bg-zinc-500";
  };

  const formatDuration = (ms) => {
    if (ms < 1000) return `${ms}ms`;
    if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
    return `${Math.floor(ms / 60000)}m ${Math.floor((ms % 60000) / 1000)}s`;
  };

  return (
    <div className={`space-y-2 ${className}`}>
      <div className="flex items-center justify-between text-xs text-muted">
        <span>Timeline</span>
        <span>{formatDuration(totalDuration)}</span>
      </div>
      <div className="relative h-2 rounded-full bg-zinc-800 overflow-hidden">
        {sorted.map((moment, i) => {
          const start = ((moment.startTime - sorted[0].startTime) / totalDuration) * 100;
          const width = moment.endTime
            ? ((moment.endTime - moment.startTime) / totalDuration) * 100
            : 2;
          return (
            <div
              key={moment.id || i}
              className={`absolute h-full ${getMomentColor(moment.type)} opacity-80`}
              style={{ left: `${start}%`, width: `${Math.max(width, 0.5)}%` }}
              title={`${moment.type} - ${formatDuration(moment.duration || 0)}`}
            />
          );
        })}
      </div>
      <div className="flex flex-wrap gap-2 text-[10px]">
        {["session_start", "question_asked", "answer_received", "risk_detected", "ai_feedback"].map((type) => (
          <div key={type} className="flex items-center gap-1">
            <div className={`h-2 w-2 rounded-full ${getMomentColor(type)}`} />
            <span className="text-muted capitalize">{type.replace(/_/g, " ")}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
