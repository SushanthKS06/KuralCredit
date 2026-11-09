import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { FinancialFactTable } from "../components/application/FinancialFactTable";
import type { FinancialFact } from "../api/types";

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

describe("FinancialFactTable", () => {
  it("calls the confirmation handler with the fact id", () => {
    const onCorrectFact = vi.fn();
    render(<FinancialFactTable facts={[fact]} onCorrectFact={onCorrectFact} />);

    fireEvent.click(screen.getByRole("button", { name: "Confirm" }));

    expect(onCorrectFact).toHaveBeenCalledWith("fact-1", "confirm");
  });

  it("does not render actions when no handler is provided", () => {
    render(<FinancialFactTable facts={[fact]} />);

    expect(screen.queryByRole("button", { name: "Confirm" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Edit" })).toBeNull();
  });

  it("saves an edited value through the correction handler", () => {
    const onCorrectFact = vi.fn();
    render(<FinancialFactTable facts={[fact]} onCorrectFact={onCorrectFact} />);

    fireEvent.click(screen.getByRole("button", { name: "Edit" }));
    fireEvent.change(screen.getByPlaceholderText("e.g. 1800000"), {
      target: { value: "2000000" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Save" }));

    expect(onCorrectFact).toHaveBeenCalledWith("fact-1", "correct", "2000000");
  });
});
