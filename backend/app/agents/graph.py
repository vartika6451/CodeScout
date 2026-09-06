import json
import logging
import os
import re
from typing import Any, Dict, List, Optional, Set

from dotenv import load_dotenv
from google import genai
from langgraph.graph import END, START, StateGraph

from app.agents.state import CodeScoutState
from app.agents.tools import (
    find_callees,
    find_callers,
    find_definition,
    find_references,
    get_class_info,
    get_dependencies,
    get_dependents,
    get_file_structure,
    search_code,
    trace_function,
)

load_dotenv()
logger = logging.getLogger(__name__)

MAX_TOOL_CALLS = 6


def _extract_symbol_candidate(question: str) -> Optional[str]:
    """Extracts a plausible function, method, class, or file identifier from a natural language query."""
    # 1. Matches quoted strings: 'AuthService.login' or "validate_user" or `chat`
    quoted = re.findall(r"['\"`]([\w\.\/\-]+)['\"`]", question)
    if quoted:
        return quoted[0]

    # 2. Matches path-like strings with extensions: app/routes/chat.py
    files = re.findall(r"\b[\w\.\/\-]+\.py\b", question)
    if files:
        return files[0]

    # 3. Known domain mappings in CodeScout
    q_low = question.lower()
    if "codescout graph" in q_low or "main graph" in q_low or "code_scout_graph" in q_low:
        return "code_scout_graph"
    if "chat endpoint" in q_low or "chat api" in q_low:
        return "chat"
    if "analyze endpoint" in q_low or "analyze repository" in q_low:
        return "analyze_repository"

    # 4. Matches snake_case identifiers with underscores: validate_token, should_analyze_file, code_scout_graph
    snake_cases = re.findall(r"\b[a-z]+_[a-z0-9_]+\b", question)
    if snake_cases:
        return snake_cases[0]

    # 5. Matches identifiers following key query phrases:
    key_verb_match = re.search(
        r"(?:who calls|what does|called by|calls|callees of|callers of|definition of|where is|trace(?:\s+function)?|flow(?:\s+from)?|depend on|dependents of|structure of|class info for)\s+([A-Za-z_][\w\.\/\-]*)",
        question,
        re.IGNORECASE,
    )
    if key_verb_match:
        candidate = key_verb_match.group(1).rstrip("?.!,:;")
        if candidate.lower() in ("the", "a", "an", "this", "that", "main"):
            after_article = re.search(
                r"(?:who calls|what does|called by|calls|callees of|callers of|definition of|where is|trace(?:\s+function)?|flow(?:\s+from)?|depend on|dependents of|structure of|class info for)\s+(?:the|a|an|this|that|main)\s+([A-Za-z_][\w\.\/\-]*)",
                question,
                re.IGNORECASE,
            )
            if after_article:
                candidate = after_article.group(1).rstrip("?.!,:;")
        if candidate.lower() not in ("the", "a", "an", "this", "that", "main", "what", "where", "who", "how", "why"):
            return candidate

    # 6. Matches identifiers with parentheses: login() -> login
    func_calls = re.findall(r"\b([A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*)\s*\(", question)
    if func_calls:
        return func_calls[0]

    # 7. Matches dotted or CamelCase identifiers: AuthService.login or UserService
    dotted_or_camel = re.findall(
        r"\b(?:[A-Za-z_]\w*\.[A-Za-z_]\w*|[A-Z][a-zA-Z0-9]+)\b",
        question,
    )
    if dotted_or_camel:
        for c in dotted_or_camel:
            if c.lower() not in (
                "what", "where", "when", "who", "how", "why", "which",
                "explain", "describe", "find", "show", "tell", "trace", "is", "are", "can",
                "codescout", "api", "rag"
            ):
                return c

    return None


def understand_question(state: CodeScoutState) -> CodeScoutState:
    """Analyzes user question, initializes investigation telemetry, and sets defaults."""
    return {
        **state,
        "tool_calls": state.get("tool_calls", []),
        "evidence": state.get("evidence", []),
        "graph_results": state.get("graph_results", []),
        "retrieved_chunks": state.get("retrieved_chunks", []),
        "investigation_step": state.get("investigation_step", 0),
        "is_sufficient": False,
        "next_tool": None,
    }


