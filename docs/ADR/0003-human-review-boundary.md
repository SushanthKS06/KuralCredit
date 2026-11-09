# ADR 0003: Strict Human Review Boundary & Non-Lender Invariant

## Status
Accepted

## Context
Automated underwriting systems that attempt autonomous credit decisions frequently encounter regulatory and ethical hazards:
- Algorithmic bias against vernacular expressions or non-standard small-business practices.
- Hallucinated financial calculations.
- Conflation of banking credits with operating revenue, leading to false fraud accusations.

## Decision
We enforce a hard system invariant: **KuralCredit is strictly a clarification and evidence preparation tool, NEVER a lender or underwriting agent.**
1. The application state machine requires transition to `submitted_for_human_review` before any review actions can occur.
2. The application status cannot transition to `review_completed` without explicit human reviewer action and recorded rationale.
3. Neither the AI model nor deterministic rules are permitted to output credit scores, approval amounts, interest rate decisions, or fraud verdicts.
4. Differences between declared revenue and bank deposits are treated as explainable variances requiring applicant context.

## Consequences
- **Positive**: Complete regulatory compliance, zero hallucinated loan commitments, high user trust, and defensible auditability.
- **Negative**: Requires human underwriters to review the evidence packets before final loan origination.

