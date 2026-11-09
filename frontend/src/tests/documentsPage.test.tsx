import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { DocumentRecord, FinancialFact } from "../api/types";
import { api } from "../api/client";
import { DocumentsPage } from "../pages/DocumentsPage";

vi.mock("../lib/auth", () => ({
  loadApplicantSession: () => ({
    token: "applicant-token",
    sessionId: "session-1",
    applicationId: "app-1",
    displayName: "Test Applicant",
    expiresAt: new Date(Date.now() + 60 * 60 * 1000).toISOString(),
  }),
}));

vi.mock("../api/client", () => ({
  api: {
    listDocuments: vi.fn(),
    listFacts: vi.fn(),
    uploadDocument: vi.fn(),
    deleteDocument: vi.fn(),
    correctFact: vi.fn(),
  },
  errorMessage: (error: unknown) => (error instanceof Error ? error.message : String(error)),
}));

const fact: FinancialFact = {
  id: "fact-1",
  application_id: "app-1",
  field_key: "annual_sales",
  label: "Declared annual sales",
  raw_value: "1800000",
  normalized_value: "1800000",
  display_value: "18,00,000",
  currency: "INR",
  period_start: null,
  period_end: null,
  period_label: "FY2025-26",
  measure_type: "amount",
  source_type: "conversation",
  source_document_id: null,
  source_turn_id: "turn-1",
  source_locator: null,
  provenance_status: "candidate",
  extraction_method: "model",
  model_id: "openai/gpt-oss-120b",
  prompt_version: "v1",
  confidence_estimate: 0.9,
  version: 1,
  supersedes_id: null,
  notes: null,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

const documents: DocumentRecord[] = [];

function renderPage() {
  return render(
    <MemoryRouter initialEntries={["/apply/app-1/documents"]}>
      <Routes>
        <Route path="/apply/:applicationId/documents" element={<DocumentsPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("DocumentsPage fact confirmation", () => {
  beforeEach(() => {
    vi.mocked(api.listDocuments).mockResolvedValue({ items: documents });
    vi.mocked(api.listFacts).mockResolvedValue({ items: [fact] });
    vi.mocked(api.correctFact).mockResolvedValue({
      fact,
      previous_fact_id: null,
      message: "Value confirmed.",
    });
  });

  it("confirms a fact through the API", async () => {
    renderPage();

    const confirmButton = await screen.findByRole("button", { name: "Confirm" });
    fireEvent.click(confirmButton);

    await waitFor(() => {
      expect(api.correctFact).toHaveBeenCalledWith("fact-1", "applicant-token", {
        action: "confirm",
      });
    });
  });
});
