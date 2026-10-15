# DocWise

**Your documents. Your questions. Answers you can verify.**

DocWise is an AI-powered document assistant that lets users upload PDFs and notes, ask questions about their contents, and receive streamed answers with clickable citations to supporting passages.

Built with a focus on reliable retrieval, evidence-based responses, privacy, and measurable AI performance.

## Features

- **Document Chat** — Ask natural-language questions about uploaded PDFs and notes.
- **Streaming Answers** — Receive responses progressively as they are generated.
- **Clickable Citations** — Trace answers back to relevant passages in source documents.
- **Hybrid Retrieval** — Combine retrieval methods using Reciprocal Rank Fusion (RRF) to improve search relevance.
- **Evidence-Based Responses** — Refuse unsupported questions when relevant evidence is unavailable.
- **Asynchronous Ingestion** — Process documents through parsing, chunking, embedding, and indexing with progress tracking.
- **Per-User Data Isolation** — Enforce document ownership across access control and retrieval.
- **Prompt-Injection Defence** — Treat document contents as untrusted input rather than instructions.
- **Usage & Cost Tracking** — Monitor token consumption, estimated LLM costs, response latency, and model usage.
- **Quota Enforcement** — Apply daily token limits to control resource consumption.
- **Evaluation Framework** — Assess retrieval quality, ranking performance, answer faithfulness, and refusal behaviour.
- **Offline Testing Mode** — Test core workflows using fake embedding and LLM providers without external AI API costs.

## Engineering Highlights

- Retrieval queries scoped to the authenticated user.
- Server-Sent Events (SSE) for streamed chat responses and source delivery.
- Background document processing through a Redis-backed job queue.
- Batched embedding generation with caching.
- Configurable LLM fallback chains, timeouts, and retries.
- Evidence-aware prompting to reduce unsupported answers.
- Automated tests for isolation, quota enforcement, and refusal behaviour.
- Evaluation workflows for comparing chunking strategies and retrieval configurations.

## Author

**Muzdalfa Zulfiqar**

[GitHub](https://github.com/MuzdalfaZulfiqar) · [Portfolio](https://muzdalfa-s-portfolio-i.vercel.app/)

---

*Answers grounded in your documents, with evidence you can inspect.*
