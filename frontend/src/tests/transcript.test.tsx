import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { TranscriptEditor } from "../components/voice/TranscriptEditor";

describe("TranscriptEditor Component", () => {
  it("renders the initial transcript in an editable textarea", () => {
    const onConfirm = vi.fn();
    const onDiscard = vi.fn();

    render(
      <TranscriptEditor
        initialTranscript="Last year sales were 18 lakh rupees"
        detectedLanguage="ta-IN"
        onConfirm={onConfirm}
        onDiscard={onDiscard}
      />
    );

    const textarea = screen.getByLabelText("Editable transcript") as HTMLTextAreaElement;
    expect(textarea.value).toBe("Last year sales were 18 lakh rupees");
    expect(screen.getByText("Detected: ta-IN")).toBeDefined();
  });

  it("allows applicant to edit and confirm corrected transcript", () => {
    const onConfirm = vi.fn();
    const onDiscard = vi.fn();

    render(
      <TranscriptEditor
        initialTranscript="Sales were 18 lakh"
        onConfirm={onConfirm}
        onDiscard={onDiscard}
      />
    );

    const textarea = screen.getByLabelText("Editable transcript");
    fireEvent.change(textarea, { target: { value: "Sales were 20 lakh rupees" } });

    const confirmButton = screen.getByRole("button", { name: /confirm/i });
    fireEvent.click(confirmButton);

    expect(onConfirm).toHaveBeenCalledWith("Sales were 20 lakh rupees");
  });

  it("calls onDiscard when discard button is clicked", () => {
    const onConfirm = vi.fn();
    const onDiscard = vi.fn();

    render(
      <TranscriptEditor
        initialTranscript="Unclear speech"
        onConfirm={onConfirm}
        onDiscard={onDiscard}
      />
    );

    const discardButton = screen.getByRole("button", { name: /discard/i });
    fireEvent.click(discardButton);

    expect(onDiscard).toHaveBeenCalled();
  });
});

