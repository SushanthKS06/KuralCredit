import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { Recorder } from "../components/voice/Recorder";

vi.mock("../lib/wav", () => ({
  normalizeToWav: vi.fn(async () => new Blob(["wav"], { type: "audio/wav" })),
}));

// Mock useRecorder hook
vi.mock("../hooks/useRecorder", () => ({
  useRecorder: vi.fn(() => ({
    status: "idle",
    seconds: 0,
    error: null,
    audioBlob: null,
    start: vi.fn(),
    stop: vi.fn(),
  })),
}));

import { useRecorder } from "../hooks/useRecorder";
import { normalizeToWav } from "../lib/wav";

describe("Recorder Component", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders idle state with click to speak button", () => {
    const onRecorded = vi.fn();
    render(<Recorder onRecorded={onRecorded} />);

    expect(screen.getByRole("button", { name: /click to speak/i })).toBeDefined();
    expect(screen.getByText(/Voice Input \(Gnani Prisma STT\)/i)).toBeDefined();
  });

  it("triggers start when click to speak button is clicked", () => {
    const startMock = vi.fn();
    (useRecorder as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
      status: "idle",
      seconds: 0,
      error: null,
      audioBlob: null,
      start: startMock,
      stop: vi.fn(),
    });

    const onRecorded = vi.fn();
    render(<Recorder onRecorded={onRecorded} />);

    const startButton = screen.getByRole("button", { name: /click to speak/i });
    fireEvent.click(startButton);

    expect(startMock).toHaveBeenCalledTimes(1);
  });

  it("renders recording state with stop button and active timer", () => {
    const stopMock = vi.fn();
    (useRecorder as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
      status: "recording",
      seconds: 14,
      error: null,
      audioBlob: null,
      start: vi.fn(),
      stop: stopMock,
    });

    const onRecorded = vi.fn();
    render(<Recorder onRecorded={onRecorded} maxSeconds={45} />);

    const stopButton = screen.getByRole("button", { name: /stop recording/i });
    expect(stopButton).toBeDefined();

    fireEvent.click(stopButton);
    expect(stopMock).toHaveBeenCalledTimes(1);
  });

  it("processes a finished recording only once even when callbacks change", async () => {
    const audioBlob = new Blob(["audio"], { type: "audio/webm" });
    (useRecorder as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
      status: "ready",
      seconds: 5,
      error: null,
      audioBlob,
      start: vi.fn(),
      stop: vi.fn(),
    });

    const onRecorded = vi.fn();
    const { rerender } = render(<Recorder onRecorded={onRecorded} />);

    await waitFor(() => expect(onRecorded).toHaveBeenCalledTimes(1));

    rerender(<Recorder onRecorded={vi.fn()} />);
    await waitFor(() => expect(normalizeToWav).toHaveBeenCalledTimes(1));
    expect(onRecorded).toHaveBeenCalledTimes(1);
  });

  it("displays microphone permission or device errors gracefully", () => {
    (useRecorder as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
      status: "error",
      seconds: 0,
      error: "Microphone permission denied by browser",
      audioBlob: null,
      start: vi.fn(),
      stop: vi.fn(),
    });

    const onRecorded = vi.fn();
    render(<Recorder onRecorded={onRecorded} />);

    expect(screen.getByText(/microphone permission denied/i)).toBeDefined();
  });
});
