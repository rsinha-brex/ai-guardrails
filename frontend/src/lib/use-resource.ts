"use client";

import { useCallback, useEffect, useRef, useState } from "react";

type ResourceState<T> = {
  data: T | null;
  error: string | null;
  loading: boolean;
  refetch: () => void;
};

/**
 * Generic fetcher hook with the load / loading / error / refetch state
 * machine that the rules / activity pages all duplicated.
 *
 * Re-runs `fetcher` whenever `deps` change. The fetcher is stored in a ref
 * so callers don't need to memoize it — re-renders that change the closure
 * but not the deps don't trigger refetches.
 *
 * Returns `data: null` until the first successful fetch. `error` is the
 * stringified rejection. `refetch()` triggers a manual reload (e.g. after
 * a mutation) without changing deps.
 */
export function useResource<T>(
  fetcher: () => Promise<T>,
  deps: unknown[],
): ResourceState<T> {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const fetcherRef = useRef(fetcher);
  // Update the ref in an effect — React 19's strict hook rules forbid
  // mutating refs during render. Functionally equivalent: the ref is read
  // by `run()` which only fires inside an effect or event handler, so the
  // value is always the latest committed fetcher.
  useEffect(() => {
    fetcherRef.current = fetcher;
  });

  const run = useCallback(() => {
    setLoading(true);
    fetcherRef
      .current()
      .then((d) => {
        setData(d);
        setError(null);
      })
      .catch((e: unknown) => setError(String(e)))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    // The standard "fetch on mount + when deps change" pattern. React 19
    // flags any setState-in-effect — but that's exactly what a data-fetch
    // hook does, by definition. Suppressed locally with a clear reason.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    run();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  return { data, error, loading, refetch: run };
}
