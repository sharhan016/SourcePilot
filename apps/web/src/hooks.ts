import { useCallback, useEffect, useState } from "react";

export function usePolling<T>(loader: () => Promise<T>, interval = 3000) {
  const [data, setData] = useState<T>();
  const [error, setError] = useState<string>();
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    try {
      setData(await loader());
      setError(undefined);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unable to load SourcePilot data");
    } finally {
      setLoading(false);
    }
  }, [loader]);

  useEffect(() => {
    void refresh();
    const timer = window.setInterval(() => void refresh(), interval);
    return () => window.clearInterval(timer);
  }, [interval, refresh]);

  return { data, error, loading, refresh };
}

