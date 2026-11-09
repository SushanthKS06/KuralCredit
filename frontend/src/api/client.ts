import type {
  Application,
  ApplicationCreatePayload,
  ApplicationCreated,
  ApplicationDetail,
  AuditEvent,
  Capabilities,
  Conversation,
  DocumentRecord,
  DocumentUploadResponse,
  FinancialFact,
  Health,
  Reconciliation,
  ReviewAction,
  ReviewActionRequest,
  ReviewerApplication,
  ReviewerQueue,
  SessionOut,
  SpeechStatus,
  TranscribeResponse,
  TurnResponse,
  WorkflowSummary,
} from "./types";

const API_BASE = (import.meta.env.VITE_API_BASE_URL ?? "/api/v1").replace(/\/$/, "");

export class ApiError extends Error {
  status: number;
  code: string;
  details: unknown;
  requestId: string | null;

  constructor(
    status: number,
    code: string,
    message: string,
    details: unknown = null,
    requestId: string | null = null,
  ) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.details = details;
    this.requestId = requestId;
  }
}

interface RequestOptions {
  method?: string;
  token?: string | null;
  json?: unknown;
  body?: BodyInit;
  headers?: HeadersInit;
  signal?: AbortSignal;
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const headers = new Headers(options.headers);
  if (options.token) {
    headers.set("Authorization", `Bearer ${options.token}`);
  }
  let body = options.body;
  if (options.json !== undefined) {
    headers.set("Content-Type", "application/json");
    body = JSON.stringify(options.json);
  }
  const response = await fetch(`${API_BASE}${path}`, {
    method: options.method ?? "GET",
    headers,
    body,
    signal: options.signal,
  });
  if (!response.ok) {
    throw await toApiError(response);
  }
  if (response.status === 204) {
    return undefined as T;
  }
  const text = await response.text();
  if (!text) {
    return undefined as T;
  }
  return JSON.parse(text) as T;
}

async function requestBlob(path: string, options: RequestOptions = {}): Promise<Blob> {
  const headers = new Headers(options.headers);
  if (options.token) {
    headers.set("Authorization", `Bearer ${options.token}`);
  }
  let body = options.body;
  if (options.json !== undefined) {
    headers.set("Content-Type", "application/json");
    body = JSON.stringify(options.json);
  }
  const response = await fetch(`${API_BASE}${path}`, {
    method: options.method ?? "GET",
    headers,
    body,
    signal: options.signal,
  });
  if (!response.ok) {
    throw await toApiError(response);
  }
  return response.blob();
}

async function toApiError(response: Response): Promise<ApiError> {
  let code = "request_failed";
  let message = `Request failed with status ${response.status}.`;
  let details: unknown = null;
  let requestId: string | null = null;
  try {
    const body = (await response.json()) as {
      error?: { code?: string; message?: string; details?: unknown };
      request_id?: string;
    };
    code = body.error?.code ?? code;
    message = body.error?.message ?? message;
    details = body.error?.details ?? null;
    requestId = body.request_id ?? null;
  } catch {
    // Keep the fallback message when the response is not JSON.
  }
  return new ApiError(response.status, code, message, details, requestId);
}

function queryString(params: Record<string, string | number | undefined>): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== "") {
      search.set(key, String(value));
    }
  }
  const encoded = search.toString();
  return encoded ? `?${encoded}` : "";
}

