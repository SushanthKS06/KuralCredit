import { useEffect, useRef, useState } from "react";
import type { ChangeEvent } from "react";
import { useRecorder } from "../../hooks/useRecorder";
import { normalizeToWav } from "../../lib/wav";
import styles from "./Recorder.module.css";

interface Props {
  onRecorded: (wavBlob: Blob) => void;
  disabled?: boolean;
  maxSeconds?: number;
}

export function Recorder({ onRecorded, disabled = false, maxSeconds = 30 }: Props) {
  const { status, seconds, error: recorderError, audioBlob, start, stop } = useRecorder(maxSeconds);
  const [conversionError, setConversionError] = useState<string | null>(null);
  const [converting, setConverting] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const onRecordedRef = useRef(onRecorded);
  const processedBlobRef = useRef<Blob | null>(null);

  useEffect(() => {
    onRecordedRef.current = onRecorded;
  }, [onRecorded]);

  async function handleStop() {
    stop();
  }

  useEffect(() => {
    if (!audioBlob || status !== "ready" || processedBlobRef.current === audioBlob) {
      return;
    }
    processedBlobRef.current = audioBlob;
    setConverting(true);
    setConversionError(null);
    normalizeToWav(audioBlob)
      .then((wav) => {
        onRecordedRef.current(wav);
      })
      .catch((err: unknown) => {
        setConversionError(
          "Audio normalization failed: " + (err instanceof Error ? err.message : String(err)),
        );
      })
      .finally(() => {
        setConverting(false);
      });
  }, [audioBlob, status]);

  async function handleFileUpload(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setConverting(true);
    setConversionError(null);
    try {
      const wav = await normalizeToWav(file);
      onRecordedRef.current(wav);
    } catch (err: unknown) {
      setConversionError(
        "Could not process uploaded audio: " + (err instanceof Error ? err.message : String(err)),
      );
    } finally {
      setConverting(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  }

  const isRecording = status === "recording";
  const error = recorderError || conversionError;

  return (
    <div className={styles.recorderCard} role="region" aria-label="Audio Recorder">
      <div className={styles.header}>
        <h4 className={styles.title}>Voice Input (Gnani Prisma STT)</h4>
        <span className={styles.timer} aria-live="polite">
          {isRecording
            ? `00:${seconds.toString().padStart(2, "0")} / 00:${maxSeconds.toString().padStart(2, "0")}`
            : `Limit: ${maxSeconds}s`}
        </span>
      </div>
      <p className={styles.helperText}>
        Recording stops automatically at the configured {maxSeconds}-second provider limit.
      </p>

      {error && <div className={styles.errorBanner} role="alert">{error}</div>}

      <div className={styles.controls}>
        {!isRecording ? (
          <button
            type="button"
            className={styles.recordBtn}
            onClick={start}
            disabled={disabled || converting || status === "requesting"}
          >
            <div className={styles.waveform}>
              <span className={styles.bar} />
              <span className={styles.bar} />
              <span className={styles.bar} />
              <span className={styles.bar} />
              <span className={styles.bar} />
            </div>
            {status === "requesting" ? "Requesting Mic..." : "Click to Speak"}
          </button>
        ) : (
          <button
            type="button"
            className={`${styles.recordBtn} ${styles.recording}`}
            onClick={handleStop}
          >
            <div className={styles.waveform}>
              <span className={styles.bar} />
              <span className={styles.bar} />
              <span className={styles.bar} />
              <span className={styles.bar} />
              <span className={styles.bar} />
            </div>
            Stop Recording
          </button>
        )}

        {converting && (
          <div className={styles.convertingNote}>
            <span className={styles.convertingSpinner} />
            <span>Normalizing audio to 16kHz WAV...</span>
          </div>
        )}
      </div>

      <div className={styles.fileFallback}>
        <label className={styles.fallbackLabel} htmlFor="audio-upload-input">
          Or upload pre-recorded audio (WAV, MP3, WebM fallback):
        </label>
        <input
          id="audio-upload-input"
          ref={fileInputRef}
          type="file"
          accept="audio/*"
          className={styles.fileInput}
          onChange={handleFileUpload}
          disabled={disabled || isRecording || converting}
        />
      </div>
    </div>
  );
}
