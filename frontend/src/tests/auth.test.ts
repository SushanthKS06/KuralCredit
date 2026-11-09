import { beforeEach, describe, expect, it } from "vitest";
import {
  loadApplicantSession,
  loadReviewerSession,
  saveApplicantSession,
  saveReviewerSession,
} from "../lib/auth";

const future = () => new Date(Date.now() + 60 * 60 * 1000).toISOString();
const past = () => new Date(Date.now() - 60 * 1000).toISOString();

describe("session storage", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("loads a valid applicant session", () => {
    saveApplicantSession({
      token: "token",
      sessionId: "session",
      applicationId: "app-1",
      displayName: "Test Applicant",
      expiresAt: future(),
    });

    expect(loadApplicantSession("app-1")?.displayName).toBe("Test Applicant");
  });

  it("drops an expired applicant session", () => {
    saveApplicantSession({
      token: "token",
      sessionId: "session",
      applicationId: "app-1",
      displayName: "Test Applicant",
      expiresAt: past(),
    });

    expect(loadApplicantSession("app-1")).toBeNull();
    expect(localStorage.getItem("kuralcredit.applicant.app-1")).toBeNull();
  });

  it("drops an expired reviewer session", () => {
    saveReviewerSession({
      token: "token",
      sessionId: "session",
      displayName: "Test Reviewer",
      expiresAt: past(),
    });

    expect(loadReviewerSession()).toBeNull();
    expect(localStorage.getItem("kuralcredit.reviewer")).toBeNull();
  });

  it("ignores sessions whose application id does not match", () => {
    saveApplicantSession({
      token: "token",
      sessionId: "session",
      applicationId: "app-1",
      displayName: "Test Applicant",
      expiresAt: future(),
    });

    expect(loadApplicantSession("app-2")).toBeNull();
  });
});
