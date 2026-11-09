import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, errorMessage } from "../api/client";
import type { DocumentRecord, FinancialFact } from "../api/types";
import { ApplicationProgress } from "../components/application/ApplicationProgress";
import { FinancialFactTable } from "../components/application/FinancialFactTable";
import { Button } from "../components/common/Button";
import { SessionMissing } from "../components/common/SessionMissing";
import { DocumentList } from "../components/documents/DocumentList";
import { DocumentUploader } from "../components/documents/DocumentUploader";
import { loadApplicantSession } from "../lib/auth";
import styles from "./DocumentsPage.module.css";

export function DocumentsPage() {
  const { applicationId } = useParams<{ applicationId: string }>();
  const session = applicationId ? loadApplicantSession(applicationId) : null;
  const token = session?.token ?? null;

  const [documents, setDocuments] = useState<DocumentRecord[]>([]);
  const [facts, setFacts] = useState<FinancialFact[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refreshData = useCallback(async () => {
    if (!applicationId || !token) {
      setLoading(false);
      return;
    }
    try {
      const [docsData, factsData] = await Promise.all([
        api.listDocuments(applicationId, token),
        api.listFacts(applicationId, token),
      ]);
      setDocuments(docsData.items);
      setFacts(factsData.items);
      setError(null);
    } catch (err: unknown) {
      setError(errorMessage(err));
    } finally {
      setLoading(false);
    }
  }, [applicationId, token]);

  useEffect(() => {
    void refreshData();
  }, [refreshData]);

  async function handleUpload(file: File, docType: string) {
    if (!applicationId || !token) return;
    setUploading(true);
    setError(null);
    try {
      await api.uploadDocument(applicationId, token, file, docType);
      await refreshData();
    } catch (err: unknown) {
      setError("Document upload or parsing failed: " + errorMessage(err));
    } finally {
      setUploading(false);
    }
  }

  async function handleDelete(documentId: string) {
    if (!token) return;
    try {
      await api.deleteDocument(documentId, token);
      await refreshData();
    } catch (err: unknown) {
      setError("Failed to delete document: " + errorMessage(err));
    }
  }

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

  if (!session) {
    return <SessionMissing />;
  }

  if (loading) {
    return <div style={{ padding: "var(--space-8)", textAlign: "center" }}>Loading documents...</div>;
  }

  return (
    <div className={styles.container}>
      <ApplicationProgress currentStage="documents" />

      <div className={styles.topBar}>
        <div>
          <h2 className={styles.pageTitle}>Financial Records &amp; Supporting Evidence</h2>
          <span className={styles.metaText}>
            Upload synthetic bank statements, GST summaries, or sales registers.
          </span>
        </div>
        <Link to={`/apply/${applicationId}/review`}>
          <Button variant="secondary">Next: Clarifications &amp; Review →</Button>
        </Link>
      </div>

      {error && (
        <div className="alert alert-danger" style={{ marginBottom: "var(--space-4)" }}>
          {error}
        </div>
      )}

      {/* Document Uploader */}
      <DocumentUploader onUpload={handleUpload} loading={uploading} />

      {/* Document List */}
      <DocumentList documents={documents} onDelete={handleDelete} />

      {/* Financial Facts Extracted */}
      <FinancialFactTable
        facts={facts.filter((fact) => fact.provenance_status !== "rejected")}
        onCorrectFact={handleCorrectFact}
      />

      <div className={styles.actionRow}>
        <Link to={`/apply/${applicationId}/review`}>
          <Button size="lg">Review Application &amp; Clarifications →</Button>
        </Link>
      </div>
    </div>
  );
}
