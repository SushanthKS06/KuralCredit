import { useCallback, useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api, ApiError, errorMessage } from "../api/client";
import type { ApplicationDetail, Conversation, FinancialFact, Reconciliation } from "../api/types";
import { ApplicationProgress } from "../components/application/ApplicationProgress";
import { ClarificationCard } from "../components/application/ClarificationCard";
import { EvidencePanel } from "../components/application/EvidencePanel";
import { FinancialFactTable } from "../components/application/FinancialFactTable";
import { Button } from "../components/common/Button";
import { SessionMissing } from "../components/common/SessionMissing";
import { StatusBadge } from "../components/common/StatusBadge";
import { loadApplicantSession } from "../lib/auth";
import styles from "./ApplicationReviewPage.module.css";

function submissionErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    const details = error.details as
      | { items?: Array<{ label?: string; detail?: string; complete?: boolean }> }
      | null;
    const blockers =
      details?.items?.filter((item) => !item.complete && item.label && item.detail) ?? [];
    if (blockers.length > 0) {
      return `${error.message} ${blockers
        .map((item) => `${item.label}: ${item.detail}`)
        .join(" ")}`;
    }
  }
  return errorMessage(error);
}

export function ApplicationReviewPage() {
  const { applicationId } = useParams<{ applicationId: string }>();
  const session = applicationId ? loadApplicantSession(applicationId) : null;
  const token = session?.token ?? null;

  const [application, setApplication] = useState<ApplicationDetail | null>(null);
  const [conversation, setConversation] = useState<Conversation | null>(null);
  const [facts, setFacts] = useState<FinancialFact[]>([]);
  const [reconciliation, setReconciliation] = useState<Reconciliation | null>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [confirmedAccuracy, setConfirmedAccuracy] = useState(false);
  const [submittedSuccess, setSubmittedSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refreshData = useCallback(async () => {
    if (!applicationId || !token) {
      setLoading(false);
      return;
    }
    try {
      const convData = await api.getConversation(applicationId, token);
      const [appData, factsData, reconData] = await Promise.all([
        api.getApplication(applicationId, token),
        api.listFacts(applicationId, token),
        api.getReconciliation(applicationId, token),
      ]);
      setApplication(appData);
      setConversation(convData);
      setFacts(factsData.items);
      setReconciliation(reconData);
      setError(null);
      if (appData.application.status === "submitted_for_human_review") {
        setSubmittedSuccess(true);
      }
    } catch (err: unknown) {
      setError(errorMessage(err));
    } finally {
      setLoading(false);
    }
  }, [applicationId, token]);

  useEffect(() => {
    void refreshData();
  }, [refreshData]);

  async function handleCorrectFact(
    factId: string,
    action: "confirm" | "correct" | "reject",
    newValue?: string,
  ) {
    if (!token) return;
    setError(null);
    try {
      await api.correctFact(factId, token, {
        action,
        ...(action === "correct" ? { normalized_value: newValue } : {}),
      });
      await refreshData();
    } catch (err: unknown) {
      setError("Failed to update financial fact: " + errorMessage(err));
    }
  }

  async function handleAnswerClarificationText(clarificationId: string, text: string) {
    if (!applicationId || !token) return;
    setSubmitting(true);
    setError(null);
    try {
      await api.submitTurn(applicationId, token, {
        text,
        input_mode: "text",
        clarification_id: clarificationId,
        confirmed_transcript: true,
      });
      await refreshData();
    } catch (err: unknown) {
      setError("Failed to submit clarification: " + errorMessage(err));
    } finally {
      setSubmitting(false);
    }
  }

  async function handleAnswerClarificationAudio(clarificationId: string, wavBlob: Blob) {
    if (!applicationId || !token) return;
    setSubmitting(true);
    setError(null);
    try {
      const lang = application?.application.language || "ta-IN";
      const trans = await api.transcribe(applicationId, token, wavBlob, lang);
      await api.submitTurn(applicationId, token, {
        text: trans.transcript,
        input_mode: "audio",
        clarification_id: clarificationId,
        confirmed_transcript: true,
        stt_request_id: trans.request_id || undefined,
        stt_latency_ms: trans.latency_ms,
        stt_model: trans.model,
      });
      await refreshData();
    } catch (err: unknown) {
      setError("Failed to transcribe & submit clarification: " + errorMessage(err));
    } finally {
      setSubmitting(false);
    }
  }

  async function handleSubmitFinal() {
    if (!applicationId || !token || !confirmedAccuracy || !application?.completeness.can_submit) return;
    setSubmitting(true);
    setError(null);
    try {
      const idempotencyKey = `sub-${applicationId}-${Date.now()}`;
      await api.submitApplication(applicationId, token, idempotencyKey);
      setSubmittedSuccess(true);
      await refreshData();
    } catch (err: unknown) {
      setError("Submission failed: " + submissionErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  }

  if (!session) {
    return <SessionMissing />;
  }

  if (loading) {
    return <div style={{ padding: "var(--space-8)", textAlign: "center" }}>Loading review packet...</div>;
  }

  const isSubmitted = submittedSuccess || application?.application.status === "submitted_for_human_review";
  const openClarifications = conversation?.open_clarifications || [];
  const completeness = application?.completeness;
  const blockers = completeness?.items.filter((item) => !item.complete) ?? [];
  const canSubmit = Boolean(completeness?.can_submit);

  return (
    <div className={styles.container}>
      <ApplicationProgress currentStage={isSubmitted ? "submitted" : "review"} />

      <div className={styles.topBar}>
        <div>
          <h2 className={styles.pageTitle}>Final Application &amp; Clarification Review</h2>
          <div className={styles.metaText}>
            <span>Application Ref: <code>{application?.application.reference}</code></span>
            <span>•</span>
            <span>Status: <StatusBadge status={application?.application.status || "created"} /></span>
          </div>
        </div>
      </div>

      {error && (
        <div className="alert alert-danger" style={{ marginBottom: "var(--space-4)" }}>
          {error}
        </div>
      )}

      {isSubmitted && (
        <div className={styles.submittedCard}>
          <h3 className={styles.submittedTitle}>
            ✓ Application Successfully Submitted for Human Review
          </h3>
          <p className={styles.submittedDesc}>
            Your declarations, speech transcripts, and uploaded records have been organized into a traceable packet.
            A human credit officer will review your evidence. KuralCredit does not issue autonomous credit decisions.
          </p>
        </div>
      )}

      {/* Open Clarifications */}
      {openClarifications.length > 0 && !isSubmitted && (
        <div style={{ marginBottom: "var(--space-6)" }}>
          <h3 className={styles.sectionHeading}>
            Pending Items Requiring Your Clarification ({openClarifications.length})
          </h3>
          <div className={styles.clarificationList}>
            {openClarifications.map((item) => (
              <ClarificationCard
                key={item.id}
                clarification={item}
                onAnswerText={handleAnswerClarificationText}
                onAnswerAudio={handleAnswerClarificationAudio}
                loading={submitting}
              />
            ))}
          </div>
        </div>
      )}

      {/* Financial Facts */}
      <FinancialFactTable
        facts={facts.filter((fact) => fact.provenance_status !== "rejected")}
        onCorrectFact={handleCorrectFact}
        readOnly={isSubmitted}
      />

      {/* Evidence & Reconciliation */}
      <EvidencePanel reconciliation={reconciliation} />

      {/* Submission Confirmation */}
      {!isSubmitted && (
        <div className={styles.submitCard}>
          <h3 className={styles.submitTitle}>Submit Application Packet</h3>

          {!canSubmit && (
            <div className={styles.readinessBox}>
              <p className={styles.readinessTitle}>Before you can submit:</p>
              {blockers.length > 0 ? (
                <ul className={styles.readinessList}>
                  {blockers.map((item) => (
                    <li key={item.key}>
                      <strong>{item.label}:</strong> {item.detail}
                    </li>
                  ))}
                </ul>
              ) : (
                <p className={styles.readinessText}>
                  The application is still being prepared. Refresh this page after answering any
                  pending questions or confirming the remaining values.
                </p>
              )}
            </div>
          )}

          <div className={styles.confirmRow}>
            <input
              id="confirm-accuracy-check"
              type="checkbox"
              className={styles.confirmCheckbox}
              checked={confirmedAccuracy}
              onChange={(e) => setConfirmedAccuracy(e.target.checked)}
              disabled={!canSubmit}
            />
            <label htmlFor="confirm-accuracy-check" className={styles.confirmLabel}>
              I confirm the accuracy of all declarations, understand that any variances have been clarified with explanations, and acknowledge that KuralCredit does not make loan decisions.
            </label>
          </div>

          <div className={styles.actionRow}>
            <Button
              size="lg"
              onClick={handleSubmitFinal}
              disabled={!canSubmit || !confirmedAccuracy || submitting}
              loading={submitting}
            >
              Submit for Human Review
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
