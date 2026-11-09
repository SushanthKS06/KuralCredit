import React, { useRef, useState } from "react";
import { Button } from "../common/Button";
import styles from "./DocumentUploader.module.css";

interface Props {
  onUpload: (file: File, documentType: string) => void;
  loading?: boolean;
}

const DOCUMENT_TYPES = [
  { id: "bank_statement", label: "Bank Statement (CSV / PDF)" },
  { id: "gst_summary", label: "GST Return Summary GSTR-3B (CSV / PDF)" },
  { id: "sales_register", label: "Sales Register / Invoices (XLSX / CSV)" },
  { id: "other", label: "Other Financial Record" },
];

export function DocumentUploader({ onUpload, loading = false }: Props) {
  const [docType, setDocType] = useState("bank_statement");
  const fileInputRef = useRef<HTMLInputElement>(null);

  function handleFileSelected(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    onUpload(file, docType);
    if (fileInputRef.current) fileInputRef.current.value = "";
  }

  return (
    <div>
      <div className={styles.typeRow}>
        <label htmlFor="doc-type-select" style={{ fontSize: "var(--text-sm)", fontWeight: 500 }}>
          Select Document Category:
        </label>
        <select
          id="doc-type-select"
          className={styles.typeSelect}
          value={docType}
          onChange={(e) => setDocType(e.target.value)}
          disabled={loading}
        >
          {DOCUMENT_TYPES.map((t) => (
            <option key={t.id} value={t.id}>
              {t.label}
            </option>
          ))}
        </select>
      </div>

      <div
        className={styles.uploadCard}
        onClick={() => fileInputRef.current?.click()}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            fileInputRef.current?.click();
          }
        }}
        aria-label="Upload document area"
      >
        <span className={styles.icon}>📄</span>
        <h4 className={styles.title}>Click or drag synthetic financial records to upload</h4>
        <p className={styles.subtitle}>
          Supports CSV, XLSX, and searchable PDF (max 10MB). Scanned PDF OCR is disabled.
        </p>
        <Button size="sm" variant="secondary" loading={loading} disabled={loading}>
          Browse File
        </Button>
        <input
          ref={fileInputRef}
          type="file"
          accept=".csv,.xlsx,.pdf"
          className={styles.fileInput}
          onChange={handleFileSelected}
          disabled={loading}
        />
      </div>
    </div>
  );
}

