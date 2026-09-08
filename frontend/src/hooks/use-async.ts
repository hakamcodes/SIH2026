"use client";

import { useEffect, useRef, useState } from "react";

import { describeUnknownError, isApiError, type ApiError } from "@/lib/errors";

export interface AsyncState<T> {
  data: T | null;
  error: ApiError | Error | null;
  /** True on the initial load AND on every refetch -- callers that want a
   *  "loaded once, now refreshing" distinction should track that themselves;
   *  none of Phase 2's read views need it. */
  loading: boolean;
  refetch: () => void;
}

interface InternalState<T> {
  data: T | null;
  error: ApiError | Error | null;
  loading: boolean;
}

/**
 * Fetches on mount and whenever `deps` changes, cancels the in-flight
 * request via AbortSignal if the component unmounts or deps change again
 * first, and never calls setState after unmount.
 *
 * `deps` is passed straight through to useEffect the same way a caller would
 * pass its own deps array -- eslint's exhaustive-deps check cannot verify a
 * variable-length array parameter's contents (a warning here, same
 * limitation any custom hook wrapping useEffect has).
 *
 * `load` is intentionally NOT wrapped in useCallback: the React Compiler
 * lint rule requires useCallback/useMemo dependency arrays to be literals,
 * which a passed-through `deps` parameter can never be. Recreating `load`
 * every render is fine here -- nothing depends on it being referentially
 * stable across renders.
 */
export function useAsync<T>(
  fetcher: (signal: AbortSignal) => Promise<T>,
  deps: React.DependencyList,
): AsyncState<T> {
  const [state, setState] = useState<InternalState<T>>({
    data: null,
    error: null,
    loading: true,
  });
  const runIdRef = useRef(0);

  function load() {
    const runId = ++runIdRef.current;
    const controller = new AbortController();

    // Deferred to a microtask rather than set synchronously here: the
    // initial "loading" value from useState already covers the mount case,
    // and the lint rule below (react-hooks/set-state-in-effect) flags any
    // setState reachable synchronously from the effect body -- the same
    // constraint that shapes every other setState call in this file to live
    // inside a promise callback instead.
    Promise.resolve().then(() => {
      if (runIdRef.current !== runId) return;
      setState((s) => ({ ...s, loading: true, error: null }));
    });

    fetcher(controller.signal)
      .then((result) => {
        if (runIdRef.current !== runId) return;
        setState({ data: result, error: null, loading: false });
      })
      .catch((err) => {
        if (runIdRef.current !== runId || controller.signal.aborted) return;
        const normalized = isApiError(err) || err instanceof Error ? err : new Error(describeUnknownError(err));
        setState((s) => ({ ...s, error: normalized, loading: false }));
      });

    return () => controller.abort();
  }

  useEffect(() => load(), deps); // eslint-disable-line react-hooks/exhaustive-deps

  function refetch() {
    load();
  }

  return { ...state, refetch };
}
