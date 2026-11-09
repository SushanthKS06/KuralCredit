import { statusLabel, statusTone } from "../../lib/format";
import styles from "./StatusBadge.module.css";

interface Props {
  status: string;
  label?: string;
}

export function StatusBadge({ status, label }: Props) {
  const tone = statusTone(status);
  return (
    <span className={[styles.badge, styles[tone] ?? styles.neutral].join(" ")}>
      {label ?? statusLabel(status)}
    </span>
  );
}
