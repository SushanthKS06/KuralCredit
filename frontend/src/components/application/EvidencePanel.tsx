import type { Reconciliation } from "../../api/types";
import { StatusBadge } from "../common/StatusBadge";
import styles from "./EvidencePanel.module.css";

interface Props {
  reconciliation: Reconciliation | null;
}

export function EvidencePanel({ reconciliation }: Props) {
  if (!reconciliation) {
    return null;
  }

  return (
    <div className={styles.container} role="region" aria-label="Evidence & Reconciliation">
      <div className={styles.notice}>
        <strong>Operational Transparency:</strong> {reconciliation.policy_note}
      </div>

      <div className={styles.card}>
        <h4 className={styles.title}>Comparative Analysis & Reconciliations</h4>
        {reconciliation.comparisons.length === 0 ? (
          <p style={{ color: "var(--text-secondary)", fontSize: "var(--text-sm)" }}>
            No comparisons performed yet. Upload financial records to trigger comparison rules.
          </p>
        ) : (
          reconciliation.comparisons.map((item, index) => (
            <div key={index} className={styles.comparisonItem}>
              <div className={styles.comparisonHeader}>
                <span className={styles.fieldsCompare}>
                  {item.left_label} vs {item.right_label}
                </span>
                <StatusBadge status={item.status} />
              </div>
              <p className={styles.explanation}>{item.explanation}</p>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
