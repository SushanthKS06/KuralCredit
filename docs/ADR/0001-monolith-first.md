# ADR 0001: Monolithic Architecture for Hackathon & Local Operation

## Status
Accepted

## Context
A complete loan clarification application requires audio processing, document parsing, deterministic financial comparisons, LLM reasoning, conversational state tracking, and a reviewer workspace. Distributed architectures (microservices, Kafka, Redis, vector databases) add significant setup friction, operational failure modes, and latency overhead without business justification for an MVP or hackathon product.

## Decision
We implement KuralCredit as a unified, well-factored monolith:
- A single FastAPI backend containing domain services, document parsers, and provider adapters.
- SQLite default storage for instant, zero-dependency local setup, with PostgreSQL compatibility for deployment.
- A single React 19 / Vite frontend built into static files served directly by the FastAPI backend or separately via a dev server.

## Consequences
- **Positive**: Single command startup, zero docker container dependencies required for development, unified database transactions, immediate debugging.
- **Negative**: Scalability across independent micro-services requires future extraction if specific components (e.g. video/OCR) become compute bottlenecks.

