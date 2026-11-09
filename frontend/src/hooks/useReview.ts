import { useCallback, useEffect, useState } from "react";
import { api, errorMessage } from "../api/client";
import type { ReviewActionRequest, ReviewerApplication, ReviewerQueue } from "../api/types";

export function useReview(reviewerToken: string | null, applicationId?: string) {
  const [queue, setQueue] = useState<ReviewerQueue | null>(null);
  const [packet, setPacket] = useState<ReviewerApplication | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchQueue = useCallback(async () => {
    if (!reviewerToken) return;
    setLoading(true);
    try {
      const res = await api.reviewerQueue(reviewerToken);
      setQueue(res);
      setError(null);
    } catch (err: unknown) {
      setError(errorMessage(err) || "Failed to load review queue");
    } finally {
      setLoading(false);
    }
  }, [reviewerToken]);

  const fetchPacket = useCallback(async () => {
    if (!reviewerToken || !applicationId) return;
    setLoading(true);
    try {
      const res = await api.reviewerApplication(applicationId, reviewerToken);
      setPacket(res);
      setError(null);
    } catch (err: unknown) {
      setError(errorMessage(err) || "Failed to load application packet");
    } finally {
      setLoading(false);
    }
  }, [reviewerToken, applicationId]);

  useEffect(() => {
    if (applicationId) {
      fetchPacket();
    } else if (reviewerToken) {
      fetchQueue();
    }
  }, [reviewerToken, applicationId, fetchPacket, fetchQueue]);

  const submitAction = useCallback(
    async (action: ReviewActionRequest, idempotencyKey?: string) => {
      if (!reviewerToken || !applicationId) throw new Error("Missing reviewer session or application ID");
      setLoading(true);
      setError(null);
      try {
        const res = await api.reviewerAction(applicationId, reviewerToken, action, idempotencyKey);
        await fetchPacket();
        return res;
      } catch (err: unknown) {
        setError(errorMessage(err) || "Failed to submit review action");
        throw err;
      } finally {
        setLoading(false);
      }
    },
    [reviewerToken, applicationId, fetchPacket],
  );

  return {
    queue,
    packet,
    loading,
    error,
    refreshQueue: fetchQueue,
    refreshPacket: fetchPacket,
    submitAction,
  };
}
