"use client";
import Input from './Input';
import { useState, useEffect, useCallback } from "react";
import { Lock, Unlock, Eye, EyeOff } from "lucide-react";

const LOCK_KEY = "intelliview_screen_lock";
const ACTIVITY_KEY = "intelliview_last_activity";
const DEFAULT_TIMEOUT = 300000;
const DEFAULT_PIN = "1234";

export function useScreenLock(timeout = DEFAULT_TIMEOUT) {
  const [isLocked, setIsLocked] = useState(false);
  const [pin, setPin] = useState("");

  useEffect(() => {
    const stored = localStorage.getItem(LOCK_KEY);
    if (stored === "locked") setIsLocked(true);
  }, []);

  const recordActivity = useCallback(() => {
    localStorage.setItem(ACTIVITY_KEY, Date.now().toString());
  }, []);

  useEffect(() => {
    const interval = setInterval(() => {
      if (isLocked) return;
      const last = parseInt(localStorage.getItem(ACTIVITY_KEY) || "0", 10);
      if (Date.now() - last > timeout) {
        setIsLocked(true);
        localStorage.setItem(LOCK_KEY, "locked");
      }
    }, 5000);
    return () => clearInterval(interval);
  }, [isLocked, timeout]);

  useEffect(() => {
    if (isLocked) return;
    const events = ["mousedown", "keydown", "scroll", "touchstart"];
    events.forEach((e) => document.addEventListener(e, recordActivity, { passive: true }));
    recordActivity();
    return () => events.forEach((e) => document.removeEventListener(e, recordActivity));
  }, [isLocked, recordActivity]);

  const unlock = useCallback((attemptPin) => {
    if (attemptPin === (process.env.NEXT_PUBLIC_SCREEN_LOCK_PIN || DEFAULT_PIN)) {
      setIsLocked(false);
      localStorage.removeItem(LOCK_KEY);
      recordActivity();
      return true;
    }
    return false;
  }, [recordActivity]);

  const lock = useCallback(() => {
    setIsLocked(true);
    localStorage.setItem(LOCK_KEY, "locked");
  }, []);

  const resetTimer = useCallback(() => {
    recordActivity();
  }, [recordActivity]);

  return { isLocked, lock, unlock, resetTimer };
}

export default function ScreenLock({ isLocked, onUnlock }) {
  const [input, setInput] = useState("");
  const [showPin, setShowPin] = useState(false);
  const [error, setError] = useState(false);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (onUnlock(input)) {
      setInput("");
      setError(false);
    } else {
      setError(true);
      setInput("");
      setTimeout(() => setError(false), 1000);
    }
  };

  if (!isLocked) return null;

  return (
    <div className="fixed inset-0 z-[9999] flex items-center justify-center bg-zinc-950/95 backdrop-blur-xl">
      <div className="w-full max-w-sm space-y-8 animate-fade-in">
        <div className="flex flex-col items-center gap-4">
          <div className="relative">
            <div className="absolute inset-0 animate-ping rounded-full bg-accent/20" />
            <div className="relative flex h-20 w-20 items-center justify-center rounded-full bg-zinc-900 border border-accent/30">
              <Lock className="h-8 w-8 text-accent" />
            </div>
          </div>
          <div className="text-center">
            <h2 className="text-xl font-semibold text-zinc-50">Screen Locked</h2>
            <p className="text-sm text-muted mt-1">Enter PIN to unlock</p>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="relative">
            <Input
              type={showPin ? "text" : "password"}
              value={input}
              onChange={setInput}
              placeholder="Enter PIN"
              autoFocus
              error={error}
              className="h-14 text-center text-2xl tracking-[0.5em] rounded-xl bg-zinc-900 text-zinc-50 placeholder-zinc-600 focus:ring-accent"
            />
              
            
            <button
              type="button"
              onClick={() => setShowPin(!showPin)}
              className="absolute right-4 top-1/2 -translate-y-1/2 text-zinc-500 hover:text-zinc-300 transition-colors"
            >
              {showPin ? <EyeOff className="h-5 w-5" /> : <Eye className="h-5 w-5" />}
            </button>
          </div>
          {error && (
            <p className="text-center text-sm text-rose-400 animate-shake">Incorrect PIN</p>
          )}
          <button
            type="submit"
            className="w-full h-12 rounded-xl bg-accent text-white font-medium hover:bg-accent/90 active:scale-[0.98] transition-all flex items-center justify-center gap-2"
          >
            <Unlock className="h-4 w-4" />
            Unlock
          </button>
        </form>

        <p className="text-center text-xs text-zinc-600">
          Auto-locks after {Math.round(DEFAULT_TIMEOUT / 60000)} min of inactivity
        </p>
      </div>
    </div>
  );
}