export const api = {
  health: () => request<Health>("/health"),

  capabilities: () => request<Capabilities>("/capabilities"),

  listWorkflows: () => request<{ items: WorkflowSummary[]; total: number }>("/workflows"),

  getWorkflow: (workflowId: string) => request<Record<string, unknown>>(`/workflows/${workflowId}`),

  speechStatus: () => request<SpeechStatus>("/speech/status"),

  createApplication: (payload: ApplicationCreatePayload) =>
    request<ApplicationCreated>("/applications", { method: "POST", json: payload }),

  getApplication: (applicationId: string, token: string) =>
    request<ApplicationDetail>(`/applications/${applicationId}`, { token }),

  updateApplication: (
    applicationId: string,
    token: string,
    payload: { business_name?: string; business_type?: string; language?: string; voice?: string },
  ) =>
    request<ApplicationDetail>(`/applications/${applicationId}`, {
      method: "PATCH",
      token,
      json: payload,
    }),

  getConversation: (applicationId: string, token: string) =>
    request<Conversation>(`/applications/${applicationId}/conversation`, { token }),

  submitTurn: (
    applicationId: string,
    token: string,
    payload: {
      text: string;
      input_mode: "text" | "audio";
      language?: string;
      stt_request_id?: string;
      stt_latency_ms?: number;
      stt_model?: string;
      confirmed_transcript?: boolean;
      clarification_id?: string;
    },
  ) =>
    request<TurnResponse>(`/applications/${applicationId}/conversation/turns`, {
      method: "POST",
      token,
      json: payload,
    }),

  listFacts: (applicationId: string, token: string) =>
    request<{ items: FinancialFact[] }>(`/applications/${applicationId}/facts`, { token }),

  correctFact: (
    factId: string,
    token: string,
    payload: {
      action: "confirm" | "correct" | "reject";
      normalized_value?: string;
      raw_value?: string;
      notes?: string;
      reason?: string;
    },
  ) =>
    request<{ fact: FinancialFact; previous_fact_id: string | null; message: string }>(
      `/facts/${factId}/corrections`,
      { method: "POST", token, json: payload },
    ),

  listDocuments: (applicationId: string, token: string) =>
    request<{ items: DocumentRecord[] }>(`/applications/${applicationId}/documents`, {
      token,
    }),

  uploadDocument: (
    applicationId: string,
    token: string,
    file: File,
    documentType: string,
  ) => {
    const form = new FormData();
    form.set("file", file);
    form.set("document_type", documentType);
    return request<DocumentUploadResponse>(`/applications/${applicationId}/documents`, {
      method: "POST",
      token,
      body: form,
    });
  },

  deleteDocument: (documentId: string, token: string) =>
    request<{ message: string }>(`/documents/${documentId}`, {
      method: "DELETE",
      token,
    }),

  getReconciliation: (applicationId: string, token: string) =>
    request<Reconciliation>(`/applications/${applicationId}/reconciliation`, { token }),

  getAudit: (applicationId: string, token: string) =>
    request<{ items: AuditEvent[] }>(`/applications/${applicationId}/audit`, { token }),

  submitApplication: (applicationId: string, token: string, idempotencyKey?: string) =>
    request<{ application: Application; message: string }>(
      `/applications/${applicationId}/submit`,
      {
        method: "POST",
        token,
        headers: idempotencyKey ? { "Idempotency-Key": idempotencyKey } : undefined,
        json: { confirm_accuracy: true, acknowledge_no_decision: true },
      },
    ),

  withdrawApplication: (applicationId: string, token: string, reason: string) =>
    request<ApplicationDetail>(`/applications/${applicationId}/withdraw`, {
      method: "POST",
      token,
      json: { reason },
    }),

  transcribe: (
    applicationId: string,
    token: string,
    audio: Blob,
    language: string,
  ) => {
    const form = new FormData();
    form.set("application_id", applicationId);
    form.set("language", language);
    form.set("audio", audio, "recording.wav");
    return request<TranscribeResponse>("/speech/transcribe", {
      method: "POST",
      token,
      body: form,
    });
  },

  synthesize: (
    applicationId: string,
    token: string,
    text: string,
    language: string,
    voice: string,
  ) =>
    requestBlob("/speech/synthesize", {
      method: "POST",
      token,
      json: { application_id: applicationId, text, language, voice },
    }),

  reviewerLogin: (email: string, password: string) =>
    request<SessionOut>("/sessions", {
      method: "POST",
      json: { role: "reviewer", email, password },
    }),

  reviewerQueue: (
    token: string,
    params: { query?: string; status?: string; limit?: number; offset?: number } = {},
  ) => request<ReviewerQueue>(`/reviewer/queue${queryString(params)}`, { token }),

  reviewerApplication: (applicationId: string, token: string) =>
    request<ReviewerApplication>(`/reviewer/applications/${applicationId}`, { token }),

  reviewerAction: (
    applicationId: string,
    token: string,
    payload: ReviewActionRequest,
    idempotencyKey?: string,
  ) =>
    request<ReviewAction>(`/reviewer/applications/${applicationId}/actions`, {
      method: "POST",
      token,
      headers: idempotencyKey ? { "Idempotency-Key": idempotencyKey } : undefined,
      json: payload,
    }),

  reviewerExport: (applicationId: string, token: string) =>
    requestBlob(`/reviewer/applications/${applicationId}/export`, { token }),

  documentFile: (documentId: string, token: string) =>
    requestBlob(`/documents/${documentId}/file`, { token }),
};

export function errorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.status === 401) {
      return "Your session has expired. Please sign in again.";
    }
    return error.message;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return "Something went wrong. Please try again.";
}
