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
  fetcherRef.current = fetcher;

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
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    run();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  return { data, error, loading, refetch: run };
}
