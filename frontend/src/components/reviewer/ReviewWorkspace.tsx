import type { FormEvent } from "react";
import { useEffect, useState } from "react";
import type { ReviewActionRequest, ReviewerApplication } from "../../api/types";
import { EvidencePanel } from "../application/EvidencePanel";
import { FinancialFactTable } from "../application/FinancialFactTable";
import { Button } from "../common/Button";
import { StatusBadge } from "../common/StatusBadge";
import { DocumentList } from "../documents/DocumentList";
import { AuditTimeline } from "./AuditTimeline";
import styles from "./ReviewWorkspace.module.css";

interface Props {
  data: ReviewerApplication;
  onAction: (payload: ReviewActionRequest) => void;
  onExport: () => void;
  loading?: boolean;
}

type ActionType = ReviewActionRequest["action"];

const ACTION_TYPES: ActionType[] = [
  "verify_fact",
  "reject_fact",
  "request_information",
  "complete_review",
];

function isActionType(value: string): value is ActionType {
  return (ACTION_TYPES as string[]).includes(value);
}

export function ReviewWorkspace({ data, onAction, onExport, loading = false }: Props) {
  const [actionType, setActionType] = useState<ActionType>("verify_fact");
  const [selectedFactKey, setSelectedFactKey] = useState(data.facts[0]?.field_key || "");
  const [reason, setReason] = useState("");

  const application = data.application;

  useEffect(() => {
    const keys = data.facts.map((fact) => fact.field_key);
    if (!keys.includes(selectedFactKey)) {
      setSelectedFactKey(keys[0] ?? "");
    }
  }, [data.facts, selectedFactKey]);

  function handleActionSubmit(e: FormEvent) {
    e.preventDefault();
    if (reason.trim().length < 5) return;
    if (actionType !== "complete_review" && !selectedFactKey) return;

    if (actionType === "verify_fact") {
      onAction({
        action: "verify_fact",
        field_key: selectedFactKey,
        reason: reason.trim(),
      });
    } else if (actionType === "request_information") {
      onAction({
        action: "request_information",
        field_key: selectedFactKey,
        reason: reason.trim(),
      });
    } else if (actionType === "complete_review") {
      onAction({
        action: "complete_review",
        reason: reason.trim(),
      });
    } else if (actionType === "reject_fact") {
      onAction({
        action: "reject_fact",
        field_key: selectedFactKey,
        reason: reason.trim(),
      });
    }
    setReason("");
  }

  return (
    <div className={styles.container} role="region" aria-label="Review Workspace">
      <div className={styles.boundaryNotice} role="note">
        <strong>Reviewer Boundary Notice:</strong> {data.boundary_notice}
      </div>

      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div>
          <h2 style={{ margin: "0 0 4px 0" }}>{application.business_name}</h2>
          <span style={{ color: "var(--text-secondary)", fontSize: "var(--text-sm)" }}>
            Applicant: {application.applicant_name} • Ref: {application.reference} • Status:{" "}
            <StatusBadge status={application.status} />
          </span>
        </div>
        <Button variant="secondary" onClick={onExport} disabled={loading}>
          Download Evidence Packet (JSON)
        </Button>
      </div>

      <div className={styles.twoColumn}>
        <div className={styles.panel}>
          <h3 className={styles.panelTitle}>Financial Evidence & Fact Verification</h3>
          <FinancialFactTable facts={data.facts} readOnly />

          <EvidencePanel reconciliation={data.reconciliation} />

          <h3 className={styles.panelTitle} style={{ marginTop: "var(--space-4)" }}>
            Uploaded Source Documents
          </h3>
          <DocumentList documents={data.documents} readOnly />
        </div>

        <div className={styles.panel}>
          <h3 className={styles.panelTitle}>AI Reviewer Summary (Groq GPT-OSS 120B)</h3>
          <div className={styles.summaryBox}>
            {data.summary.applicant_declared_facts?.length > 0 && (
              <p>
                <strong>Declared Facts:</strong> {data.summary.applicant_declared_facts.join("; ")}
              </p>
            )}
            {data.summary.applicant_explanations?.length > 0 && (
              <p>
                <strong>Applicant Explanations:</strong> {data.summary.applicant_explanations.join("; ")}
              </p>
            )}
            {data.summary.limitations?.length > 0 && (
              <p>
                <strong>Limitations Noted:</strong> {data.summary.limitations.join("; ")}
              </p>
            )}
            {data.summary.unresolved_items?.length > 0 && (
              <p style={{ color: "var(--warning)" }}>
                <strong>Unresolved:</strong> {data.summary.unresolved_items.join("; ")}
              </p>
            )}
          </div>

          <h3 className={styles.panelTitle}>Take Review Action</h3>
          <form onSubmit={handleActionSubmit} className={styles.actionForm}>
            <label style={{ fontSize: "var(--text-xs)", fontWeight: 600 }}>Action Type</label>
            <select
              className={styles.actionSelect}
              value={actionType}
              onChange={(e) => {
                if (isActionType(e.target.value)) {
                  setActionType(e.target.value);
                }
              }}
              disabled={loading}
            >
              <option value="verify_fact">Verify Specific Fact</option>
              <option value="reject_fact">Reject Specific Fact</option>
              <option value="request_information">Request Additional Information</option>
              <option value="complete_review">Mark Review Completed</option>
            </select>

            {(actionType === "verify_fact" || actionType === "reject_fact" || actionType === "request_information") && (
              <>
                <label style={{ fontSize: "var(--text-xs)", fontWeight: 600 }}>Target Fact</label>
                <select
                  className={styles.actionSelect}
                  value={selectedFactKey}
                  onChange={(e) => setSelectedFactKey(e.target.value)}
                  disabled={loading || data.facts.length === 0}
                >
                  {data.facts.length === 0 && <option value="">No facts available</option>}
                  {data.facts.map((f) => (
                    <option key={f.id} value={f.field_key}>
                      {f.label || f.field_key} ({f.normalized_value ?? f.raw_value})
                    </option>
                  ))}
                </select>
              </>
            )}

            <label style={{ fontSize: "var(--text-xs)", fontWeight: 600 }}>
              {actionType === "verify_fact"
                ? "Evidence Verification Rationale"
                : actionType === "reject_fact"
                ? "Reason for Rejecting Fact"
                : actionType === "request_information"
                ? "Clarification Question for Applicant"
                : "Review Completion Findings Summary"}
            </label>
            <textarea
              className={styles.actionInput}
              rows={3}
              minLength={5}
              maxLength={1000}
              placeholder={
                actionType === "verify_fact"
                  ? "e.g. Cross-checked declared sales against bank statement customer receipts and cash register."
                  : actionType === "reject_fact"
                  ? "e.g. Unsupported declaration with conflicting bank credit records."
                  : actionType === "request_information"
                  ? "e.g. Please clarify the nature of ₹4,00,000 personal transfer on 15/12/2025."
                  : "e.g. All declared figures verified with synthetic supporting documentation. Ready for underwriting packet."
              }
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              disabled={loading}
            />

            <Button
              type="submit"
              loading={loading}
              disabled={
                reason.trim().length < 5 ||
                (actionType !== "complete_review" && !selectedFactKey)
              }
            >
              Submit Review Action
            </Button>
          </form>

          <h3 className={styles.panelTitle} style={{ marginTop: "var(--space-4)" }}>
            Application Audit Trail
          </h3>
          <AuditTimeline events={data.audit_events} />
        </div>
      </div>
    </div>
  );
}
