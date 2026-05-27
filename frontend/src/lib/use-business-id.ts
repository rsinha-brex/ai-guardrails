"use client";

import { useCallback, useEffect, useState } from "react";

/**
 * Read + write the current `?business=<id>` query param.
 *
 * - Always returns `null` on the server and the first client render so
 *   `Link` hrefs that depend on it don't hydration-mismatch; the real
 *   value is set by the post-mount `useEffect`.
 * - Listens for `popstate` so all consumers (AppShell + each page) stay
 *   in sync without prop-drilling.
 * - The setter rewrites `?business=` via `history.pushState` and fires a
 *   synthetic `popstate` so sibling consumers re-read the URL. This is
 *   the central place that knows about the synthetic event — components
 *   should never dispatch one themselves.
 */
export function useBusinessId(): {
  businessId: string | null;
  setBusinessId: (id: string) => void;
} {
  const [businessId, setBusinessIdState] = useState<string | null>(null);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const sync = () => {
      const usp = new URLSearchParams(window.location.search);
      setBusinessIdState(usp.get("business"));
    };
    sync();
    window.addEventListener("popstate", sync);
    return () => window.removeEventListener("popstate", sync);
  }, []);

  const setBusinessId = useCallback((id: string) => {
    if (typeof window === "undefined") return;
    const url = new URL(window.location.href);
    url.searchParams.set("business", id);
    window.history.pushState({}, "", url.toString());
    // pushState doesn't fire popstate automatically; do it ourselves so
    // every consumer of useBusinessId() picks up the change.
    setTimeout(() => window.dispatchEvent(new PopStateEvent("popstate")), 0);
  }, []);

  return { businessId, setBusinessId };
}
