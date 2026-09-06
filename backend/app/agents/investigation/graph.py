from langgraph.graph import END, START, StateGraph

from app.agents.investigation.models import BugInvestigationState
from app.agents.investigation.steps import (
    MAX_INVESTIGATION_STEPS,
    MAX_PATCH_ITERATIONS,
    MAX_TEST_RUNS,
    analyze_runtime_failures,
    evaluate_hypotheses,
    execute_test_verification,
    gather_evidence,
    generate_hypotheses,
    generate_patch_step,
    generate_report,
    identify_entry_points,
    revise_patch_step,
    trace_code,
    understand_bug,
    verify_patch_step,
)


def route_after_evaluation(state: BugInvestigationState) -> str:
    """
    Decides whether to perform further test verification, proceed to patch generation,
    or generate the final report directly if no failures were detected.
    """
    if not state.get("failures"):
        return "generate_report"

    if (
        state.get("is_conclusive", False)
        or state.get("step_count", 0) >= MAX_INVESTIGATION_STEPS
        or state.get("test_count", 0) >= MAX_TEST_RUNS
    ):
        return "generate_patch"

    test_runs = state.get("test_runs", [])
    if len(test_runs) < MAX_TEST_RUNS:
        return "execute_test_verification"

    return "generate_patch"


def route_after_patch_verification(state: BugInvestigationState) -> str:
    """
    Decides whether to revise the patch on failure or conclude with the final report.
    """
    status = state.get("final_status", "INCONCLUSIVE")
    iteration = state.get("patch_iteration", 1)
    max_iterations = state.get("max_patch_iterations", MAX_PATCH_ITERATIONS)

    # If no patch proposed, or fix is verified, proceed to final report
    if not state.get("proposed_patch") or status in ("FIX_VERIFIED", "PRE_EXISTING_FAILURES"):
        return "generate_report"

    # If verification failed and iterations remain, revise and try again
    if iteration < max_iterations:
        return "revise_patch"

    return "generate_report"


def build_bug_investigation_graph():
    """
    Builds and compiles the complete Phase 4 Bug Investigation, Patch Generation,
    and Safe Workspace Verification LangGraph state machine.
    """
    workflow = StateGraph(BugInvestigationState)

    # Investigation & Runtime Execution nodes
    workflow.add_node("understand_bug", understand_bug)
    workflow.add_node("identify_entry_points", identify_entry_points)
    workflow.add_node("gather_evidence", gather_evidence)
    workflow.add_node("trace_code", trace_code)
    workflow.add_node("generate_hypotheses", generate_hypotheses)
    workflow.add_node("execute_test_verification", execute_test_verification)
    workflow.add_node("analyze_runtime_failures", analyze_runtime_failures)
    workflow.add_node("evaluate_hypotheses", evaluate_hypotheses)

    # Phase 4: Patching & Verification nodes
    workflow.add_node("generate_patch", generate_patch_step)
    workflow.add_node("verify_patch", verify_patch_step)
    workflow.add_node("revise_patch", revise_patch_step)
    workflow.add_node("generate_report", generate_report)

    # Step 1: Investigation -> Hypotheses -> Test Verification
    workflow.add_edge(START, "understand_bug")
    workflow.add_edge("understand_bug", "identify_entry_points")
    workflow.add_edge("identify_entry_points", "gather_evidence")
    workflow.add_edge("gather_evidence", "trace_code")
    workflow.add_edge("trace_code", "generate_hypotheses")
    workflow.add_edge("generate_hypotheses", "execute_test_verification")
    workflow.add_edge("execute_test_verification", "analyze_runtime_failures")
    workflow.add_edge("analyze_runtime_failures", "evaluate_hypotheses")

    # Step 2: Evaluation loop -> Patch Generation / Report
    workflow.add_conditional_edges(
        "evaluate_hypotheses",
        route_after_evaluation,
        {
            "execute_test_verification": "execute_test_verification",
            "generate_patch": "generate_patch",
            "generate_report": "generate_report",
        },
    )

    # Step 3: Patch Generation -> Isolated Verification -> Bounded Revision Loop
    workflow.add_edge("generate_patch", "verify_patch")
    workflow.add_conditional_edges(
        "verify_patch",
        route_after_patch_verification,
        {
            "revise_patch": "revise_patch",
            "generate_report": "generate_report",
        },
    )
    workflow.add_edge("revise_patch", "generate_patch")

    # Step 4: Final Report -> END
    workflow.add_edge("generate_report", END)

    return workflow.compile()


bug_investigation_graph = build_bug_investigation_graph()