def choose_tool(state: CodeScoutState) -> CodeScoutState:
    """Decides which investigation tool (semantic search or structural graph) to execute next."""
    step = state.get("investigation_step", 0)
    if step >= MAX_TOOL_CALLS or state.get("is_sufficient", False):
        return {**state, "is_sufficient": True, "next_tool": None}

    question = state["question"]
    tool_calls = state.get("tool_calls", [])
    executed_tools = {tc.get("tool") for tc in tool_calls}
    q_lower = question.lower()
    symbol = _extract_symbol_candidate(question)

    selected_tool: Optional[Dict[str, Any]] = None

    # Structural intention detection
    if any(k in q_lower for k in ("who calls", "callers", "caller")):
        target = symbol or "chat"
        selected_tool = {"tool": "find_callers", "args": {"symbol": target}}

    elif any(k in q_lower for k in ("what does", "callees", "callee")) and "call" in q_lower:
        target = symbol or "chat"
        selected_tool = {"tool": "find_callees", "args": {"symbol": target}}

    elif any(k in q_lower for k in ("trace", "call tree", "flow")):
        target = symbol or "chat"
        selected_tool = {"tool": "trace_function", "args": {"symbol": target, "depth": 2}}

    elif any(k in q_lower for k in ("where is", "where are", "find definition", "definition of", "located")):
        if symbol:
            selected_tool = {"tool": "find_definition", "args": {"symbol": symbol}}
        else:
            selected_tool = {"tool": "search_code", "args": {"query": question}}

    elif any(k in q_lower for k in ("dependents", "depends on", "what depends on", "files depend on", "who depends on")):
        target = symbol or question
        selected_tool = {"tool": "get_dependents", "args": {"file_or_symbol": target}}

    elif any(k in q_lower for k in ("dependencies", "depend on", "imports of")):
        target = symbol or question
        selected_tool = {"tool": "get_dependencies", "args": {"file_or_symbol": target}}

    elif any(k in q_lower for k in ("structure of", "file structure", "outline of")):
        target = symbol or "app/routes/chat.py"
        selected_tool = {"tool": "get_file_structure", "args": {"file_path": target}}

    elif any(k in q_lower for k in ("class info", "subclasses of", "class details")):
        target = symbol or "CodeGraph"
        selected_tool = {"tool": "get_class_info", "args": {"class_name": target}}

    elif any(k in q_lower for k in ("references", "referenced")):
        target = symbol or question
        selected_tool = {"tool": "find_references", "args": {"symbol": target}}

    # Multi-step reasoning fallback
    if not selected_tool or selected_tool["tool"] in executed_tools:
        if "search_code" not in executed_tools:
            selected_tool = {"tool": "search_code", "args": {"query": question}}
        elif symbol and "find_definition" not in executed_tools:
            selected_tool = {"tool": "find_definition", "args": {"symbol": symbol}}
        else:
            return {**state, "is_sufficient": True, "next_tool": None}

    # Guard against repeated identical tool executions
    for prev in tool_calls:
        if prev.get("tool") == selected_tool["tool"] and prev.get("args") == selected_tool["args"]:
            return {**state, "is_sufficient": True, "next_tool": None}

    return {**state, "next_tool": selected_tool}


def route_after_choose(state: CodeScoutState) -> str:
    """Routes to tool execution or directly to generation if enough information is present."""
    if state.get("is_sufficient", False) or not state.get("next_tool"):
        return "generate"
    return "execute_tool"


