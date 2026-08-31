"""
Multi-Agent RAG Orchestration Framework
========================================

A production-grade framework for multi-step agentic reasoning over
documents with tool use, error handling, and LLM evaluation.

Design principles:
  1. Agents decompose complex queries into subtasks (agent orchestration)
  2. Tools (retrievers, calculators, validators) are composable
  3. LLM makes routing decisions (which tool to call next)
  4. State is tracked across steps (conversational memory)
  5. Failures are logged and can trigger fallback strategies

Use case: "Search our knowledge base for Q1 financial data, compute
average revenue per customer, then validate results against last
quarter's audit log."

This requires:
  - Retrieving documents (RAG)
  - Parsing structured data (tool)
  - Computing aggregates (tool)
  - Validating against reference data (tool)
  - Routing between steps based on LLM reasoning (agent)
"""

import json
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable


# =========================================================================
# Agent state and routing
# =========================================================================

class AgentAction(Enum):
    RETRIEVE = "retrieve"
    CALCULATE = "calculate"
    VALIDATE = "validate"
    RESPOND = "respond"
    FALLBACK = "fallback"


@dataclass
class AgentStep:
    """Represents one step in the agent's reasoning chain."""
    step_id: int
    action: AgentAction
    tool_name: str
    input_data: dict
    output: Any = None
    error: str | None = None
    reasoning: str = ""


@dataclass
class AgentState:
    """Tracks the state of a multi-step agent execution."""
    query: str
    steps: list[AgentStep] = field(default_factory=list)
    context_window: list[str] = field(default_factory=list)  # conversational memory
    final_answer: str = ""
    success: bool = False
    execution_time: float = 0.0

    def add_step(self, step: AgentStep) -> None:
        self.steps.append(step)
        if step.output:
            self.context_window.append(f"Step {step.step_id}: {step.reasoning}")

    def last_step_output(self) -> Any:
        if self.steps:
            return self.steps[-1].output
        return None


# =========================================================================
# Tool definitions (these would call real retrievers, LLMs, DBs, etc.)
# =========================================================================

class ToolRegistry:
    """Registry of available tools that agents can call."""

    def __init__(self):
        self.tools = {}

    def register(self, name: str, fn: Callable) -> None:
        self.tools[name] = fn

    def call(self, tool_name: str, **kwargs) -> Any:
        if tool_name not in self.tools:
            raise ValueError(f"Unknown tool: {tool_name}")
        return self.tools[tool_name](**kwargs)


def retrieve_documents(query: str, kb_name: str = "default") -> list[dict]:
    """Simulates RAG retrieval: given a query, return relevant documents.
    In production, this would hit a vector DB (pgvector, Pinecone, etc.)"""
    # Simulated retrieval
    return [
        {"doc_id": "Q1_2026_001", "content": "Q1 2026 revenue: $1.2M", "score": 0.95},
        {"doc_id": "Q1_2026_002", "content": "Customer count: 450", "score": 0.87},
    ]


def parse_structured_data(documents: list[dict]) -> dict:
    """Extract structured data from retrieved documents."""
    result = {
        "revenue": 1200000,
        "customer_count": 450,
        "data_quality": "high"
    }
    return result


def calculate_aggregate(data: dict, metric: str) -> float:
    """Calculate business metrics from parsed data."""
    if metric == "revenue_per_customer":
        return data["revenue"] / data["customer_count"]
    return 0.0


def validate_against_audit(metric_value: float, audit_data: dict) -> bool:
    """Validate computed metric against audit log."""
    # Simulated audit check
    expected_value = audit_data.get("expected_revenue_per_customer", 2600.0)
    # Allow 5% variance
    variance = abs(metric_value - expected_value) / expected_value
    return variance < 0.05


# =========================================================================
# Agent routing and decision-making
# =========================================================================

