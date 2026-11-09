import { useCallback, useEffect, useRef, useState } from "react";

export type RecorderStatus = "idle" | "requesting" | "recording" | "processing" | "ready";

const MIME_CANDIDATES = [
  "audio/webm;codecs=opus",
  "audio/webm",
  "audio/mp4",
  "audio/ogg;codecs=opus",
];

export function useRecorder(maxSeconds = 30) {
  const [status, setStatus] = useState<RecorderStatus>("idle");
  const [seconds, setSeconds] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [audioBlob, setAudioBlob] = useState<Blob | null>(null);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const intervalRef = useRef<number | null>(null);

  const cleanup = useCallback(() => {
    if (intervalRef.current !== null) {
      window.clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
    recorderRef.current = null;
  }, []);

  useEffect(() => cleanup, [cleanup]);

  const stop = useCallback(() => {
    const recorder = recorderRef.current;
    if (!recorder || recorder.state === "inactive") {
      return;
    }
    setStatus("processing");
    recorder.stop();
  }, []);

  useEffect(() => {
    if (status === "recording" && seconds >= maxSeconds) {
      stop();
    }
  }, [maxSeconds, seconds, status, stop]);

  const start = useCallback(async () => {
    setError(null);
    setAudioBlob(null);
    setSeconds(0);
    if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === "undefined") {
      setError("This browser does not support microphone recording. Use the text fallback.");
      return;
    }
    setStatus("requesting");
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      });
      streamRef.current = stream;
      const mimeType = MIME_CANDIDATES.find((candidate) =>
        MediaRecorder.isTypeSupported(candidate),
      );
      const recorder = mimeType
        ? new MediaRecorder(stream, { mimeType })
        : new MediaRecorder(stream);
      recorderRef.current = recorder;
      chunksRef.current = [];
      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          chunksRef.current.push(event.data);
        }
      };
      recorder.onerror = () => {
        setError("Recording failed. Please try again or use the text fallback.");
        setStatus("idle");
        cleanup();
      };
      recorder.onstop = () => {
        const blob = new Blob(chunksRef.current, {
          type: recorder.mimeType || "audio/webm",
        });
        cleanup();
        setAudioBlob(blob);
        setStatus("ready");
      };
      recorder.start();
      setStatus("recording");
      intervalRef.current = window.setInterval(() => {
        setSeconds((current) => Math.min(current + 1, maxSeconds));
      }, 1000);
    } catch (caught) {
      cleanup();
      setStatus("idle");
      setError(
        caught instanceof Error && caught.name === "NotAllowedError"
          ? "Microphone access was denied. You can still type your answer."
          : "Could not start the microphone. Use the text fallback instead.",
      );
    }
  }, [cleanup, maxSeconds]);

  const reset = useCallback(() => {
    cleanup();
    setStatus("idle");
    setSeconds(0);
    setAudioBlob(null);
    setError(null);
  }, [cleanup]);

  return { status, seconds, error, audioBlob, start, stop, reset };
}