def execute_tool(state: CodeScoutState) -> CodeScoutState:
    """Executes the chosen tool and accumulates structured facts and textual evidence."""
    next_tool = state.get("next_tool")
    if not next_tool:
        return state

    tool_name = next_tool.get("tool", "")
    args = next_tool.get("args", {})
    step = state.get("investigation_step", 0) + 1

    result: Dict[str, Any] = {"success": False}
    evidence_text = ""

    if tool_name == "search_code":
        result = search_code(query=args.get("query", ""), repository=state.get("repository"))
        if result.get("success"):
            new_chunks = result.get("results", [])
            retrieved = state.get("retrieved_chunks", []) + new_chunks
            evidence_text = f"Semantic search for '{args.get('query')}' found {len(new_chunks)} code chunks."
            return {
                **state,
                "retrieved_chunks": retrieved,
                "tool_calls": state.get("tool_calls", []) + [{"tool": tool_name, "args": args, "result": result}],
                "evidence": state.get("evidence", []) + [evidence_text],
                "investigation_step": step,
                "next_tool": None,
            }

    elif tool_name == "find_definition":
        result = find_definition(symbol=args.get("symbol", ""))
        if result.get("success"):
            d = result["definition"]
            evidence_text = f"Definition of {args.get('symbol')}: {d['type']} in {d['file_path']} at line {d['line_number']}."
        else:
            evidence_text = f"Definition search: {result.get('error')}."

    elif tool_name == "find_callees":
        result = find_callees(symbol=args.get("symbol", ""))
        if result.get("success"):
            callees = [f"{c['name']} ({c['file_path']}:{c['line_number']})" for c in result.get("callees", [])]
            evidence_text = f"{args.get('symbol')} calls: {', '.join(callees) if callees else 'no functions recorded'}."
        else:
            evidence_text = f"Callees search: {result.get('error')}."

    elif tool_name == "find_callers":
        result = find_callers(symbol=args.get("symbol", ""))
        if result.get("success"):
            callers = [f"{c['name']} ({c['file_path']}:{c['line_number']})" for c in result.get("callers", [])]
            evidence_text = f"{args.get('symbol')} is called by: {', '.join(callers) if callers else 'no recorded callers'}."
        else:
            evidence_text = f"Callers search: {result.get('error')}."

    elif tool_name == "find_references":
        result = find_references(symbol=args.get("symbol", ""))
        if result.get("success"):
            refs = result.get("references", {})
            evidence_text = (
                f"References to {args.get('symbol')}: {len(refs.get('call_sites', []))} call sites, "
                f"{len(refs.get('import_sites', []))} import sites, {len(refs.get('subclasses', []))} subclasses."
            )
        else:
            evidence_text = f"References search: {result.get('error')}."

    elif tool_name == "get_file_structure":
        result = get_file_structure(file_path=args.get("file_path", ""))
        if result.get("success"):
            cls_names = [c["name"] for c in result.get("classes", [])]
            fn_names = [f["name"] for f in result.get("functions", [])]
            evidence_text = (
                f"File {result.get('file_path')} structure: classes={cls_names}, functions={fn_names}."
            )
        else:
            evidence_text = f"File structure: {result.get('error')}."

    elif tool_name == "get_class_info":
        result = get_class_info(class_name=args.get("class_name", ""))
        if result.get("success"):
            methods = [m["name"] for m in result.get("methods", [])]
            evidence_text = f"Class {args.get('class_name')} in {result.get('file_path')} has methods: {methods}."
        else:
            evidence_text = f"Class info: {result.get('error')}."

    elif tool_name == "trace_function":
        result = trace_function(symbol=args.get("symbol", ""), depth=args.get("depth", 2))
        if result.get("success"):
            tree = result.get("tree", {})
            evidence_text = f"Traced call tree for {args.get('symbol')} (depth {args.get('depth', 2)}): root at {tree.get('file_path')}:{tree.get('line_number')}."
        else:
            evidence_text = f"Trace function: {result.get('error')}."

    elif tool_name == "get_dependencies":
        result = get_dependencies(file_or_symbol=args.get("file_or_symbol", ""))
        if result.get("success"):
            imported = result.get("imported_files", []) or result.get("callees", [])
            evidence_text = f"Dependencies of {args.get('file_or_symbol')}: {imported}."
        else:
            evidence_text = f"Dependencies: {result.get('error')}."

    elif tool_name == "get_dependents":
        result = get_dependents(file_or_symbol=args.get("file_or_symbol", ""))
        if result.get("success"):
            deps = result.get("dependent_files", []) or result.get("callers", [])
            evidence_text = f"Dependents of {args.get('file_or_symbol')}: {deps}."
        else:
            evidence_text = f"Dependents: {result.get('error')}."

    return {
        **state,
        "tool_calls": state.get("tool_calls", []) + [{"tool": tool_name, "args": args, "result": result}],
        "evidence": state.get("evidence", []) + [evidence_text],
        "graph_results": state.get("graph_results", []) + [result],
        "investigation_step": step,
        "next_tool": None,
    }


def evaluate_evidence(state: CodeScoutState) -> CodeScoutState:
    """Evaluates whether sufficient concrete evidence has been accumulated to answer the question."""
    step = state.get("investigation_step", 0)
    tool_calls = state.get("tool_calls", [])

    if step >= MAX_TOOL_CALLS or state.get("is_sufficient", False):
        return {**state, "is_sufficient": True}

    if tool_calls:
        last_tool = tool_calls[-1].get("tool")
        # Any structural lookup (definition, callers, callees, structure, trace, etc.)
        # provides direct evidence answering the query (or confirms the symbol is absent).
        if last_tool in (
            "find_callers",
            "find_callees",
            "find_definition",
            "get_file_structure",
            "get_class_info",
            "trace_function",
            "get_dependencies",
            "get_dependents",
            "find_references",
        ):
            return {**state, "is_sufficient": True}

        if step >= 2:
            return {**state, "is_sufficient": True}

    return {**state, "is_sufficient": False}


