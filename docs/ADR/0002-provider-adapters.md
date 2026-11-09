# ADR 0002: Abstract Provider Adapters for Speech and Reasoning

## Status
Accepted

## Context
KuralCredit relies on external providers:
1. **Gnani Prisma STT** and **Timbre TTS** for Indian speech AI.
2. **Groq** for high-throughput LLM reasoning (`openai/gpt-oss-120b`).

Hardcoding API URLs, headers, or request shapes across services leads to tight coupling, makes automated unit/integration testing difficult, and risks silent failures during network outages.

## Decision
We establish explicit abstract base classes:
- `SpeechToTextProvider`
- `TextToSpeechProvider`
- `ReasoningProvider`

We provide one concrete implementation for each:
1. `GnaniSTTProvider`
2. `GnaniTTSProvider`
3. `GroqReasoningProvider`

A centralized `ProviderRegistry` constructs providers from validated typed settings. `PROVIDER_MODE=real` selects the concrete provider adapters and fails when credentials are missing. `PROVIDER_MODE=mock` selects deterministic, clearly labelled mock adapters for tests and offline demos; mock mode is rejected in production. There is no silent fallback between the two modes. The test suite also injects local test doubles through FastAPI dependency overrides.

## Consequences
- **Positive**: Clean provider separation, zero secret leakage to UI, explicit real/mock behavior, and the ability to switch models via configuration.
- **Negative**: The test suite must maintain test doubles synchronized with the provider interfaces, and reviewers must check the reported provider mode before interpreting demo output.

