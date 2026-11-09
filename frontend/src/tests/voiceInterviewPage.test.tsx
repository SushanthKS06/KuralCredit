import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type {
  ApplicationDetail,
  Capabilities,
  Conversation,
} from "../api/types";
import { api } from "../api/client";
import { VoiceInterviewPage } from "../pages/VoiceInterviewPage";

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
    getApplication: vi.fn(),
    getConversation: vi.fn(),
    listFacts: vi.fn(),
    synthesize: vi.fn(),
    capabilities: vi.fn(),
  },
  errorMessage: (error: unknown) =>
    error instanceof Error ? error.message : String(error),
}));

vi.mock("../components/voice/Recorder", () => ({
  Recorder: ({ maxSeconds }: { maxSeconds: number }) => (
    <div data-testid="recorder">limit:{maxSeconds}</div>
  ),
}));

vi.mock("../components/voice/AudioPlayer", () => ({
  AudioPlayer: ({ label }: { label: string }) => (
    <div data-testid="audio-player">{label}</div>
  ),
}));

vi.mock("../components/application/ApplicationProgress", () => ({
  ApplicationProgress: () => null,
}));

vi.mock("../components/application/FinancialFactTable", () => ({
  FinancialFactTable: () => null,
}));

const applicationDetail: ApplicationDetail = {
  application: {
    id: "app-1",
    reference: "KC-TEST-1",
    status: "collecting_financial_context",
    applicant_name: "Test Applicant",
    business_name: "Test Textiles",
    business_type: "Textile retail",
    language: "ta-IN",
    voice: "Trisha",
    consent_version: "v1",
    consent_given_at: "2026-01-01T00:00:00Z",
    submitted_at: null,
    review_completed_at: null,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
    is_demo: false,
    demo_scenario: null,
  },
  completeness: {
    can_submit: false,
    missing_fields: [],
    unconfirmed_fields: [],
    missing_documents: [],
    open_clarifications: 1,
    items: [],
  },
};

const conversation: Conversation = {
  application_id: "app-1",
  status: "collecting_financial_context",
  stage: "interview",
  turns: [],
  next_question: null,
  open_clarifications: [
    {
      id: "clar-1",
      application_id: "app-1",
      field_key: "annual_sales",
      question_text: "What does the annual sales figure include?",
      reason: "The declared value differs from the document.",
      expected_answer_type: "amount",
      status: "open",
      priority: 1,
      source: "reconciliation",
      language: "ta-IN",
      created_at: "2026-01-01T00:00:00Z",
      answered_at: null,
      answer_turn_id: null,
    },
  ],
  candidate_facts_count: 0,
  note: null,
};

const capabilities: Capabilities = {
  catalog_version: "2026-01",
  verified_at: "2026-01-01",
  source_urls: [],
  stt_max_audio_seconds: 30,
  stt_supported_formats: ["wav"],
  stt_max_upload_bytes: 15728640,
  tts_supported_formats: ["wav"],
  languages: [],
  defaults: {
    language: "ta-IN",
    voice: "Trisha",
    stt_model: "prisma-v3.0",
    tts_model: "timbre-v2.5",
  },
  providers: {
    provider_mode: "mock",
    mock_mode: true,
    live_provider_calls: false,
    stt_provider: "mock-gnani-prisma",
    tts_provider: "mock-gnani-timbre",
    reasoning_provider: "local_test_adapter",
    gnani_stt_configured: false,
    gnani_tts_configured: false,
    groq_configured: false,
  },
  features: {
    mock_provider_mode: true,
  },
};

function renderPage() {
  return render(
    <MemoryRouter initialEntries={["/apply/app-1/interview"]}>
      <Routes>
        <Route path="/apply/:applicationId/interview" element={<VoiceInterviewPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("VoiceInterviewPage speech wiring", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.getApplication).mockResolvedValue(applicationDetail);
    vi.mocked(api.getConversation).mockResolvedValue(conversation);
    vi.mocked(api.listFacts).mockResolvedValue({ items: [] });
    vi.mocked(api.capabilities).mockResolvedValue(capabilities);
    vi.mocked(api.synthesize).mockResolvedValue(
      new Blob(["wav"], { type: "audio/wav" }),
    );
  });

  it("uses the capability limit, labels mock mode, and speaks the question once", async () => {
    renderPage();

    expect(await screen.findByText(/DEMO \/ MOCK MODE/i)).toBeDefined();
    expect(screen.getByTestId("recorder").textContent).toBe("limit:30");
    expect(
      await screen.findByText("Demo audio (mock Gnani Timbre)"),
    ).toBeDefined();
    expect(api.synthesize).toHaveBeenCalledTimes(1);
    expect(api.synthesize).toHaveBeenCalledWith(
      "app-1",
      "applicant-token",
      conversation.open_clarifications[0].question_text,
      "ta-IN",
      "Trisha",
    );
  });

  it("keeps the text question available and retries failed speech", async () => {
    vi.mocked(api.synthesize)
      .mockRejectedValueOnce(new Error("Timbre unavailable"))
      .mockResolvedValueOnce(new Blob(["wav"], { type: "audio/wav" }));

    renderPage();

    expect(
      await screen.findByText(/Spoken audio is unavailable: Timbre unavailable/i),
    ).toBeDefined();
    expect(
      screen.getByText("What does the annual sales figure include?"),
    ).toBeDefined();

    fireEvent.click(screen.getByRole("button", { name: "Retry audio" }));

    expect(
      await screen.findByText("Demo audio (mock Gnani Timbre)"),
    ).toBeDefined();
    await waitFor(() => expect(api.synthesize).toHaveBeenCalledTimes(2));
  });
});