def route_after_evidence(state: CodeScoutState) -> str:
    """Routes between continuing tool investigation or proceeding to final answer generation."""
    if state.get("is_sufficient", False) or state.get("investigation_step", 0) >= MAX_TOOL_CALLS:
        return "generate"
    return "choose_tool"


def generate_node(state: CodeScoutState) -> CodeScoutState:
    """Synthesizes the final answer combining RAG context and structural CodeGraph evidence."""
    question = state["question"]
    retrieved_chunks = state.get("retrieved_chunks", [])
    evidence = state.get("evidence", [])

    context_parts: List[str] = []

    # Section 1: Structural Code Graph Evidence
    if evidence:
        context_parts.append("STRUCTURAL EVIDENCE (From Code Graph):")
        for idx, ev in enumerate(evidence, start=1):
            context_parts.append(f"{idx}. {ev}")

    # Section 2: Semantic Code Chunks
    if retrieved_chunks:
        context_parts.append("\nRELEVANT SOURCE CODE CHUNKS:")
        for res in retrieved_chunks:
            context_parts.append(
                f"FILE: {res.get('file_path')}\n"
                f"CHUNK: {res.get('chunk_index')}\n"
                f"SIMILARITY: {res.get('similarity', 0.0):.2f}\n"
                f"CODE:\n{res.get('content', '')}\n"
            )

    full_context = "\n".join(context_parts).strip()

    # If Gemini API key is configured, synthesize via Gemini LLM
    api_key = os.getenv("GEMINI_API_KEY")
    if api_key:
        try:
            client = genai.Client(api_key=api_key)
            prompt = f"""
You are CodeScout, an advanced AI code analysis assistant.
Answer the user's question using the provided structural graph evidence and code context.

RULES:
1. Cite exact file paths and line numbers when available.
2. If a symbol was reported as 'not found' or 'ambiguous' in the evidence, clearly report that it was not found or is ambiguous. Do not hallucinate definitions or relationships.
3. Be concise and provide architectural clarity.

USER QUESTION:
{question}

EVIDENCE & CONTEXT:
{full_context if full_context else "No relevant context or evidence discovered."}
"""
            model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip()
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
            )
            answer = response.text
        except Exception as exc:
            logger.warning("Gemini generation failed, falling back to evidence synthesis: %s", exc)
            answer = _synthesize_fallback_answer(question, evidence, retrieved_chunks)
    else:
        answer = _synthesize_fallback_answer(question, evidence, retrieved_chunks)

    return {
        **state,
        "context": full_context,
        "answer": answer,
    }


def _synthesize_fallback_answer(
    question: str,
    evidence: List[str],
    retrieved_chunks: List[Dict[str, Any]],
) -> str:
    """Deterministic answer synthesis fallback when running in offline or test environments."""
    if not evidence and not retrieved_chunks:
        return f"I investigated the codebase but could not find information regarding: {question}."

    parts: List[str] = [f"Based on CodeScout's codebase investigation for: '{question}':\n"]

    if evidence:
        parts.append("**Structural Evidence:**")
        for ev in evidence:
            parts.append(f"- {ev}")

    if retrieved_chunks:
        parts.append("\n**Related Source Files:**")
        seen_files = set()
        for chunk in retrieved_chunks:
            fp = chunk.get("file_path")
            if fp and fp not in seen_files:
                seen_files.add(fp)
                parts.append(f"- `{fp}` (chunk {chunk.get('chunk_index', 0)})")

    return "\n".join(parts)


def build_graph():
    """Builds and compiles the Phase 2 LangGraph agent state machine."""
    workflow = StateGraph(CodeScoutState)

    workflow.add_node("understand_question", understand_question)
    workflow.add_node("choose_tool", choose_tool)
    workflow.add_node("execute_tool", execute_tool)
    workflow.add_node("evaluate_evidence", evaluate_evidence)
    workflow.add_node("generate", generate_node)

    workflow.add_edge(START, "understand_question")
    workflow.add_edge("understand_question", "choose_tool")

    workflow.add_conditional_edges(
        "choose_tool",
        route_after_choose,
        {
            "execute_tool": "execute_tool",
            "generate": "generate",
        },
    )

    workflow.add_edge("execute_tool", "evaluate_evidence")

    workflow.add_conditional_edges(
        "evaluate_evidence",
        route_after_evidence,
        {
            "choose_tool": "choose_tool",
            "generate": "generate",
        },
    )

    workflow.add_edge("generate", END)

    return workflow.compile()


code_scout_graph = build_graph()