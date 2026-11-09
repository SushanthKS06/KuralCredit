import React from "react";
import styles from "./ApplicationProgress.module.css";

export type ApplicationStage =
  | "profile"
  | "interview"
  | "documents"
  | "review"
  | "submitted";

interface Props {
  currentStage: ApplicationStage;
}

const STAGES: { id: ApplicationStage; label: string }[] = [
  { id: "profile", label: "1. Profile" },
  { id: "interview", label: "2. Voice Interview" },
  { id: "documents", label: "3. Documents" },
  { id: "review", label: "4. Clarification Review" },
  { id: "submitted", label: "5. Submitted" },
];

export function ApplicationProgress({ currentStage }: Props) {
  const currentIndex = STAGES.findIndex((s) => s.id === currentStage);

  return (
    <nav className={styles.container} aria-label="Application Progress">
      {STAGES.map((stage, idx) => {
        const isActive = idx === currentIndex;
        const isCompleted = idx < currentIndex;
        return (
          <React.Fragment key={stage.id}>
            <div
              className={`${styles.stepItem} ${isActive ? styles.active : ""} ${
                isCompleted ? styles.completed : ""
              }`}
            >
              <span className={styles.stepCircle}>
                {isCompleted ? "✓" : idx + 1}
              </span>
              <span className={styles.stepLabel}>{stage.label}</span>
            </div>
            {idx < STAGES.length - 1 && <div className={styles.separator} />}
          </React.Fragment>
        );
      })}
    </nav>
  );
}

