"use client";

import { useEffect, useRef, useState } from "react";

/**
 * Animates a number counting up from 0 to `value` on mount / whenever
 * `value` changes, using requestAnimationFrame rather than an interval so it
 * stays smooth and cancels cleanly. Deliberately tiny -- this exists so the
 * dashboard's stat tiles can feel alive without pulling in a library for one
 * effect.
 *
 * Returns `null` unchanged when `value` is null (CounterTile's contract: a
 * genuine zero and "not loaded yet" must never look identical -- see
 * counter-tile.tsx), so callers don't have to special-case loading state.
 */
export function useCountUp(value: number | null, durationMs = 700): number | null {
  const [display, setDisplay] = useState<number>(value ?? 0);
  const frameRef = useRef<number | null>(null);
  const prefersReducedMotion = useRef(false);

  useEffect(() => {
    prefersReducedMotion.current =
      typeof window !== "undefined" &&
      window.matchMedia?.("(prefers-reduced-motion: reduce)").matches === true;
  }, []);

  useEffect(() => {
    if (value === null) return;

    if (prefersReducedMotion.current) {
      setDisplay(value);
      return;
    }

    const from = 0;
    const to = value;
    const start = performance.now();

    function tick(now: number) {
      const elapsed = now - start;
      const progress = Math.min(1, elapsed / durationMs);
      // ease-out-cubic
      const eased = 1 - Math.pow(1 - progress, 3);
      setDisplay(Math.round(from + (to - from) * eased));
      if (progress < 1) {
        frameRef.current = requestAnimationFrame(tick);
      }
    }

    frameRef.current = requestAnimationFrame(tick);
    return () => {
      if (frameRef.current !== null) cancelAnimationFrame(frameRef.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps -- durationMs is
    // treated as a constant per call site, not reactive.
  }, [value]);

  return value === null ? null : display;
}
