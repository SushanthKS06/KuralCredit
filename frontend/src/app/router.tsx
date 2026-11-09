import { Routes, Route } from "react-router-dom";
import { AppShell } from "../components/layout/AppShell";
import { LandingPage } from "../pages/LandingPage";
import { ConsentPage } from "../pages/ConsentPage";
import { ApplicantDashboard } from "../pages/ApplicantDashboard";
import { VoiceInterviewPage } from "../pages/VoiceInterviewPage";
import { DocumentsPage } from "../pages/DocumentsPage";
import { ApplicationReviewPage } from "../pages/ApplicationReviewPage";
import { ReviewerLoginPage } from "../pages/ReviewerLoginPage";
import { ReviewerDashboard } from "../pages/ReviewerDashboard";
import { ReviewerApplicationPage } from "../pages/ReviewerApplicationPage";
import { NotFoundPage } from "../pages/NotFoundPage";

export function AppRouter() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route index element={<LandingPage />} />
        <Route path="consent" element={<ConsentPage />} />
        <Route path="apply/:applicationId" element={<ApplicantDashboard />} />
        <Route path="apply/:applicationId/interview" element={<VoiceInterviewPage />} />
        <Route path="apply/:applicationId/documents" element={<DocumentsPage />} />
        <Route path="apply/:applicationId/review" element={<ApplicationReviewPage />} />
        <Route path="reviewer/login" element={<ReviewerLoginPage />} />
        <Route path="reviewer" element={<ReviewerDashboard />} />
        <Route path="reviewer/:applicationId" element={<ReviewerApplicationPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  );
}

