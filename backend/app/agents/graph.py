from langgraph.graph import StateGraph, START, END

from app.agents.state import CodeScoutState
from app.agents.retrieve import retrieve_node
from app.agents.generate import generate_node
from app.agents.evaluate import evaluate_retrieval
from app.agents.refine import refine_query


def route_after_evaluation(state: CodeScoutState):

    if state.get("needs_refinement", False):

        if state.get("attempt_count", 0) >= 3:
            return "generate"

        return "refine"

    return "generate"


def build_graph():

    graph = StateGraph(CodeScoutState)

    graph.add_node("retrieve", retrieve_node)
    graph.add_node("evaluate", evaluate_retrieval)
    graph.add_node("refine", refine_query)
    graph.add_node("generate", generate_node)

    graph.add_edge(START, "retrieve")

    graph.add_edge("retrieve", "evaluate")

    graph.add_conditional_edges(
        "evaluate",
        route_after_evaluation,
        {
            "refine": "refine",
            "generate": "generate",
        },
    )

    graph.add_edge("refine", "retrieve")

    graph.add_edge("generate", END)

    return graph.compile()


code_scout_graph = build_graph()