"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";

/**
 * Holds the inspector identity that becomes the `X-Inspector-Id` header on
 * write requests. This is deliberately NOT authentication: the backend's
 * auth model (backend/lmd/api/deps.py) is a single shared bearer token held
 * server-side, and the inspector ID is a caller-asserted string used as the
 * audit-log actor. The UI must therefore never imply a verified login.
 */
const STORAGE_KEY = "lmd.inspector";
// Render's free tier spins the backend down after 15 minutes idle. A
// best-effort ping every 10 minutes from this always-mounted provider keeps
// the instance warm while a judge is browsing, without a hard dependency on
// any single page staying open.
const KEEP_ALIVE_INTERVAL_MS = 10 * 60 * 1000;

export interface InspectorIdentity {
  inspectorId: string;
  name: string;
  designation: string;
}

interface InspectorContextValue {
  inspector: InspectorIdentity | null;
  /** false until localStorage has been read, so no page flashes a signed-out
   *  state at a signed-in inspector. */
  ready: boolean;
  signIn: (identity: InspectorIdentity) => void;
  signOut: () => void;
}

const InspectorContext = createContext<InspectorContextValue | null>(null);

interface InspectorState {
  inspector: InspectorIdentity | null;
  ready: boolean;
}

export function InspectorProvider({ children }: { children: React.ReactNode }) {
  const [{ inspector, ready }, setState] = useState<InspectorState>({
    inspector: null,
    ready: false,
  });

  useEffect(() => {
    // One-time hydration from localStorage: this cannot run during the
    // server render (no localStorage there), so it must be an effect, and it
    // can only ever set state once per mount -- not the update-on-every-
    // external-change loop the lint rule is guarding against.
    let next: InspectorIdentity | null = null;
    try {
      const raw = window.localStorage.getItem(STORAGE_KEY);
      if (raw) next = JSON.parse(raw) as InspectorIdentity;
    } catch {
      // A corrupt entry must not break the app; treat it as signed out.
      window.localStorage.removeItem(STORAGE_KEY);
    }
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setState({ inspector: next, ready: true });
  }, []);

  useEffect(() => {
    const interval = setInterval(() => {
      fetch("/api/lmd/health", { cache: "no-store" }).catch(() => {
        // Best-effort ping only -- failures here are not surfaced anywhere.
      });
    }, KEEP_ALIVE_INTERVAL_MS);
    return () => clearInterval(interval);
  }, []);

  const setInspector = useCallback((next: InspectorIdentity | null) => {
    setState((s) => ({ ...s, inspector: next }));
  }, []);

  const signIn = useCallback(
    (identity: InspectorIdentity) => {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(identity));
      setInspector(identity);
    },
    [setInspector],
  );

  const signOut = useCallback(() => {
    window.localStorage.removeItem(STORAGE_KEY);
    setInspector(null);
  }, [setInspector]);

  const value = useMemo(
    () => ({ inspector, ready, signIn, signOut }),
    [inspector, ready, signIn, signOut],
  );

  return (
    <InspectorContext.Provider value={value}>{children}</InspectorContext.Provider>
  );
}

export function useInspector(): InspectorContextValue {
  const context = useContext(InspectorContext);
  if (context === null) {
    throw new Error("useInspector must be used inside <InspectorProvider>");
  }
  return context;
}
