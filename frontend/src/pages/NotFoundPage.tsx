import { Link } from "react-router-dom";
import { Button } from "../components/common/Button";

export function NotFoundPage() {
  return (
    <div style={{ maxWidth: "600px", margin: "var(--space-12) auto", textAlign: "center", padding: "0 var(--space-4)" }}>
      <h1 style={{ fontSize: "var(--text-3xl)", color: "var(--text-primary)", marginBottom: "var(--space-2)" }}>
        404
      </h1>
      <h2 style={{ fontSize: "var(--text-xl)", color: "var(--text-secondary)", marginBottom: "var(--space-4)" }}>
        Page Not Found
      </h2>
      <p style={{ color: "var(--text-secondary)", marginBottom: "var(--space-6)" }}>
        The page you are looking for does not exist or has been moved.
      </p>
      <Link to="/">
        <Button size="md">Return to Home</Button>
      </Link>
    </div>
  );
}
