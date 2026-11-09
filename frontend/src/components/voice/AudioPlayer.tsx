import { useEffect, useRef, useState } from "react";
import styles from "./AudioPlayer.module.css";

interface Props {
  audioBlob?: Blob | null;
  audioUrl?: string | null;
  label?: string;
  autoPlay?: boolean;
  onError?: (message: string) => void;
}

export function AudioPlayer({
  audioBlob,
  audioUrl,
  label = "Spoken Response (Gnani Timbre)",
  autoPlay = false,
  onError,
}: Props) {
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [sourceUrl, setSourceUrl] = useState<string | null>(null);
  const [playbackError, setPlaybackError] = useState<string | null>(null);
  const [autoplayBlocked, setAutoplayBlocked] = useState(false);

  useEffect(() => {
    setPlaybackError(null);
    setAutoplayBlocked(false);
    setIsPlaying(false);
    if (audioBlob) {
      const url = URL.createObjectURL(audioBlob);
      setSourceUrl(url);
      return () => {
        URL.revokeObjectURL(url);
      };
    }
    if (audioUrl) {
      setSourceUrl(audioUrl);
    } else {
      setSourceUrl(null);
    }
  }, [audioBlob, audioUrl]);

  useEffect(() => {
    if (!sourceUrl || !autoPlay || !audioRef.current) return;
    audioRef.current.play().catch(() => {
      setAutoplayBlocked(true);
    });
  }, [sourceUrl, autoPlay]);

  if (!sourceUrl) return null;

  function reportError(message: string) {
    setPlaybackError(message);
    onError?.(message);
  }

  function togglePlay() {
    if (!audioRef.current) return;
    if (isPlaying) {
      audioRef.current.pause();
      return;
    }
    audioRef.current.play().catch(() => {
      reportError("Audio could not play automatically. Use the Play button to try again.");
    });
  }

  return (
    <div className={styles.playerContainer} role="region" aria-label="Audio playback">
      <audio
        ref={audioRef}
        src={sourceUrl}
        preload="auto"
        className={styles.audioElement}
        onPlay={() => setIsPlaying(true)}
        onPause={() => setIsPlaying(false)}
        onEnded={() => setIsPlaying(false)}
        onError={() => reportError("The generated audio could not be played in this browser.")}
      />
      <button
        type="button"
        className={styles.playBtn}
        onClick={togglePlay}
        aria-label={isPlaying ? "Pause audio" : "Play spoken response"}
      >
        {isPlaying ? "❚❚" : "▶"}
      </button>
      <span className={styles.label}>{label}</span>
      <span className={styles.status} role="status" aria-live="polite">
        {playbackError
          ? "Playback failed"
          : isPlaying
            ? "Playing"
            : autoplayBlocked
              ? "Ready — press Play"
              : "Ready"}
      </span>
      {playbackError && (
        <span className={styles.errorText} role="alert">
          {playbackError}
        </span>
      )}
    </div>
  );
}
