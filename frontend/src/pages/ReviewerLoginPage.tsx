import type { FormEvent } from "react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, errorMessage } from "../api/client";
import { Button } from "../components/common/Button";
import { saveReviewerSession } from "../lib/auth";
import styles from "./ReviewerLoginPage.module.css";

export function ReviewerLoginPage() {
  const navigate = useNavigate();
  const [email, setEmail] = useState("reviewer@kuralcredit.demo");
  const [password, setPassword] = useState("test-reviewer-password");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleLogin(e: FormEvent) {
    e.preventDefault();
    if (!email.trim() || !password.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const res = await api.reviewerLogin(email.trim(), password.trim());
      saveReviewerSession({
        token: res.token,
        sessionId: res.session_id,
        displayName: res.display_name,
        expiresAt: res.expires_at,
      });
      navigate("/reviewer");
    } catch (err: unknown) {
      setError(errorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className={styles.container}>
      <div className={styles.loginCard}>
        <h2 className={styles.title}>Reviewer Portal Login</h2>
        <p className={styles.subtitle}>
          Access the evidence evaluation queue and human review workspace.
        </p>

        {error && (
          <div className="alert alert-danger" style={{ marginBottom: "var(--space-4)" }}>
            {error}
          </div>
        )}

        <form onSubmit={handleLogin} className={styles.form}>
          <div className={styles.fieldGroup}>
            <label htmlFor="reviewer-email" className={styles.label}>
              Email Address
            </label>
            <input
              id="reviewer-email"
              type="email"
              className={styles.input}
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </div>

          <div className={styles.fieldGroup}>
            <label htmlFor="reviewer-password" className={styles.label}>
              Password
            </label>
            <input
              id="reviewer-password"
              type="password"
              className={styles.input}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>

          <Button type="submit" size="md" loading={loading} disabled={!email || !password}>
            Sign In to Reviewer Portal
          </Button>
        </form>

        <div className={styles.demoNotice}>
          <strong>Demo Notice:</strong> Default synthetic reviewer credentials are pre-filled above for hackathon demonstration.
        </div>
      </div>
    </div>
  );
}
