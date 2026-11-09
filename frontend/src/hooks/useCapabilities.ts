import { useEffect, useState } from "react";
import { api, errorMessage } from "../api/client";
import type { Capabilities } from "../api/types";

export function useCapabilities() {
  const [capabilities, setCapabilities] = useState<Capabilities | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    api
      .capabilities()
      .then((data: Capabilities) => {
        if (mounted) {
          setCapabilities(data);
          setError(null);
        }
      })
      .catch((err: unknown) => {
        if (mounted) {
          setError(errorMessage(err) || "Failed to load speech and language capabilities");
        }
      })
      .finally(() => {
        if (mounted) setLoading(false);
      });

    return () => {
      mounted = false;
    };
  }, []);

  return {
    capabilities,
    languages: capabilities?.languages ?? [],
    defaults: capabilities?.defaults ?? null,
    loading,
    error,
  };
}
