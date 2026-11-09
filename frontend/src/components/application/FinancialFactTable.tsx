import { useState } from "react";
import type { FinancialFact } from "../../api/types";
import { formatIndianScale, formatMoney } from "../../lib/format";
import { Button } from "../common/Button";
import { StatusBadge } from "../common/StatusBadge";
import styles from "./FinancialFactTable.module.css";

interface Props {
  facts: FinancialFact[];
  onCorrectFact?: (factId: string, action: "confirm" | "correct" | "reject", newValue?: string) => void;
  readOnly?: boolean;
}

export function FinancialFactTable({ facts, onCorrectFact, readOnly = false }: Props) {
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editValue, setEditValue] = useState("");
  const canEdit = !readOnly && Boolean(onCorrectFact);

  function startEdit(fact: FinancialFact) {
    setEditingId(fact.id);
    setEditValue(fact.normalized_value ?? fact.raw_value);
  }

  function handleSave(factId: string) {
    if (onCorrectFact && editValue.trim()) {
      onCorrectFact(factId, "correct", editValue.trim());
    }
    setEditingId(null);
  }

  function handleConfirm(factId: string) {
    if (onCorrectFact) {
      onCorrectFact(factId, "confirm");
    }
  }

  if (facts.length === 0) {
    return (
      <div className={styles.tableCard}>
        <div className={styles.header}>
          <h4 className={styles.title}>Financial Evidence & Facts</h4>
        </div>
        <div className={styles.empty}>
          No financial facts declared or extracted yet. Complete the voice interview or upload documents.
        </div>
      </div>
    );
  }

  return (
    <div className={styles.tableCard} role="region" aria-label="Extracted Financial Facts">
      <div className={styles.header}>
        <h4 className={styles.title}>Financial Evidence & Facts</h4>
        <span style={{ fontSize: "var(--text-xs)", color: "var(--text-secondary)" }}>
          {facts.length} record{facts.length > 1 ? "s" : ""}
        </span>
      </div>

      <div className={styles.tableWrapper}>
        <table className={styles.table}>
          <thead>
            <tr>
              <th className={styles.th}>Field</th>
              <th className={styles.th}>Amount (INR)</th>
              <th className={styles.th}>Scale</th>
              <th className={styles.th}>Period</th>
              <th className={styles.th}>Source</th>
              <th className={styles.th}>Status</th>
              {canEdit && <th className={styles.th}>Actions</th>}
            </tr>
          </thead>
          <tbody>
            {facts.map((f) => {
              const isEditing = editingId === f.id;
              const isRejected = f.provenance_status === "rejected";
              return (
                <tr key={f.id}>
                  <td className={styles.td}>
                    <strong>{f.label || f.field_key}</strong>
                  </td>
                  <td className={styles.td}>
                    {isEditing ? (
                      <div className={styles.editRow}>
                        <input
                          type="text"
                          value={editValue}
                          onChange={(e) => setEditValue(e.target.value)}
                          className={styles.editInput}
                          placeholder="e.g. 1800000"
                        />
                        <Button size="sm" onClick={() => handleSave(f.id)}>Save</Button>
                        <Button size="sm" variant="ghost" onClick={() => setEditingId(null)}>Cancel</Button>
                      </div>
                    ) : (
                      <span className={styles.amount}>
                        {formatMoney(f.normalized_value ?? f.raw_value)}
                      </span>
                    )}
                  </td>
                  <td className={styles.td}>
                    {formatIndianScale(f.normalized_value ?? f.raw_value)}
                  </td>
                  <td className={styles.td}>{f.period_label || "-"}</td>
                  <td className={styles.td}>
                    <span style={{ textTransform: "capitalize", fontSize: "var(--text-xs)" }}>
                      {f.source_type.replace(/_/g, " ")}
                    </span>
                  </td>
                  <td className={styles.td}>
                    <StatusBadge status={f.provenance_status} />
                  </td>
                  {canEdit && (
                    <td className={styles.td}>
                      {isRejected ? (
                        <span style={{ fontSize: "var(--text-xs)", color: "var(--text-secondary)" }}>
                          No actions
                        </span>
                      ) : f.provenance_status !== "applicant_confirmed" && f.provenance_status !== "reviewer_verified" ? (
                        <div style={{ display: "flex", gap: "var(--space-2)" }}>
                          <Button size="sm" variant="secondary" onClick={() => handleConfirm(f.id)}>
                            Confirm
                          </Button>
                          <Button size="sm" variant="ghost" onClick={() => startEdit(f)}>
                            Edit
                          </Button>
                        </div>
                      ) : (
                        <Button size="sm" variant="ghost" onClick={() => startEdit(f)}>
                          Edit
                        </Button>
                      )}
                    </td>
                  )}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