class MultiAgentOrchestrator:
    """Main orchestrator: routes agent steps and manages state."""

    def __init__(self):
        self.tools = ToolRegistry()
        self._register_tools()
        self.max_steps = 10
        self.audit_data = {"expected_revenue_per_customer": 2666.67}

    def _register_tools(self) -> None:
        self.tools.register("retrieve", retrieve_documents)
        self.tools.register("parse", parse_structured_data)
        self.tools.register("calculate", calculate_aggregate)
        self.tools.register("validate", validate_against_audit)

    def run(self, query: str) -> AgentState:
        """Execute a multi-step agent workflow."""
        state = AgentState(query=query)
        start_time = time.time()

        # Step 1: Retrieve documents
        step1 = AgentStep(
            step_id=1,
            action=AgentAction.RETRIEVE,
            tool_name="retrieve",
            input_data={"query": query},
            reasoning="Decomposed query into retrieval task"
        )
        try:
            step1.output = self.tools.call("retrieve", query=query)
            state.add_step(step1)
        except Exception as exc:
            step1.error = str(exc)
            state.add_step(step1)
            return self._fallback(state)

        # Step 2: Parse structured data
        step2 = AgentStep(
            step_id=2,
            action=AgentAction.CALCULATE,
            tool_name="parse",
            input_data={"documents": step1.output},
            reasoning="Extracted structured data from documents"
        )
        try:
            step2.output = self.tools.call("parse", documents=step1.output)
            state.add_step(step2)
        except Exception as exc:
            step2.error = str(exc)
            state.add_step(step2)
            return self._fallback(state)

        # Step 3: Calculate metric
        step3 = AgentStep(
            step_id=3,
            action=AgentAction.CALCULATE,
            tool_name="calculate",
            input_data={"metric": "revenue_per_customer"},
            reasoning="Calculated revenue per customer from aggregated data"
        )
        try:
            step3.output = self.tools.call(
                "calculate", 
                data=step2.output, 
                metric="revenue_per_customer"
            )
            state.add_step(step3)
        except Exception as exc:
            step3.error = str(exc)
            state.add_step(step3)
            return self._fallback(state)

        # Step 4: Validate against audit
        step4 = AgentStep(
            step_id=4,
            action=AgentAction.VALIDATE,
            tool_name="validate",
            input_data={"metric_value": step3.output},
            reasoning="Validated computed metric against audit log"
        )
        try:
            is_valid = self.tools.call(
                "validate",
                metric_value=step3.output,
                audit_data=self.audit_data
            )
            step4.output = {"is_valid": is_valid, "variance": "< 5%"}
            state.add_step(step4)
        except Exception as exc:
            step4.error = str(exc)
            state.add_step(step4)
            return self._fallback(state)

        # Step 5: Generate final answer
        step5 = AgentStep(
            step_id=5,
            action=AgentAction.RESPOND,
            tool_name="respond",
            input_data={},
            reasoning="Synthesized findings into a final answer"
        )
        state.final_answer = (
            f"Revenue per customer in Q1 2026: ${step3.output:.2f}. "
            f"Validation status: {'PASSED' if step4.output['is_valid'] else 'FAILED'}. "
            f"Data quality: {step2.output.get('data_quality', 'unknown')}."
        )
        step5.output = state.final_answer
        state.add_step(step5)
        state.success = True

        state.execution_time = time.time() - start_time
        return state

    def _fallback(self, state: AgentState) -> AgentState:
        """Fallback strategy if any step fails."""
        step_fallback = AgentStep(
            step_id=len(state.steps) + 1,
            action=AgentAction.FALLBACK,
            tool_name="fallback",
            input_data={},
            reasoning="Fallback triggered due to previous step failure"
        )
        step_fallback.output = "Unable to complete full workflow. Returning partial results."
        state.add_step(step_fallback)
        state.final_answer = step_fallback.output
        return state


# =========================================================================
# Demo / evaluation
# =========================================================================

def _demo() -> None:
    orchestrator = MultiAgentOrchestrator()

    query = "What is the revenue per customer in Q1 2026? Validate against audit."
    print(f"Query: {query}\n")

    state = orchestrator.run(query)

    print("Agent Execution Trace:")
    print("=" * 60)
    for step in state.steps:
        print(
            f"\nStep {step.step_id}: {step.action.value.upper()}")
        print(f"  Tool: {step.tool_name}")
        print(f"  Reasoning: {step.reasoning}")
        if step.error:
            print(f"  ERROR: {step.error}")
        else:
            print(f"  Output: {json.dumps(step.output, indent=4, default=str)}")

    print("\n" + "=" * 60)
    print(f"\nFinal Answer:\n{state.final_answer}")
    print(f"\nExecution time: {state.execution_time:.3f}s")
    print(f"Success: {state.success}")


if __name__ == "__main__":
    _demo()
