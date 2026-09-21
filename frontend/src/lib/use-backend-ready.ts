"use client";

import { useEffect, useState } from "react";

/**
 * Render's free tier spins the backend down after 15 minutes of inactivity;
 * the first request after that takes ~30-60s to wake it. Without this, a
 * judge's first click on the scan page hits a dead backend with no
 * indication anything is happening. Polls the versioned health route (the
 * Next.js proxy rewrites /api/lmd/<path> to /api/v1/<path> -- see
 * frontend/src/app/api/lmd/[...path]/route.ts -- so this must hit
 * /api/v1/health, not the unprefixed /health Render itself probes).
 */
export function useBackendReady(): { ready: boolean; attempts: number } {
  const [ready, setReady] = useState(false);
  const [attempts, setAttempts] = useState(0);

  useEffect(() => {
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | undefined;

    async function check() {
      if (cancelled) return;
      setAttempts((n) => n + 1);
      try {
        const response = await fetch("/api/lmd/health", {
          cache: "no-store",
          signal: AbortSignal.timeout(5000),
        });
        if (!cancelled && response.ok) {
          setReady(true);
          return;
        }
      } catch {
        // backend still asleep or unreachable -- retry below
      }
      if (!cancelled) {
        timer = setTimeout(check, 3000);
      }
    }

    check();

    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
    };
  }, []);

  return { ready, attempts };
}
