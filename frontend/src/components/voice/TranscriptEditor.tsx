import React, { useState } from "react";
import { Button } from "../common/Button";
import styles from "./TranscriptEditor.module.css";

interface Props {
  initialTranscript: string;
  detectedLanguage?: string | null;
  onConfirm: (confirmedText: string) => void;
  onDiscard: () => void;
  loading?: boolean;
}

export function TranscriptEditor({
  initialTranscript,
  detectedLanguage,
  onConfirm,
  onDiscard,
  loading = false,
}: Props) {
  const [text, setText] = useState(initialTranscript);
  const isEdited = text.trim() !== initialTranscript.trim();

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!text.trim()) return;
    onConfirm(text.trim());
  }

  return (
    <form className={styles.container} onSubmit={handleSubmit} role="region" aria-label="Transcript preview">
      <div className={styles.titleRow}>
        <h4 className={styles.title}>Review Your Speech Transcript</h4>
        {detectedLanguage && (
          <span className={styles.badge}>Detected: {detectedLanguage}</span>
        )}
      </div>

      <p className={styles.hint}>
        Check for any speech-recognition typos below. Edit if needed, then confirm to proceed.
      </p>

      <textarea
        className={styles.textarea}
        value={text}
        onChange={(e) => setText(e.target.value)}
        disabled={loading}
        aria-label="Editable transcript"
      />

      <div className={styles.actions}>
        <Button
          type="button"
          variant="ghost"
          size="sm"
          onClick={onDiscard}
          disabled={loading}
        >
          Discard & Re-record
        </Button>
        <Button
          type="submit"
          variant="primary"
          size="sm"
          loading={loading}
          disabled={!text.trim()}
        >
          {isEdited ? "Confirm Edited Transcript" : "Confirm Transcript"}
        </Button>
      </div>
    </form>
  );
}

