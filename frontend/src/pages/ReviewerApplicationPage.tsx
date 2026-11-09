import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api, ApiError, errorMessage } from "../api/client";
import type { ReviewActionRequest, ReviewerApplication } from "../api/types";
import { ReviewWorkspace } from "../components/reviewer/ReviewWorkspace";
import { loadReviewerSession } from "../lib/auth";
import { downloadBlob } from "../lib/download";

export function ReviewerApplicationPage() {
  const { applicationId } = useParams<{ applicationId: string }>();
  const navigate = useNavigate();
  const session = loadReviewerSession();
  const token = session?.token ?? null;

  const [data, setData] = useState<ReviewerApplication | null>(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refreshData = useCallback(async () => {
    if (!applicationId || !token) {
      setLoading(false);
      return;
    }
    try {
      const res = await api.reviewerApplication(applicationId, token);
      setData(res);
      setError(null);
    } catch (err: unknown) {
      if (err instanceof ApiError && (err.status === 401 || err.status === 403)) {
        navigate("/reviewer/login");
      } else {
        setError(errorMessage(err));
      }
    } finally {
      setLoading(false);
    }
  }, [applicationId, token, navigate]);

  useEffect(() => {
    if (!token) {
      navigate("/reviewer/login");
      return;
    }
    if (!applicationId) return;
    void refreshData();
  }, [applicationId, token, navigate, refreshData]);

  async function handleAction(payload: ReviewActionRequest) {
    if (!applicationId || !token) return;
    setActionLoading(true);
    setError(null);
    try {
      const idempotencyKey = `act-${Date.now()}`;
      await api.reviewerAction(applicationId, token, payload, idempotencyKey);
      await refreshData();
    } catch (err: unknown) {
      setError("Reviewer action failed: " + errorMessage(err));
    } finally {
      setActionLoading(false);
    }
  }

  async function handleExport() {
    if (!applicationId || !token) return;
    try {
      const blob = await api.reviewerExport(applicationId, token);
      downloadBlob(blob, `kuralcredit_packet_${applicationId}.json`);
    } catch (err: unknown) {
      setError("Failed to download packet: " + errorMessage(err));
    }
  }

  if (loading) {
    return <div style={{ padding: "var(--space-8)", textAlign: "center" }}>Loading application workspace...</div>;
  }

  if (!data) {
    return (
      <div style={{ maxWidth: "860px", margin: "0 auto", padding: "var(--space-8)" }}>
        <p>Application not found.</p>
        <Link to="/reviewer">← Back to Queue</Link>
      </div>
    );
  }

  return (
    <div style={{ maxWidth: "1140px", margin: "0 auto", padding: "var(--space-6) var(--space-4)" }}>
      <div style={{ marginBottom: "var(--space-4)" }}>
        <Link to="/reviewer" style={{ fontSize: "var(--text-sm)", color: "var(--primary)" }}>
          ← Back to Review Queue
        </Link>
      </div>

      {error && (
        <div style={{ background: "var(--danger-subtle)", color: "var(--danger)", padding: "var(--space-3)", borderRadius: "var(--radius-sm)", marginBottom: "var(--space-4)" }}>
          {error}
        </div>
      )}

      <ReviewWorkspace
        data={data}
        onAction={handleAction}
        onExport={handleExport}
        loading={actionLoading}
      />
    </div>
  );
}
