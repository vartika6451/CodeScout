from langgraph.graph import StateGraph, START, END

from app.agents.state import CodeScoutState
from app.agents.retrieve import retrieve_node
from app.agents.generate import generate_node


def build_graph():
    # Create a graph using our shared state
    graph = StateGraph(CodeScoutState)

    # Add our nodes
    graph.add_node("retrieve", retrieve_node)
    graph.add_node("generate", generate_node)

    # Define the workflow
    graph.add_edge(START, "retrieve")
    graph.add_edge("retrieve", "generate")
    graph.add_edge("generate", END)

    # Compile the graph
    return graph.compile()


code_scout_graph = build_graph()