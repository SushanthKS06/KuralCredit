import { Link } from "react-router-dom";
import { Button } from "./Button";

interface Props {
  title?: string;
  message?: string;
}

export function SessionMissing({
  title = "Application session not found",
  message = "Your application session is missing or has expired. Start a new application to continue.",
}: Props) {
  return (
    <div
      role="alert"
      style={{
        maxWidth: "640px",
        margin: "var(--space-12) auto",
        padding: "var(--space-6)",
        textAlign: "center",
      }}
    >
      <h2 style={{ fontSize: "var(--text-xl)", marginBottom: "var(--space-3)" }}>{title}</h2>
      <p style={{ color: "var(--text-secondary)", marginBottom: "var(--space-6)" }}>{message}</p>
      <Link to="/consent">
        <Button size="md">Start a New Application</Button>
      </Link>
    </div>
  );
}
