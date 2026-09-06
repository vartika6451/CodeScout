from langgraph.graph import END, START, StateGraph

from app.agents.investigation.models import BugInvestigationState
from app.agents.investigation.steps import (
    MAX_INVESTIGATION_STEPS,
    MAX_TEST_RUNS,
    analyze_runtime_failures,
    evaluate_hypotheses,
    execute_test_verification,
    gather_evidence,
    generate_hypotheses,
    generate_report,
    identify_entry_points,
    trace_code,
    understand_bug,
)


def route_after_evaluation(state: BugInvestigationState) -> str:
    """
    Decides whether to perform further test verification, gather more evidence,
    or generate the final report.
    """
    if (
        state.get("is_conclusive", False)
        or state.get("step_count", 0) >= MAX_INVESTIGATION_STEPS
        or state.get("test_count", 0) >= MAX_TEST_RUNS
    ):
        return "generate_report"

    test_runs = state.get("test_runs", [])
    if len(test_runs) < MAX_TEST_RUNS:
        return "execute_test_verification"

    return "generate_report"


def build_bug_investigation_graph():
    """
    Builds and compiles the Phase 3 Part 2 Bug Investigation & Runtime Verification
    LangGraph state machine.
    """
    workflow = StateGraph(BugInvestigationState)

    workflow.add_node("understand_bug", understand_bug)
    workflow.add_node("identify_entry_points", identify_entry_points)
    workflow.add_node("gather_evidence", gather_evidence)
    workflow.add_node("trace_code", trace_code)
    workflow.add_node("generate_hypotheses", generate_hypotheses)
    workflow.add_node("execute_test_verification", execute_test_verification)
    workflow.add_node("analyze_runtime_failures", analyze_runtime_failures)
    workflow.add_node("evaluate_hypotheses", evaluate_hypotheses)
    workflow.add_node("generate_report", generate_report)

    # Core sequential flow: Static Understanding -> Hypotheses -> Runtime Execution -> Analysis
    workflow.add_edge(START, "understand_bug")
    workflow.add_edge("understand_bug", "identify_entry_points")
    workflow.add_edge("identify_entry_points", "gather_evidence")
    workflow.add_edge("gather_evidence", "trace_code")
    workflow.add_edge("trace_code", "generate_hypotheses")
    workflow.add_edge("generate_hypotheses", "execute_test_verification")
    workflow.add_edge("execute_test_verification", "analyze_runtime_failures")
    workflow.add_edge("analyze_runtime_failures", "evaluate_hypotheses")

    # Bounded evaluation loop: more test verification vs final report
    workflow.add_conditional_edges(
        "evaluate_hypotheses",
        route_after_evaluation,
        {
            "execute_test_verification": "execute_test_verification",
            "generate_report": "generate_report",
        },
    )

    workflow.add_edge("generate_report", END)

    return workflow.compile()


bug_investigation_graph = build_bug_investigation_graph()
