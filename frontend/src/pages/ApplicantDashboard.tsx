import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, errorMessage } from "../api/client";
import type { ApplicationDetail } from "../api/types";
import { ApplicationProgress } from "../components/application/ApplicationProgress";
import { Button } from "../components/common/Button";
import { SessionMissing } from "../components/common/SessionMissing";
import { StatusBadge } from "../components/common/StatusBadge";
import { loadApplicantSession } from "../lib/auth";
import styles from "./ApplicantDashboard.module.css";

export function ApplicantDashboard() {
  const { applicationId } = useParams<{ applicationId: string }>();
  const session = applicationId ? loadApplicantSession(applicationId) : null;
  const token = session?.token ?? null;

  const [data, setData] = useState<ApplicationDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!applicationId || !token) {
      setLoading(false);
      return;
    }
    let active = true;
    api
      .getApplication(applicationId, token)
      .then((detail) => {
        if (active) {
          setData(detail);
          setError(null);
        }
      })
      .catch((err: unknown) => {
        if (active) setError(errorMessage(err));
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [applicationId, token]);

  if (!session) {
    return <SessionMissing />;
  }

  if (loading) {
    return <div style={{ padding: "var(--space-8)", textAlign: "center" }}>Loading application details...</div>;
  }

  const app = data?.application;
  const isSubmitted = app?.status === "submitted_for_human_review";

  return (
    <div className={styles.container}>
      <ApplicationProgress currentStage={isSubmitted ? "submitted" : "interview"} />

      <div className={styles.headerRow}>
        <div>
          <h2 className={styles.businessTitle}>{app?.business_name || "Application Dashboard"}</h2>
          <div className={styles.metaText}>
            <span>Applicant: <strong>{app?.applicant_name}</strong></span>
            <span>•</span>
            <span>Ref: <code>{app?.reference}</code></span>
            <span>•</span>
            <span>Language: {app?.language} ({app?.voice})</span>
          </div>
        </div>
        <StatusBadge status={app?.status || "created"} />
      </div>

      {error && (
        <div className="alert alert-danger" style={{ marginBottom: "var(--space-4)" }}>
          {error}
        </div>
      )}

      {/* Overview Stats */}
      {(() => {
        const items = data?.completeness?.items || [];
        const completedItems = items.filter((i) => i.complete).length;
        const completenessPercent =
          items.length > 0
            ? Math.round((completedItems / items.length) * 100)
            : isSubmitted
            ? 100
            : 0;
        return (
          <div className={styles.summaryBox}>
            <div className={styles.summaryTitle}>Application Status Overview</div>
            <div className={styles.summaryStats}>
              <div className={styles.statItem}>
                <span className={styles.statValue}>{completenessPercent}%</span>
                <span className={styles.statLabel}>Completeness Score</span>
              </div>
              <div className={styles.statItem}>
                <span className={styles.statValue}>
                  {data?.completeness?.missing_fields.length ?? 0}
                </span>
                <span className={styles.statLabel}>Missing Fields</span>
              </div>
              <div className={styles.statItem}>
                <span className={styles.statValue}>
                  {data?.completeness?.open_clarifications ?? 0}
                </span>
                <span className={styles.statLabel}>Open Clarifications</span>
              </div>
              <div className={styles.statItem}>
                <span className={styles.statValue}>
                  {data?.completeness?.can_submit ? "Ready to Submit" : isSubmitted ? "Submitted" : "In Progress"}
                </span>
                <span className={styles.statLabel}>Readiness</span>
              </div>
            </div>
          </div>
        );
      })()}

      {/* Action Cards */}
      <div className={styles.cardGrid}>
        <div className={styles.card}>
          <div className={styles.cardTop}>
            <span className={styles.cardIcon}>🎙️</span>
            <h4 className={styles.cardTitle}>1. Voice Interview</h4>
            <p className={styles.cardDesc}>
              Explain your business income, seasonality, and turnover in your preferred language.
            </p>
          </div>
          <Link to={`/apply/${applicationId}/interview`}>
            <Button size="sm" variant="secondary">Go to Interview →</Button>
          </Link>
        </div>

        <div className={styles.card}>
          <div className={styles.cardTop}>
            <span className={styles.cardIcon}>📄</span>
            <h4 className={styles.cardTitle}>2. Documents &amp; Evidence</h4>
            <p className={styles.cardDesc}>
              Upload synthetic bank statements and GST return summaries for verification.
            </p>
          </div>
          <Link to={`/apply/${applicationId}/documents`}>
            <Button size="sm" variant="secondary">Go to Documents →</Button>
          </Link>
        </div>

        <div className={styles.card}>
          <div className={styles.cardTop}>
            <span className={styles.cardIcon}>📋</span>
            <h4 className={styles.cardTitle}>3. Final Review</h4>
            <p className={styles.cardDesc}>
              Answer any follow-up questions and submit your evidence packet for a human credit officer.
            </p>
          </div>
          <Link to={`/apply/${applicationId}/review`}>
            <Button size="sm" variant="primary">Review &amp; Submit →</Button>
          </Link>
        </div>
      </div>
    </div>
  );
}
