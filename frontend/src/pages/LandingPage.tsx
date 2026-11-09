import { Link } from "react-router-dom";
import { Button } from "../components/common/Button";
import styles from "./LandingPage.module.css";

const FEATURES = [
  {
    icon: "🎙️",
    title: "Voice-First Multilingual",
    desc: "Speak Tamil, Tanglish, Hindi or English. Gnani Prisma STT transcribes your words accurately.",
  },
  {
    icon: "🧠",
    title: "AI-Assisted Extraction",
    desc: "Groq GPT-OSS 120B extracts structured financial facts from your speech and uploaded records.",
  },
  {
    icon: "📄",
    title: "Document Reconciliation",
    desc: "Bank statements and GST summaries are compared using deterministic rules — no guesswork.",
  },
  {
    icon: "🔍",
    title: "Human Review Packet",
    desc: "A traceable, evidence-backed packet is routed to a human credit officer — no autonomous decisions.",
  },
];

export function LandingPage() {
  return (
    <div className={styles.page}>
      {/* Hero */}
      <section className={styles.hero}>
        <div className={styles.heroBadge}>
          Gnani Prisma STT&nbsp;•&nbsp;Timbre TTS&nbsp;•&nbsp;Groq GPT-OSS 120B
        </div>
        <h1 className={styles.heroTitle}>KuralCredit</h1>
        <p className={styles.heroTagline}>
          Speak naturally. Clarify confidently.<br />
          Submit an evidence-backed application.
        </p>
        <div className={styles.heroCta}>
          <Link to="/consent">
            <Button size="lg">Start New Application →</Button>
          </Link>
          <Link to="/reviewer/login">
            <Button size="lg" variant="ghost">Reviewer Portal</Button>
          </Link>
        </div>
      </section>

      {/* Feature grid */}
      <section className={styles.featureGrid}>
        {FEATURES.map((f) => (
          <div key={f.title} className={styles.featureCard}>
            <span className={styles.featureIcon}>{f.icon}</span>
            <h3 className={styles.featureTitle}>{f.title}</h3>
            <p className={styles.featureDesc}>{f.desc}</p>
          </div>
        ))}
      </section>

      {/* How it works */}
      <section className={styles.howItWorks}>
        <h2 className={styles.sectionHeading}>How It Works</h2>
        <ol className={styles.stepList}>
          {[
            ["Consent & Profile", "Enter your name, business, choose language and voice."],
            ["Voice Interview", "Speak your turnover, seasonality, and GST status in your language."],
            ["Upload Records", "Upload synthetic bank statements and GST summaries."],
            ["Clarify & Review", "Answer follow-up questions; inspect and correct every extracted fact."],
            ["Human Review", "A traceable completeness packet is submitted for a human credit officer."],
          ].map(([title, desc], i) => (
            <li key={i} className={styles.stepItem}>
              <span className={styles.stepNumber}>{i + 1}</span>
              <div>
                <strong>{title}</strong>
                <p>{desc}</p>
              </div>
            </li>
          ))}
        </ol>
      </section>

      {/* Disclosure */}
      <div className={styles.disclosure}>
        <strong>Product Boundaries &amp; Disclosures:&nbsp;</strong>
        KuralCredit is NOT a lender, credit bureau, or underwriting engine. It does not issue credit
        approvals, rejections, risk grades, or fraud labels. Bank statement credits are never assumed
        to equal business revenue. All final decisions require human review.
      </div>
    </div>
  );
}
