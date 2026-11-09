import type { AuditEvent } from "../../api/types";
import { formatDate } from "../../lib/format";
import styles from "./AuditTimeline.module.css";

interface Props {
  events: AuditEvent[];
}

export function AuditTimeline({ events }: Props) {
  if (events.length === 0) {
    return <div className={styles.empty}>No audit events recorded yet.</div>;
  }

  return (
    <div className={styles.container} role="region" aria-label="Audit Timeline">
      {events.map((evt) => (
        <div key={evt.id} className={styles.timelineItem}>
          <span className={styles.bullet} />
          <div className={styles.metaRow}>
            <span className={styles.actor}>{evt.actor}</span>
            <span>•</span>
            <span>{formatDate(evt.created_at)}</span>
            <span>•</span>
            <span style={{ textTransform: "uppercase", fontSize: "10px" }}>{evt.event_type}</span>
          </div>
          <p className={styles.summary}>{evt.summary}</p>
        </div>
      ))}
    </div>
  );
}
