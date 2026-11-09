import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, ApiError, errorMessage } from "../api/client";
import type { ReviewerQueueItem } from "../api/types";
import { ReviewQueue } from "../components/reviewer/ReviewQueue";
import { loadReviewerSession } from "../lib/auth";

export function ReviewerDashboard() {
  const navigate = useNavigate();
  const session = loadReviewerSession();

  const [items, setItems] = useState<ReviewerQueueItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!session?.token) {
      navigate("/reviewer/login");
      return;
    }

    api
      .reviewerQueue(session.token)
      .then((data) => {
        setItems(data.items);
        setTotal(data.total);
      })
      .catch((err: unknown) => {
        if (err instanceof ApiError && (err.status === 401 || err.status === 403)) {
          navigate("/reviewer/login");
        } else {
          setError(errorMessage(err));
        }
      })
      .finally(() => setLoading(false));
  }, [session?.token, navigate]);

  return (
    <div style={{ maxWidth: "1080px", margin: "0 auto", padding: "var(--space-6) var(--space-4)" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "var(--space-6)" }}>
        <div>
          <h2 style={{ margin: "0 0 4px 0" }}>Reviewer Applications Queue</h2>
          <span style={{ fontSize: "var(--text-sm)", color: "var(--text-secondary)" }}>
            Logged in as: {session?.displayName || "Reviewer"}
          </span>
        </div>
      </div>

      {error && (
        <div style={{ background: "var(--danger-subtle)", color: "var(--danger)", padding: "var(--space-3)", borderRadius: "var(--radius-sm)", marginBottom: "var(--space-4)" }}>
          {error}
        </div>
      )}

      <ReviewQueue items={items} total={total} loading={loading} />
    </div>
  );
}
