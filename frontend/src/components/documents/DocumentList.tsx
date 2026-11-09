import type { DocumentRecord } from "../../api/types";
import { formatBytes, formatDate } from "../../lib/format";
import { Button } from "../common/Button";
import { StatusBadge } from "../common/StatusBadge";
import styles from "./DocumentList.module.css";

interface Props {
  documents: DocumentRecord[];
  onDelete?: (documentId: string) => void;
  readOnly?: boolean;
}

export function DocumentList({ documents, onDelete, readOnly = false }: Props) {
  if (documents.length === 0) {
    return (
      <div className={styles.listCard}>
        <div className={styles.header}>Uploaded Records (0)</div>
        <div className={styles.empty}>No documents uploaded yet.</div>
      </div>
    );
  }

  return (
    <div className={styles.listCard} role="region" aria-label="Uploaded Documents List">
      <div className={styles.header}>Uploaded Records ({documents.length})</div>
      <div>
        {documents.map((doc) => (
          <div key={doc.id} className={styles.item}>
            <div className={styles.fileInfo}>
              <span className={styles.fileName}>
                📄 {doc.original_filename} ({doc.document_type.replace(/_/g, " ")})
              </span>
              <span className={styles.fileMeta}>
                {formatBytes(doc.size_bytes)} • SHA256: {doc.sha256.substring(0, 12)}... • Uploaded: {formatDate(doc.created_at)}
              </span>
            </div>
            <div className={styles.actions}>
              <StatusBadge status={doc.status} />
              {!readOnly && onDelete && (
                <Button size="sm" variant="ghost" onClick={() => onDelete(doc.id)}>
                  Delete
                </Button>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
