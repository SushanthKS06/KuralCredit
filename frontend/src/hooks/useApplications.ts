import { useCallback, useEffect, useState } from "react";
import { api, errorMessage } from "../api/client";
import type { ApplicationCreatePayload, ApplicationCreated, ApplicationDetail } from "../api/types";

export function useApplications(applicationId?: string, token?: string | null) {
  const [detail, setDetail] = useState<ApplicationDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchDetail = useCallback(async () => {
    if (!applicationId || !token) return;
    setLoading(true);
    try {
      const data = await api.getApplication(applicationId, token);
      setDetail(data);
      setError(null);
    } catch (err: unknown) {
      setError(errorMessage(err) || "Failed to load application details");
    } finally {
      setLoading(false);
    }
  }, [applicationId, token]);

  useEffect(() => {
    fetchDetail();
  }, [fetchDetail]);

  const createApplication = useCallback(async (payload: ApplicationCreatePayload): Promise<ApplicationCreated> => {
    setLoading(true);
    setError(null);
    try {
      const created = await api.createApplication(payload);
      return created;
    } catch (err: unknown) {
      setError(errorMessage(err) || "Failed to create application");
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const submitApplication = useCallback(async (id: string, appToken: string) => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.submitApplication(id, appToken);
      await fetchDetail();
      return res;
    } catch (err: unknown) {
      setError(errorMessage(err) || "Failed to submit application");
      throw err;
    } finally {
      setLoading(false);
    }
  }, [fetchDetail]);

  const withdrawApplication = useCallback(async (id: string, appToken: string, reason: string) => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.withdrawApplication(id, appToken, reason);
      await fetchDetail();
      return res;
    } catch (err: unknown) {
      setError(errorMessage(err) || "Failed to withdraw application");
      throw err;
    } finally {
      setLoading(false);
    }
  }, [fetchDetail]);

  return {
    detail,
    application: detail?.application ?? null,
    completeness: detail?.completeness ?? null,
    loading,
    error,
    refresh: fetchDetail,
    createApplication,
    submitApplication,
    withdrawApplication,
  };
}

