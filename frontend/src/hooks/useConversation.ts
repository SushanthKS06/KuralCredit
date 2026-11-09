import { useCallback, useEffect, useState } from "react";
import { api, errorMessage } from "../api/client";
import type { Conversation, TurnResponse } from "../api/types";

export function useConversation(applicationId: string | undefined, token: string | null) {
  const [conversation, setConversation] = useState<Conversation | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchConversation = useCallback(async () => {
    if (!applicationId || !token) return;
    setLoading(true);
    try {
      const data = await api.getConversation(applicationId, token);
      setConversation(data);
      setError(null);
    } catch (err: unknown) {
      setError(errorMessage(err) || "Failed to load conversation");
    } finally {
      setLoading(false);
    }
  }, [applicationId, token]);

  useEffect(() => {
    fetchConversation();
  }, [fetchConversation]);

  const submitTurn = useCallback(
    async (payload: {
      text: string;
      input_mode: "text" | "audio";
      language?: string;
      stt_request_id?: string;
      stt_latency_ms?: number;
      stt_model?: string;
      confirmed_transcript?: boolean;
      clarification_id?: string;
    }): Promise<TurnResponse> => {
      if (!applicationId || !token) throw new Error("Missing application session");
      setLoading(true);
      setError(null);
      try {
        const res = await api.submitTurn(applicationId, token, payload);
        await fetchConversation();
        return res;
      } catch (err: unknown) {
        setError(errorMessage(err) || "Failed to submit response");
        throw err;
      } finally {
        setLoading(false);
      }
    },
    [applicationId, token, fetchConversation],
  );

  return {
    conversation,
    turns: conversation?.turns ?? [],
    openClarifications: conversation?.open_clarifications ?? [],
    nextQuestion: conversation?.next_question ?? null,
    loading,
    error,
    refresh: fetchConversation,
    submitTurn,
  };
}
