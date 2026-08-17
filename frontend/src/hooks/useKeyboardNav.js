"use client";
import { useEffect } from "react";
import { useRouter } from "next/navigation";
function useKeyboardNav(onShowHelp) {
  const router = useRouter();
  useEffect(() => {
    let lastG = 0;
    const onKey = (e) => {
      const target = e.target;
      if (target && (target.tagName === "INPUT" || target.tagName === "TEXTAREA" || target.isContentEditable)) {
        return;
      }
      const now = Date.now();
      if (e.key === "g" && now - lastG < 800) {
        lastG = 0;
        return;
      }
      if (e.key === "g") {
        lastG = now;
        return;
      }
      if (lastG && now - lastG < 800) {
        const route = {
          s: "/sessions",
          w: "/workers",
          a: "/analytics",
          o: "/",
          ",": "/settings",
          i: "/interview",
          c: "/candidates"
        };
        if (route[e.key.toLowerCase()]) {
          e.preventDefault();
          router.push(route[e.key.toLowerCase()]);
          lastG = 0;
        }
        return;
      }
      if (e.key === "?") {
        e.preventDefault();
        onShowHelp();
      }
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [router, onShowHelp]);
}
export {
  useKeyboardNav
};
