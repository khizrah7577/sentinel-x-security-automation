"""LangGraph workflow: Monitoring → Investigation → Decision → Response → Explanation."""

from __future__ import annotations

from langgraph.graph import END, StateGraph

from app.agents.nodes import (
    decision_agent,
    explanation_agent,
    investigation_agent,
    monitoring_agent,
    response_agent,
)
from app.agents.state import AgentState


def build_investigation_graph():
    graph = StateGraph(AgentState)
    graph.add_node("monitoring", monitoring_agent)
    graph.add_node("investigation", investigation_agent)
    graph.add_node("decision", decision_agent)
    graph.add_node("response", response_agent)
    graph.add_node("explanation", explanation_agent)

    graph.set_entry_point("monitoring")
    graph.add_edge("monitoring", "investigation")
    graph.add_edge("investigation", "decision")
    graph.add_edge("decision", "response")
    graph.add_edge("response", "explanation")
    graph.add_edge("explanation", END)
    return graph.compile()


_GRAPH = None


def get_graph():
    global _GRAPH
    if _GRAPH is None:
        _GRAPH = build_investigation_graph()
    return _GRAPH


def run_investigation_workflow(initial: AgentState) -> AgentState:
    """Run once with recursion limit guard against loops."""
    graph = get_graph()
    result = graph.invoke(initial, config={"recursion_limit": 10})
    return result  # type: ignore[return-value]
