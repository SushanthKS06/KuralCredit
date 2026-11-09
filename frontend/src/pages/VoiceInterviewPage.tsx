import { useCallback, useEffect, useRef, useState } from "react";
import type { FormEvent } from "react";
import { Link, useParams } from "react-router-dom";
import { api, errorMessage } from "../api/client";
import type { ApplicationDetail, Conversation, FinancialFact } from "../api/types";
import { ApplicationProgress } from "../components/application/ApplicationProgress";
import { FinancialFactTable } from "../components/application/FinancialFactTable";
import { Button } from "../components/common/Button";
import { SessionMissing } from "../components/common/SessionMissing";
import { AudioPlayer } from "../components/voice/AudioPlayer";
import { Recorder } from "../components/voice/Recorder";
import { TranscriptEditor } from "../components/voice/TranscriptEditor";
import { useCapabilities } from "../hooks/useCapabilities";
import { loadApplicantSession } from "../lib/auth";
import styles from "./VoiceInterviewPage.module.css";

type TtsStatus = "idle" | "loading" | "ready" | "error";

const FALLBACK_MAX_AUDIO_SECONDS = 30;

interface SttMetadata {
  stt_request_id: string | null;
  stt_latency_ms: number;
  stt_model: string;
}

export function VoiceInterviewPage() {
  const { applicationId } = useParams<{ applicationId: string }>();
  const session = applicationId ? loadApplicantSession(applicationId) : null;
  const token = session?.token ?? null;

  const [application, setApplication] = useState<ApplicationDetail | null>(null);
  const [conversation, setConversation] = useState<Conversation | null>(null);
  const [facts, setFacts] = useState<FinancialFact[]>([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [sttPending, setSttPending] = useState(false);
  const [previewTranscript, setPreviewTranscript] = useState<string | null>(null);
  const [detectedLang, setDetectedLang] = useState<string | null>(null);
  const [sttMetadata, setSttMetadata] = useState<SttMetadata | null>(null);
  const [textInput, setTextInput] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [ttsStatus, setTtsStatus] = useState<TtsStatus>("idle");
  const [ttsBlob, setTtsBlob] = useState<Blob | null>(null);
  const [ttsError, setTtsError] = useState<string | null>(null);
  const [ttsRetry, setTtsRetry] = useState(0);
  const ttsRequestRef = useRef<string | null>(null);
  const { capabilities, error: capabilitiesError } = useCapabilities();

  const refreshData = useCallback(async () => {
    if (!applicationId || !token) {
      setLoading(false);
      return;
    }
    try {
      const [appData, convData, factsData] = await Promise.all([
        api.getApplication(applicationId, token),
        api.getConversation(applicationId, token),
        api.listFacts(applicationId, token),
      ]);
      setApplication(appData);
      setConversation(convData);
      setFacts(factsData.items);
      setError(null);
    } catch (err: unknown) {
      setError(errorMessage(err));
    } finally {
      setLoading(false);
    }
  }, [applicationId, token]);

  useEffect(() => {
    void refreshData();
  }, [refreshData]);

  const currentClarification = conversation?.open_clarifications?.[0] ?? null;
  const currentQuestionKey = currentClarification
    ? `clarification:${currentClarification.id}`
    : conversation?.next_question
      ? `workflow:${conversation.next_question.question_id}`
      : null;
  const currentQuestionText = currentClarification
    ? currentClarification.question_text
    : conversation?.next_question?.prompt ?? null;
  const ttsLanguage = application?.application.language ?? null;
  const ttsVoice = application?.application.voice ?? null;

  useEffect(() => {
    if (
      !applicationId ||
      !token ||
      !currentQuestionKey ||
      !currentQuestionText ||
      !ttsLanguage ||
      !ttsVoice
    ) {
      return;
    }
    const requestToken = `${currentQuestionKey}:${ttsRetry}`;
    if (ttsRequestRef.current === requestToken) {
      return;
    }
    ttsRequestRef.current = requestToken;
    setTtsStatus("loading");
    setTtsBlob(null);
    setTtsError(null);
    api
      .synthesize(
        applicationId,
        token,
        currentQuestionText,
        ttsLanguage,
        ttsVoice,
      )
      .then((blob) => {
        if (ttsRequestRef.current !== requestToken) return;
        setTtsBlob(blob);
        setTtsStatus("ready");
      })
      .catch((err: unknown) => {
        if (ttsRequestRef.current !== requestToken) return;
        setTtsError(errorMessage(err));
        setTtsStatus("error");
      });
    return () => {
      if (ttsRequestRef.current === requestToken) {
        ttsRequestRef.current = null;
      }
    };
  }, [
    applicationId,
    currentQuestionKey,
    currentQuestionText,
    token,
    ttsLanguage,
    ttsVoice,
    ttsRetry,
  ]);

  function retryTts() {
    ttsRequestRef.current = null;
    setTtsRetry((value) => value + 1);
  }

  async function handleAudioRecorded(wavBlob: Blob) {
    if (!applicationId || !token) return;
    setError(null);
    setSttPending(true);
    try {
      const lang = application?.application.language || "ta-IN";
      const res = await api.transcribe(applicationId, token, wavBlob, lang);
      setPreviewTranscript(res.transcript);
      setDetectedLang(res.detected_language);
      setSttMetadata({
        stt_request_id: res.request_id,
        stt_latency_ms: res.latency_ms,
        stt_model: res.model,
      });
    } catch (err: unknown) {
      setError("Speech-to-text error: " + errorMessage(err));
    } finally {
      setSttPending(false);
    }
  }

  async function handleConfirmTranscript(confirmedText: string) {
    if (!applicationId || !token) return;
    setSubmitting(true);
    setError(null);
    try {
      await api.submitTurn(applicationId, token, {
        text: confirmedText,
        input_mode: "audio",
        language: application?.application.language,
        stt_request_id: sttMetadata?.stt_request_id ?? undefined,
        stt_latency_ms: sttMetadata?.stt_latency_ms,
        stt_model: sttMetadata?.stt_model,
        confirmed_transcript: true,
      });
      setPreviewTranscript(null);
      setSttMetadata(null);
      await refreshData();
    } catch (err: unknown) {
      setError("Failed to process conversation turn: " + errorMessage(err));
    } finally {
      setSubmitting(false);
    }
  }

  async function handleTextSubmit(e: FormEvent) {
    e.preventDefault();
    if (!applicationId || !token || !textInput.trim()) return;
    setSubmitting(true);
    setError(null);
    try {
      await api.submitTurn(applicationId, token, {
        text: textInput.trim(),
        input_mode: "text",
        language: application?.application.language,
        confirmed_transcript: true,
      });
      setTextInput("");
      await refreshData();
    } catch (err: unknown) {
      setError("Failed to submit text turn: " + errorMessage(err));
    } finally {
      setSubmitting(false);
    }
  }

  async function handleCorrectFact(factId: string, action: "confirm" | "correct" | "reject", newValue?: string) {
    if (!token) return;
    try {
      await api.correctFact(factId, token, {
        action,
        normalized_value: newValue,
      });
      await refreshData();
    } catch (err: unknown) {
      setError("Failed to update fact: " + errorMessage(err));
    }
  }

  if (!session) {
    return <SessionMissing />;
  }

  if (loading) {
    return <div style={{ padding: "var(--space-8)", textAlign: "center" }}>Loading interview session...</div>;
  }

  return (
    <div className={styles.container}>
      <ApplicationProgress currentStage="interview" />

      <div className={styles.topBar}>
        <div>
          <h2 className={styles.pageTitle}>Voice Clarification &amp; Declaration</h2>
          <span className={styles.metaText}>
            Applicant: <strong>{application?.application.applicant_name}</strong> • Business: {application?.application.business_name} (Language: {application?.application.language})
          </span>
          {capabilities?.providers.mock_mode && (
            <span className={styles.mockBadge} role="status">
              DEMO / MOCK MODE — no live Gnani or Groq call
            </span>
          )}
        </div>
        <Link to={`/apply/${applicationId}/documents`}>
          <Button variant="secondary">Next: Upload Documents →</Button>
        </Link>
      </div>

      {error && (
        <div className="alert alert-danger" style={{ marginBottom: "var(--space-4)" }}>
          {error}
        </div>
      )}

      {/* Latest Assistant Question or Initial Declaration Prompt */}
      {conversation?.open_clarifications && conversation.open_clarifications.length > 0 ? (
        <div className={styles.questionCard}>
          <span className={styles.questionBadge}>
            Current Clarification Question
          </span>
          <h3 className={styles.questionHeading}>
            {conversation.open_clarifications[0].question_text}
          </h3>
          {conversation.open_clarifications[0].reason && (
            <p className={styles.questionHelp}>
              <strong>Context:</strong> {conversation.open_clarifications[0].reason}
            </p>
          )}
          <div className={styles.voiceResponse}>
            {ttsStatus === "loading" && (
              <span className={styles.transcribingStatus} role="status">
                <span className={styles.spinner} />
                <span>Generating spoken prompt with Gnani Timbre...</span>
              </span>
            )}
            {ttsStatus === "ready" && ttsBlob && (
              <AudioPlayer
                audioBlob={ttsBlob}
                autoPlay
                label={
                  capabilities?.providers.mock_mode
                    ? "Demo audio (mock Gnani Timbre)"
                    : "Spoken clarification (Gnani Timbre)"
                }
              />
            )}
            {ttsStatus === "error" && (
              <div className={styles.ttsError} role="alert">
                <span>
                  Spoken audio is unavailable{ttsError ? `: ${ttsError}` : "."} The text
                  question above is still available.
                </span>
                <Button type="button" size="sm" variant="secondary" onClick={retryTts}>
                  Retry audio
                </Button>
              </div>
            )}
          </div>
        </div>
      ) : (
        <div className={styles.questionCard}>
          <span className={styles.questionBadge}>
            {conversation?.next_question ? "Current Question" : "Initial Declaration Prompt"}
          </span>
          <h3 className={styles.questionHeading}>
            {conversation?.next_question?.prompt ??
              "Please tell us about your business turnover, last year sales, and GST filing status in your own words."}
          </h3>
          <p className={styles.questionHelp}>
            {conversation?.next_question?.reason ??
              "For example: \"My business is a textile retail shop in Madurai. Last year annual sales were 18 lakh rupees. GST turnover filed was 16.5 lakh.\""}
          </p>
          <div className={styles.voiceResponse}>
            {ttsStatus === "loading" && (
              <span className={styles.transcribingStatus} role="status">
                <span className={styles.spinner} />
                <span>Generating spoken prompt with Gnani Timbre...</span>
              </span>
            )}
            {ttsStatus === "ready" && ttsBlob && (
              <AudioPlayer
                audioBlob={ttsBlob}
                autoPlay
                label={
                  capabilities?.providers.mock_mode
                    ? "Demo audio (mock Gnani Timbre)"
                    : "Spoken question (Gnani Timbre)"
                }
              />
            )}
            {ttsStatus === "error" && (
              <div className={styles.ttsError} role="alert">
                <span>
                  Spoken audio is unavailable{ttsError ? `: ${ttsError}` : "."} The text
                  question above is still available.
                </span>
                <Button type="button" size="sm" variant="secondary" onClick={retryTts}>
                  Retry audio
                </Button>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Audio Capture */}
      {capabilitiesError && (
        <p className={styles.capabilityWarning} role="status">
          Speech capabilities could not be refreshed. Using safe defaults
          ({FALLBACK_MAX_AUDIO_SECONDS}s, WAV). {capabilitiesError}
        </p>
      )}
      <Recorder
        onRecorded={handleAudioRecorded}
        disabled={sttPending || submitting}
        maxSeconds={
          capabilities?.stt_max_audio_seconds ?? FALLBACK_MAX_AUDIO_SECONDS
        }
      />

      {sttPending && (
        <div className={styles.transcribingStatus}>
          <span className={styles.spinner} />
          <span>Transcribing audio using Gnani Prisma STT...</span>
        </div>
      )}

      {/* Transcript Editor & Confirmation */}
      {previewTranscript && (
        <TranscriptEditor
          initialTranscript={previewTranscript}
          detectedLanguage={detectedLang}
          onConfirm={handleConfirmTranscript}
          onDiscard={() => setPreviewTranscript(null)}
          loading={submitting}
        />
      )}

      {/* Text fallback input */}
      <div className={styles.textFallback}>
        <h4 className={styles.textFallbackTitle}>Text-only Fallback:</h4>
        <form onSubmit={handleTextSubmit} className={styles.textFallbackForm}>
          <input
            type="text"
            className={styles.textInput}
            placeholder="Type your response or figures here if microphone is unavailable..."
            value={textInput}
            onChange={(e) => setTextInput(e.target.value)}
            disabled={submitting}
          />
          <Button type="submit" size="sm" loading={submitting} disabled={!textInput.trim()}>
            Submit Text
          </Button>
        </form>
      </div>

      {/* Candidate Facts Table */}
      <FinancialFactTable facts={facts} onCorrectFact={handleCorrectFact} />

      <div className={styles.actionRow}>
        <Link to={`/apply/${applicationId}/documents`}>
          <Button size="lg">Proceed to Upload Documents →</Button>
        </Link>
      </div>
    </div>
  );
}
