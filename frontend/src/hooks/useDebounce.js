"use client";
import { useState, useEffect, useRef, useCallback, useMemo } from "react";

export function useDebounce(value, delay = 300) {
  const [debouncedValue, setDebouncedValue] = useState(value);

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedValue(value), delay);
    return () => clearTimeout(timer);
  }, [value, delay]);

  return debouncedValue;
}

export function useThrottle(callback, delay = 100) {
  const lastCallRef = useRef(0);
  const timerRef = useRef(null);

  return useCallback(
    (...args) => {
      const now = Date.now();
      const timeUntilCall = delay - (now - lastCallRef.current);

      if (timeUntilCall <= 0) {
        lastCallRef.current = now;
        callback(...args);
      } else if (!timerRef.current) {
        timerRef.current = setTimeout(() => {
          lastCallRef.current = Date.now();
          timerRef.current = null;
          callback(...args);
        }, timeUntilCall);
      }
    },
    [callback, delay],
  );
}

export function useVirtualList(items, { itemHeight = 40, overscan = 5 }) {
  const [scrollTop, setScrollTop] = useState(0);
  const [containerHeight, setContainerHeight] = useState(0);

  const visibleItems = useMemo(() => {
    const startIndex = Math.max(0, Math.floor(scrollTop / itemHeight) - overscan);
    const endIndex = Math.min(
      items.length - 1,
      Math.ceil((scrollTop + containerHeight) / itemHeight) + overscan,
    );

    return items.slice(startIndex, endIndex + 1).map((item, i) => ({
      ...item,
      _virtualIndex: startIndex + i,
      _virtualTop: (startIndex + i) * itemHeight,
    }));
  }, [items, scrollTop, containerHeight, itemHeight, overscan]);

  const totalHeight = items.length * itemHeight;

  const handleScroll = useCallback((e) => {
    setScrollTop(e.target.scrollTop);
  }, []);

  const containerRef = useCallback((node) => {
    if (node) {
      setContainerHeight(node.clientHeight);
      const observer = new ResizeObserver(([entry]) => {
        setContainerHeight(entry.contentRect.height);
      });
      observer.observe(node);
      return () => observer.disconnect();
    }
  }, []);

  return {
    visibleItems,
    totalHeight,
    handleScroll,
    containerRef,
  };
}

export function useLazyLoad(options = {}) {
  const [isVisible, setIsVisible] = useState(false);
  const ref = useRef(null);

  useEffect(() => {
    const element = ref.current;
    if (!element) return;

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setIsVisible(true);
          observer.disconnect();
        }
      },
      { threshold: 0.1, ...options },
    );

    observer.observe(element);
    return () => observer.disconnect();
  }, []);

  return { ref, isVisible };
}
