# Multi-Agent RAG Orchestration Framework

A production-grade framework demonstrating multi-step agentic reasoning over documents, combining RAG (Retrieval-Augmented Generation), tool use, and LLM-driven routing.

## What it demonstrates

A real-world workflow: *"Analyze Q1 financial data from our knowledge base, compute revenue per customer, and validate against the audit log."*

This requires:
1. **Retrieval** — search documents for Q1 data (RAG)
2. **Parsing** — extract structured metrics from unstructured documents
3. **Calculation** — aggregate metrics (revenue per customer)
4. **Validation** — check results against audit log
5. **Response** — synthesize findings into an answer

## Architecture

```
User Query
    ↓
Agent Step 1: Retrieve docs from KB (RAG)
    ↓
Agent Step 2: Parse structured data
    ↓
Agent Step 3: Calculate business metrics
    ↓
Agent Step 4: Validate against audit
    ↓
Agent Step 5: Synthesize into final answer
    ↓
Return to user with full execution trace
```

## Key features

- **State tracking** — `AgentState` maintains conversational memory and execution context
- **Tool registry** — pluggable tools (retrieve, parse, calculate, validate)
- **Error handling** — step failures trigger fallback strategies
- **Full tracing** — every step is logged with reasoning, input, output, and latency
- **LLM-driven routing** — in production, an LLM decides which tool to call next

## Design insights

### Multi-agent reasoning vs. simple RAG

Simple RAG: query → retrieve → return
**Multi-agent: query → decompose into steps → route between tools → synthesize answer**

This matters because business questions often require multiple steps:
- "How are we trending?" requires retrieving data, computing deltas, validating against expectations
- A single retrieval + LLM call often fails on multi-step reasoning

### Tool composability

Each tool is independent: retrieve, parse, calculate, validate. In production:
- Retrieve uses pgvector or Pinecone (vector DB)
- Parse could use an LLM or regex (depends on document structure)
- Calculate uses SQL or pandas
- Validate queries audit logs or reference datasets

Orchestrator doesn't care — it just calls tools and routes based on outputs.

### Error handling patterns

If Step 3 (calculate) fails, fallback is triggered. In production:
- Retry with exponential backoff
- Fall back to a simpler tool (e.g., use aggregated cache instead of live calc)
- Escalate to human review
- Log to monitoring (this is evaluable in LangFuse / Langsmith)

## Usage

```bash
python3 multi_agent_rag.py
```

This runs a demo query and prints the full execution trace:
- Each step's reasoning
- Tool calls and outputs
- Validation results
- Final synthesized answer

## Interview talking points

- "I decompose complex queries into steps, each with a dedicated tool"
- "State is tracked across steps — this enables complex multi-turn workflows"
- "Tool failures don't crash the system — fallbacks ensure robustness"
- "Each step is evaluated (in production, via Langfuse) to catch LLM drift or tool performance degradation"
- "This pattern scales: same framework works for customer support, data analysis, compliance checks, etc."

## Production deployment

In production (e.g., with Mastra or LangGraph):
- Replace simulated tools with real integrations (vector DB, SQL engine, etc.)
- Add an LLM layer for dynamic routing (which tool to call based on current state)
- Integrate evaluation harness (Langfuse) to track step success rates and latency
- Add rate limiting, retry policies, and circuit breakers
- Log all execution traces for debugging and improvement

This code shows the **core orchestration pattern** that underlies production agentic systems.
