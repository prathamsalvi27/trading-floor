# Trading Floor

A personal stock portfolio simulator built to learn agentic AI patterns: a single LLM orchestrated by LangGraph, calling only deterministic tools exposed over MCP. Built as a learning project, not a real trading system — all money and trades are fake.

## Core pattern

**The LLM calls tools. Tools never call the LLM.**

- A single Groq LLM instance is orchestrated by LangGraph across 3 nodes: `researcher` → `trader` → `risk_manager`.
- Each node does real tool-calling — the LLM decides which tools to call, not hardcoded logic — against its own MCP server, then produces structured (Pydantic) output.
- All reasoning (sentiment, trade decisions, risk approval) happens in the LLM only. The 3 MCP servers expose *only* deterministic tools (same input → same output, zero interpretation) — price lookups, position-size math, wallet/risk checks. No LLM runs inside any MCP server.
- A human confirms every trade (via LangGraph's `interrupt`) before it executes. Execution itself (`execute_buy` / `execute_sell`) is a deterministic action, not a decision — no LLM involved.

## Stack

- **LLM**: Groq (`openai/gpt-oss-120b`, free tier)
- **Orchestration**: LangGraph (3-node graph, human-in-the-loop interrupt, in-memory checkpointing)
- **Tool protocol**: MCP (`mcp` SDK 2.0.0), stdio transport, hand-written client (no `langchain-mcp-adapters` — incompatible with MCP 2.0.0)
- **Market data**: Alpha Vantage (price), NewsAPI (headlines)
- **Database**: SQLite
- **UI**: Gradio

## Project structure

