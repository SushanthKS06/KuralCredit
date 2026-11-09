import type { FormEvent } from "react";
import { useState } from "react";
import type { Clarification } from "../../api/types";
import { Button } from "../common/Button";
import { Recorder } from "../voice/Recorder";
import styles from "./ClarificationCard.module.css";

interface Props {
  clarification: Clarification;
  onAnswerText: (clarificationId: string, text: string) => void;
  onAnswerAudio: (clarificationId: string, wavBlob: Blob) => void;
  loading?: boolean;
}

export function ClarificationCard({
  clarification,
  onAnswerText,
  onAnswerAudio,
  loading = false,
}: Props) {
  const [mode, setMode] = useState<"voice" | "text">("voice");
  const [textAnswer, setTextAnswer] = useState("");

  function handleTextSubmit(e: FormEvent) {
    e.preventDefault();
    if (!textAnswer.trim()) return;
    onAnswerText(clarification.id, textAnswer.trim());
    setTextAnswer("");
  }

  function handleVoiceRecorded(wavBlob: Blob) {
    onAnswerAudio(clarification.id, wavBlob);
  }

  return (
    <div className={styles.card} role="region" aria-label="Clarification Question">
      <div className={styles.questionHeader}>
        <h3 className={styles.questionText}>{clarification.question_text}</h3>
      </div>

      {clarification.reason && (
        <p className={styles.reasonNote}>
          <strong>Why we ask:</strong> {clarification.reason}
        </p>
      )}

      <div className={styles.answerSection}>
        <div className={styles.toggleRow}>
          <button
            type="button"
            className={`${styles.toggleBtn} ${mode === "voice" ? styles.active : ""}`}
            onClick={() => setMode("voice")}
          >
            Answer by Voice
          </button>
          <button
            type="button"
            className={`${styles.toggleBtn} ${mode === "text" ? styles.active : ""}`}
            onClick={() => setMode("text")}
          >
            Answer by Text
          </button>
        </div>

        {mode === "voice" ? (
          <Recorder onRecorded={handleVoiceRecorded} disabled={loading} maxSeconds={60} />
        ) : (
          <form onSubmit={handleTextSubmit} className={styles.textInputRow}>
            <input
              type="text"
              className={styles.textInput}
              value={textAnswer}
              onChange={(e) => setTextAnswer(e.target.value)}
              placeholder="Type your explanation here..."
              disabled={loading}
            />
            <Button type="submit" size="md" loading={loading} disabled={!textAnswer.trim()}>
              Submit Answer
            </Button>
          </form>
        )}
      </div>
    </div>
  );
}
