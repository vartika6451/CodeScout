from langgraph.graph import END, START, StateGraph

from app.agents.investigation.models import BugInvestigationState
from app.agents.investigation.steps import (
    MAX_INVESTIGATION_STEPS,
    evaluate_hypotheses,
    gather_evidence,
    generate_hypotheses,
    generate_report,
    identify_entry_points,
    trace_code,
    understand_bug,
)


def route_after_evaluation(state: BugInvestigationState) -> str:
    """Decides whether to perform another evidence-gathering cycle or generate the final report."""
    if state.get("is_conclusive", False) or state.get("step_count", 0) >= MAX_INVESTIGATION_STEPS:
        return "generate_report"
    return "gather_evidence"


def build_bug_investigation_graph():
    """Builds and compiles the Phase 3 dedicated Bug Investigation LangGraph state machine."""
    workflow = StateGraph(BugInvestigationState)

    workflow.add_node("understand_bug", understand_bug)
    workflow.add_node("identify_entry_points", identify_entry_points)
    workflow.add_node("gather_evidence", gather_evidence)
    workflow.add_node("trace_code", trace_code)
    workflow.add_node("generate_hypotheses", generate_hypotheses)
    workflow.add_node("evaluate_hypotheses", evaluate_hypotheses)
    workflow.add_node("generate_report", generate_report)

    workflow.add_edge(START, "understand_bug")
    workflow.add_edge("understand_bug", "identify_entry_points")
    workflow.add_edge("identify_entry_points", "gather_evidence")
    workflow.add_edge("gather_evidence", "trace_code")
    workflow.add_edge("trace_code", "generate_hypotheses")
    workflow.add_edge("generate_hypotheses", "evaluate_hypotheses")

    workflow.add_conditional_edges(
        "evaluate_hypotheses",
        route_after_evaluation,
        {
            "gather_evidence": "gather_evidence",
            "generate_report": "generate_report",
        },
    )

    workflow.add_edge("generate_report", END)

    return workflow.compile()


bug_investigation_graph = build_bug_investigation_graph()
