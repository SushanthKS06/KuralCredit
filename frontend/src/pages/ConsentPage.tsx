import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, errorMessage } from "../api/client";
import { ApplicationProgress } from "../components/application/ApplicationProgress";
import { Button } from "../components/common/Button";
import { LanguageVoiceSelector } from "../components/voice/LanguageVoiceSelector";
import { saveApplicantSession } from "../lib/auth";
import styles from "./ConsentPage.module.css";

export function ConsentPage() {
  const navigate = useNavigate();
  const [applicantName, setApplicantName] = useState("");
  const [businessName, setBusinessName] = useState("");
  const [workflowId, setWorkflowId] = useState("loan_application");
  const [language, setLanguage] = useState("ta-IN");
  const [voice, setVoice] = useState("Trisha");
  const [consentAccepted, setConsentAccepted] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!applicantName.trim() || !businessName.trim() || !consentAccepted) {
      setError("Please fill out all fields and accept the privacy notice.");
      return;
    }
    setError(null);
    setLoading(true);
    try {
      const res = await api.createApplication({
        applicant_name: applicantName.trim(),
        business_name: businessName.trim(),
        language,
        voice,
        consent_accepted: true,
        workflow_id: workflowId,
      });

      saveApplicantSession({
        token: res.token,
        sessionId: res.session_id,
        applicationId: res.application.id,
        displayName: res.application.applicant_name,
        expiresAt: new Date(res.expires_at).toISOString(),
      });

      navigate(`/apply/${res.application.id}/interview`);
    } catch (err: unknown) {
      setError(errorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className={styles.container}>
      <ApplicationProgress currentStage="profile" />

      <h2 className={styles.heading}>Applicant Privacy, Consent &amp; Preferences</h2>
      <p className={styles.subheading}>
        Step 1 of 5: Please review our data handling policy and choose your preferred language and voice.
      </p>

      {error && (
        <div className="alert alert-danger" style={{ marginBottom: "var(--space-4)" }}>
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className={styles.form}>
        <div className={styles.sectionCard}>
          <h3 className={styles.sectionTitle}>1. Workflow &amp; Applicant Information</h3>
          <div className={styles.fieldGroup}>
            <label htmlFor="workflow-select" className={styles.label}>
              Voice Workflow
            </label>
            <select
              id="workflow-select"
              className={styles.input}
              value={workflowId}
              onChange={(e) => setWorkflowId(e.target.value)}
            >
              <option value="loan_application">MSME Loan Clarification (Reference)</option>
              <option value="customer_support_intake">Customer Support Intake (Demonstration)</option>
            </select>
          </div>

          <div className={styles.fieldGroup}>
            <label htmlFor="applicant-name" className={styles.label}>
              {workflowId === "customer_support_intake" ? "Caller / Customer Name" : "Applicant Full Name (Synthetic)"}
            </label>
            <input
              id="applicant-name"
              type="text"
              className={styles.input}
              value={applicantName}
              onChange={(e) => setApplicantName(e.target.value)}
              placeholder={workflowId === "customer_support_intake" ? "e.g. Anand Kumar" : "e.g. Meenakshi Sundaram"}
              required
            />
          </div>

          <div className={styles.fieldGroup}>
            <label htmlFor="business-name" className={styles.label}>
              {workflowId === "customer_support_intake" ? "Organization / Account Reference" : "Enterprise / Business Name"}
            </label>
            <input
              id="business-name"
              type="text"
              className={styles.input}
              value={businessName}
              onChange={(e) => setBusinessName(e.target.value)}
              placeholder={workflowId === "customer_support_intake" ? "e.g. Retail Consumer / Acme Co" : "e.g. Meenakshi Handloom Textiles"}
              required
            />
          </div>
        </div>

        <div className={styles.sectionCard}>
          <h3 className={styles.sectionTitle}>2. Multilingual Voice Settings</h3>
          <p className={styles.sectionSubtitle}>
            Powered by Gnani Prisma Speech-to-Text and Gnani Timbre Text-to-Speech.
          </p>
          <LanguageVoiceSelector
            selectedLanguage={language}
            selectedVoice={voice}
            onLanguageChange={setLanguage}
            onVoiceChange={setVoice}
          />
        </div>

        <div className={styles.termsCard}>
          <h3 className={styles.sectionTitle}>3. Notice &amp; Consent Terms</h3>
          <ul className={styles.termsList}>
            <li>Your spoken answers and uploaded synthetic records will be transcribed via Gnani Prisma.</li>
            <li>Groq GPT-OSS 120B will extract structured candidate facts and generate neutral follow-up questions.</li>
            <li>No credit decisions, approvals, or rejections are made by this system.</li>
            <li>You can inspect and correct every extracted fact before submission.</li>
          </ul>

          <div className={styles.consentRow}>
            <input
              id="consent-checkbox"
              type="checkbox"
              className={styles.consentCheckbox}
              checked={consentAccepted}
              onChange={(e) => setConsentAccepted(e.target.checked)}
              required
            />
            <label htmlFor="consent-checkbox" className={styles.consentLabel}>
              I consent to the collection of declared business facts, voice processing via Gnani, and structured preparation for a human reviewer.
            </label>
          </div>
        </div>

        <div className={styles.actions}>
          <Button
            type="submit"
            size="lg"
            loading={loading}
            disabled={!consentAccepted || !applicantName || !businessName}
          >
            Continue to Voice Interview →
          </Button>
        </div>
      </form>
    </div>
  );
}
