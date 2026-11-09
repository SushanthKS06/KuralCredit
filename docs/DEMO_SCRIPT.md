# KuralCredit â€” 3-Minute Demo Script & Presentation Guide

**Target Demo Duration:** 3 Minutes  
**Scenario:** Meenakshi Handloom Textiles (Madurai, Tamil Nadu)  
**Synthetic Data Notice:** All names, numbers, account figures, and transactions are synthetic.

## Before the Demo

- **Real-provider demo:** rotate exposed credentials, set
  `PROVIDER_MODE=real`, configure the private `.env`, and run
  `scripts/run_provider_smoke_tests.py --live` first.
- **Offline/mock demo:** set `PROVIDER_MODE=mock`. The UI displays a mock
  badge, and TTS playback uses deterministic mock audio. Do not describe
  mock audio as a live Gnani Timbre voice sample.
- Live provider verification is currently **BLOCKED** until credential
  rotation. See `docs/READINESS_REPORT.md`.

---

## Timeline & Narrative Walkthrough

### 0:00 â€“ 0:25 | The Problem & Vision
- **Speaker:** *"Small business borrowers in India often struggle with digital loan forms. They speak Tamil, Tanglish, or Hindi, manage a mix of cash and digital receipts, and find standard banking forms rigid. This is KuralCredit â€” a voice-first clarification and evidence preparation system powered by Gnani Prisma, Gnani Timbre, and Groq GPT-OSS 120B."*
- **Action:** Open Landing Page. Highlight the tagline: *"Speak naturally. Clarify confidently. Submit an evidence-backed application."* Note the explicit boundary disclosure: *KuralCredit does NOT make loan decisions.*

### 0:25 â€“ 0:55 | Voice Interview in Tamil / Tanglish
- **Speaker:** *"The borrower selects Tamil with Gnani's Trisha voice and explains their business turnover naturally."*
- **Action:**
  1. Click *"Start New Application"*.
  2. In the Voice Interview page, speak or play the Tamil utterance:
     > *"à®Žà®™à¯à®• à®•à®Ÿà¯ˆ à®šà¯†à®©à¯à®± à®µà®°à¯à®Ÿ à®µà®¿à®±à¯à®ªà®©à¯ˆ à®ªà®¤à®¿à®©à¯†à®Ÿà¯à®Ÿà¯ à®²à®Ÿà¯à®šà®®à¯ à®°à¯‚à®ªà®¾à®¯à¯, à®œà®¿à®Žà®¸à¯à®Ÿà®¿ à®µà®¿à®±à¯à®±à¯à®®à¯à®¤à®²à¯ à®ªà®¤à®¿à®©à®¾à®±à¯ à®²à®Ÿà¯à®šà®®à¯ à®à®®à¯à®ªà®¤à®¾à®¯à®¿à®°à®®à¯."*
     *(Our shop last year sales were 18 lakh rupees, GST turnover was 16.5 lakh).*
  3. Show the transcript returned by **Gnani Prisma STT** (in mock mode, the mock badge is visible).
  4. Demonstrate the **Transcript Editor**: the applicant can edit or confirm before downstream processing.

### 0:55 â€“ 1:30 | Candidate Fact Extraction & Document Upload
- **Speaker:** *"Groq GPT-OSS 120B extracts candidate financial facts into a strict schema, while deterministic Python Decimal normalizes the Indian number scales â€” 18 lakh becomes â‚¹18,00,000."*
- **Action:**
  1. Show extracted candidate facts in the Financial Facts Table with `candidate` status.
  2. Navigate to **Documents Page**.
  3. Upload `sample_bank_statement.csv`.
  4. Show document parsed with SHA-256 hash and total credits of â‚¹34,00,000.

### 1:30 â€“ 2:10 | Deterministic Reconciliation & Spoken Clarification
- **Speaker:** *"Here is the critical distinction: Bank credits of â‚¹34L exceed declared sales of â‚¹18L. In traditional software, this triggers a false fraud alert. But in KuralCredit, deterministic rules recognize that bank credits are not automatically revenue! The system generates a neutral clarification question."*
- **Action:**
  1. Open the **Clarification Review Page**.
  2. Show **EvidencePanel**: highlights the variance without calling it fraud.
  3. Play the **Gnani Timbre TTS** spoken audio asking (mock mode labels the audio as a mock):
     > *"Bank credits of â‚¹34 Lakhs exceed declared sales of â‚¹18 Lakhs. Were there personal transfers, loans, or cash counter receipts?"*
  4. Applicant replies (by voice or text):
     > *"â‚¹4,00,000 was a personal transfer from savings account, and counter cash sales are recorded in our sales register."*
  5. The explanation is attached directly to the reconciliation item.

### 2:10 â€“ 2:45 | Reviewer Command Center & Evidence Packet
- **Speaker:** *"Now we switch to Persona B: The institutional credit reviewer."*
- **Action:**
  1. Sign in to `/reviewer` with demo credentials.
  2. Open the application from the queue.
  3. View side-by-side evidence: declared facts vs bank statement rows vs applicant explanation.
  4. Verify the fact with reviewer rationale: *"Cross-checked against bank statement receipts and physical sales register."*
  5. Click *"Download Evidence Packet (JSON)"* to show the complete, auditable packet.

### 2:45 â€“ 3:00 | Closing Pitch
- **Speaker:** *"KuralCredit doesn't decide who gets credit. It helps small business owners explain their records in their own voice, and equips human underwriters with transparent, evidence-backed packets."*
- **Final Slide:** Thank you! Powered by Gnani Prisma, Gnani Timbre, and Groq GPT-OSS 120B.


