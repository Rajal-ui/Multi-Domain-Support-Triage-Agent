# Design Decisions

## Retrieval method
Chose TF-IDF over a vector database because the corpus is local, moderate in size, deterministic, and easy to run in a hackathon environment without extra infrastructure.

## LLM backend
Chose a hosted LLM backend for structured JSON generation and concise user-facing responses, while keeping all factual grounding tied to local retrieved context.

## Escalation policy
Used escalation-heavy defaults because the problem statement penalizes unsupported claims more than conservative routing.

## Sample-set verification
Used `sample_support_tickets.csv` as a mini dev set to inspect status mismatches, request type mismatches, and likely hallucination or over-escalation failures.
