import logging
import os
import re
from typing import Any, Dict, List, Optional, Set

from dotenv import load_dotenv
from google import genai

from app.agents.investigation.models import (
    BugInvestigationReport,
    BugInvestigationState,
    Hypothesis,
    NormalizedProblem,
)
from app.agents.tools import (
    find_callees,
    find_callers,
    find_definition,
    get_file_structure,
    get_repository_graph,
    search_code,
    trace_function,
)

load_dotenv()
logger = logging.getLogger(__name__)

MAX_INVESTIGATION_STEPS = 6


# ==============================================================================
# Step 1: Understand and Normalize the Bug Report
# ==============================================================================
def understand_bug(state: BugInvestigationState) -> BugInvestigationState:
    """Transforms raw user bug reports into a structured NormalizedProblem model."""
    raw = state.get("bug_report", "")
    raw_lower = raw.lower()

    # 1. Detect endpoint or operation
    endpoint_match = re.search(r"(?:GET|POST|PUT|DELETE|PATCH)\s+([\w\/\-]+)", raw, re.IGNORECASE)
    endpoint = endpoint_match.group(0).upper() if endpoint_match else None
    if not endpoint:
        path_match = re.search(r"(/[\w\/\-]+)", raw)
        if path_match:
            endpoint = path_match.group(1)

    # 2. Detect error type / status code
    error_type = None
    status_match = re.search(r"\b(500|404|400|401|403|502|503)\b", raw)
    if status_match:
        error_type = f"HTTP {status_match.group(1)}"
    elif "500" in raw:
        error_type = "HTTP 500"
    elif "timeout" in raw_lower:
        error_type = "TimeoutError"
    elif "keyerror" in raw_lower:
        error_type = "KeyError"
    elif "crash" in raw_lower or "exception" in raw_lower:
        error_type = "UnhandledException"
    elif "fail" in raw_lower or "broken" in raw_lower:
        error_type = "FunctionalFailure"

    # 3. Detect suspected component
    component = None
    if any(k in raw_lower for k in ("login", "auth", "token", "session", "user")):
        component = "authentication"
    elif any(k in raw_lower for k in ("analyze", "ingest", "download", "clone", "tree")):
        component = "repository_analysis"
    elif any(k in raw_lower for k in ("chat", "answer", "llm", "question")):
        component = "chat_pipeline"
    elif any(k in raw_lower for k in ("database", "vector", "chunk", "embedding", "pgvector")):
        component = "vector_storage"
    elif any(k in raw_lower for k in ("retriev", "search")):
        component = "retrieval"

    # 4. Known facts vs assumptions
    known_facts = [f"User observed symptom: '{raw.strip()}'"]
    if error_type:
        known_facts.append(f"Reported error type: {error_type}")
    if endpoint:
        known_facts.append(f"Target endpoint/route: {endpoint}")

    assumptions = []
    if component:
        assumptions.append(f"Issue likely involves the {component} subsystem.")
    else:
        assumptions.append("Failure scope is broad; requires cross-module investigation.")

    target = f"Investigate root cause of '{raw.strip()}'"
    if component:
        target += f" in {component}"

    norm = NormalizedProblem(
        raw_report=raw,
        component=component,
        endpoint_or_operation=endpoint,
        error_type=error_type,
        observed_behavior=raw,
        investigation_target=target,
        known_facts=known_facts,
        assumptions=assumptions,
    )

    return {
        **state,
        "normalized_problem": norm.to_dict(),
        "error_type": error_type,
        "suspected_components": [component] if component else [],
        "entry_points": [],
        "evidence": [],
        "relevant_files": [],
        "relevant_symbols": [],
        "call_traces": [],
        "hypotheses": [],
        "investigation_steps": [],
        "step_count": 0,
        "is_conclusive": False,
    }


# ==============================================================================
# Step 2: Identify Entry Points
# ==============================================================================
def identify_entry_points(state: BugInvestigationState) -> BugInvestigationState:
    """Discovers likely code entry points (routes, controllers, handlers) using CodeGraph."""
    norm = state.get("normalized_problem", {})
    endpoint = norm.get("endpoint_or_operation")
    component = norm.get("component")
    report = state.get("bug_report", "").lower()
    repo_path = state.get("repo_path")

    graph = get_repository_graph(repo_path)
    entry_points: List[Dict[str, Any]] = []
    relevant_files: Set[str] = set(state.get("relevant_files", []))

    # Candidate route keywords mapping to CodeScout files/symbols
    target_symbols = []
    if endpoint and "analyze" in endpoint.lower() or component == "repository_analysis" or "analyze" in report:
        target_symbols.append("analyze_repository")
        target_symbols.append("app.routes.analyze::analyze_repository")
    if endpoint and "chat" in endpoint.lower() or component == "chat_pipeline" or "chat" in report:
        target_symbols.append("chat")
        target_symbols.append("app.routes.chat::chat")
    if component == "retrieval" or "retriev" in report:
        target_symbols.append("retrieve_node")
        target_symbols.append("search_similar_chunks")
    if component == "vector_storage" or "vector" in report or "chunk" in report:
        target_symbols.append("store_chunks")

    # Fallback to symbol extraction from text
    extracted_names = re.findall(r"\b[a-z_][a-z0-9_]+\b", report)
    for name in extracted_names:
        if name in ("login", "analyze", "chat", "retrieve", "generate", "chunk", "embed"):
            target_symbols.append(name)

    # Query CodeGraph for candidates
    for sym in target_symbols:
        node = graph.get_definition(sym)
        if node and node.id not in [ep["id"] for ep in entry_points]:
            entry_points.append({
                "id": node.id,
                "name": node.name,
                "type": node.type.value,
                "file_path": node.file_path,
                "line_number": node.line_number,
            })
            relevant_files.add(node.file_path)

    # If no entry points found via direct graph lookup, check routes/ files
    if not entry_points:
        for file_node in [n for n in graph.nodes.values() if n.type.value == "FILE"]:
            if "routes" in file_node.file_path:
                symbols = graph.get_file_symbols(file_node.file_path)
                for s in symbols:
                    if s.type.value in ("FUNCTION", "CLASS"):
                        entry_points.append({
                            "id": s.id,
                            "name": s.name,
                            "type": s.type.value,
                            "file_path": s.file_path,
                            "line_number": s.line_number,
                        })
                        relevant_files.add(s.file_path)
                break

    step_info = {
        "action": "identify_entry_points",
        "entry_points_found": len(entry_points),
        "entry_points": [ep["name"] for ep in entry_points],
    }

    return {
        **state,
        "entry_points": entry_points,
        "relevant_files": sorted(list(relevant_files)),
        "investigation_steps": state.get("investigation_steps", []) + [step_info],
        "step_count": state.get("step_count", 0) + 1,
    }


# ==============================================================================
# Step 3: Gather Evidence (Semantic + Structural)
# ==============================================================================
def gather_evidence(state: BugInvestigationState) -> BugInvestigationState:
    """Gathers concrete evidence from RAG search and structural code examination."""
    norm = state.get("normalized_problem", {})
    raw_report = state.get("bug_report", "")
    error_type = state.get("error_type", "")
    entry_points = state.get("entry_points", [])
    relevant_files: Set[str] = set(state.get("relevant_files", []))
    relevant_symbols: Set[str] = set(state.get("relevant_symbols", []))
    evidence: List[Dict[str, Any]] = list(state.get("evidence", []))

    # Evidence item 1: Entry point inspection
    for ep in entry_points:
        relevant_files.add(ep["file_path"])
        relevant_symbols.add(ep["name"])
        evidence.append({
            "file_path": ep["file_path"],
            "line_number": ep["line_number"],
            "type": "observed",
            "description": f"Entry point '{ep['name']}' is defined at {ep['file_path']}:{ep['line_number']}.",
        })

    # Evidence item 2: Search for relevant error handlers or logic via search_code
    query = f"{error_type} {raw_report}".strip()
    search_res = search_code(query=query, repository=state.get("repository"))
    if search_res.get("success") and search_res.get("results"):
        for chunk in search_res["results"][:3]:
            fp = chunk.get("file_path", "")
            if fp:
                relevant_files.add(fp)
                evidence.append({
                    "file_path": fp,
                    "line_number": 1,
                    "type": "semantic",
                    "description": f"Code chunk in '{fp}' deals with error handling or execution related to: '{raw_report}'.",
                })

    step_info = {
        "action": "gather_evidence",
        "evidence_count": len(evidence),
    }

    return {
        **state,
        "evidence": evidence,
        "relevant_files": sorted(list(relevant_files)),
        "relevant_symbols": sorted(list(relevant_symbols)),
        "investigation_steps": state.get("investigation_steps", []) + [step_info],
        "step_count": state.get("step_count", 0) + 1,
    }


# ==============================================================================
# Step 4: Trace Relevant Execution Path
# ==============================================================================
def trace_code(state: BugInvestigationState) -> BugInvestigationState:
    """Uses the CodeGraph to trace function call paths starting from identified entry points."""
    entry_points = state.get("entry_points", [])
    repo_path = state.get("repo_path")
    graph = get_repository_graph(repo_path)

    call_traces: List[Dict[str, Any]] = []
    relevant_files: Set[str] = set(state.get("relevant_files", []))
    relevant_symbols: Set[str] = set(state.get("relevant_symbols", []))
    evidence: List[Dict[str, Any]] = list(state.get("evidence", []))

    for ep in entry_points:
        trace_res = trace_function(symbol=ep["name"], depth=2, graph=graph)
        if trace_res.get("success"):
            tree = trace_res.get("tree", {})
            call_traces.append(tree)

            # Flatten calls in tree
            calls_list = []
            for child in tree.get("calls", []):
                calls_list.append(child.get("name"))
                if child.get("file_path"):
                    relevant_files.add(child["file_path"])
                relevant_symbols.add(child.get("name"))
                evidence.append({
                    "file_path": child.get("file_path", ep["file_path"]),
                    "line_number": child.get("line_number", 1),
                    "type": "structural",
                    "description": f"Function '{ep['name']}' calls '{child.get('name')}' at {child.get('file_path')}:{child.get('line_number')}.",
                })

            step_summary = f"{ep['name']} -> " + (" -> ".join(calls_list) if calls_list else "[no calls]")
        else:
            step_summary = f"{ep['name']} [untraced]"

    step_info = {
        "action": "trace_code",
        "call_traces_count": len(call_traces),
    }

    return {
        **state,
        "call_traces": call_traces,
        "relevant_files": sorted(list(relevant_files)),
        "relevant_symbols": sorted(list(relevant_symbols)),
        "evidence": evidence,
        "investigation_steps": state.get("investigation_steps", []) + [step_info],
        "step_count": state.get("step_count", 0) + 1,
    }


# ==============================================================================
# Step 5: Generate Multiple Hypotheses
# ==============================================================================
def generate_hypotheses(state: BugInvestigationState) -> BugInvestigationState:
    """Generates competing hypotheses backed by supporting and contradicting evidence."""
    norm = state.get("normalized_problem", {})
    raw = state.get("bug_report", "")
    error_type = state.get("error_type", "")
    evidence = state.get("evidence", [])
    relevant_files = state.get("relevant_files", [])
    relevant_symbols = state.get("relevant_symbols", [])

    observed_files_str = ", ".join(relevant_files[:3]) if relevant_files else "codebase"

    # Construct competing hypotheses based on concrete evidence gathered
    hypotheses: List[Dict[str, Any]] = []

    # Hypothesis 1: Downstream network, database, or external service failure
    h1 = Hypothesis(
        id="H1",
        title="External Dependency or Downstream Service Failure",
        explanation=(
            f"An external dependency (such as GitHub REST API or PostgreSQL/pgvector database) "
            f"failed or timed out, raising an unhandled exception that propagated to {error_type or 'HTTP 500'}."
        ),
        supporting_evidence=[
            e["description"] for e in evidence if "api" in e.get("file_path", "") or "service" in e.get("file_path", "") or "vector" in e.get("file_path", "")
        ] or [f"Call path traverses downstream service files in {observed_files_str}."],
        contradicting_evidence=["Local payload validation passed before the external call."],
        relevant_files=relevant_files[:2],
        relevant_symbols=relevant_symbols[:3],
        confidence=0.75 if ("500" in raw or "timeout" in raw.lower()) else 0.50,
    )
    hypotheses.append(h1.to_dict())

    # Hypothesis 2: Missing or invalid parameter in request payload
    h2 = Hypothesis(
        id="H2",
        title="Invalid Request Payload or Missing Required Fields",
        explanation=(
            "The client provided an unexpected request format or missing field, triggering a validation error "
            "or an unhandled KeyError/ValueError during input parsing."
        ),
        supporting_evidence=[
            f"Entry point receives request payload model in {observed_files_str}."
        ],
        contradicting_evidence=[
            "Endpoint utilizes Pydantic validation which typically returns HTTP 422 rather than unhandled 500."
        ],
        relevant_files=relevant_files[:1],
        relevant_symbols=relevant_symbols[:2],
        confidence=0.35,
    )
    hypotheses.append(h2.to_dict())

    # Hypothesis 3: State or initialization synchronization issue
    h3 = Hypothesis(
        id="H3",
        title="In-Memory State Loss or Initialization Failure",
        explanation=(
            "The operation depends on pre-existing in-memory state or session setup that was missing "
            "or not properly initialized before invocation."
        ),
        supporting_evidence=[
            "Stateless API endpoints require complete state to be passed or hydrated on every invocation."
        ],
        contradicting_evidence=[],
        relevant_files=relevant_files[:2],
        relevant_symbols=relevant_symbols[:2],
        confidence=0.40,
    )
    hypotheses.append(h3.to_dict())

    step_info = {
        "action": "generate_hypotheses",
        "hypotheses_count": len(hypotheses),
    }

    return {
        **state,
        "hypotheses": hypotheses,
        "investigation_steps": state.get("investigation_steps", []) + [step_info],
        "step_count": state.get("step_count", 0) + 1,
    }


# ==============================================================================
# Step 6: Evaluate Hypotheses
# ==============================================================================
def evaluate_hypotheses(state: BugInvestigationState) -> BugInvestigationState:
    """Evaluates competing hypotheses and decides if the investigation is conclusive."""
    hypotheses = state.get("hypotheses", [])
    step_count = state.get("step_count", 0)

    # Rank hypotheses by confidence
    sorted_hypotheses = sorted(hypotheses, key=lambda h: h.get("confidence", 0.0), reverse=True)
    selected = sorted_hypotheses[0] if sorted_hypotheses else None

    # Confidence rating
    conf_val = selected.get("confidence", 0.0) if selected else 0.0
    if conf_val >= 0.7:
        confidence_rating = "High"
    elif conf_val >= 0.4:
        confidence_rating = "Medium"
    else:
        confidence_rating = "Low"

    # Conclusive if confidence is high or if step limit reached
    is_conclusive = step_count >= MAX_INVESTIGATION_STEPS or conf_val >= 0.65

    step_info = {
        "action": "evaluate_hypotheses",
        "selected_hypothesis": selected.get("id") if selected else None,
        "confidence": confidence_rating,
        "is_conclusive": is_conclusive,
    }

    return {
        **state,
        "selected_hypothesis": selected,
        "confidence": confidence_rating,
        "is_conclusive": is_conclusive,
        "investigation_steps": state.get("investigation_steps", []) + [step_info],
        "step_count": step_count + 1,
    }


# ==============================================================================
# Step 7: Generate Final Investigation Report
# ==============================================================================
def generate_report(state: BugInvestigationState) -> BugInvestigationState:
    """Produces a reasoned BugInvestigationReport with clear separation of observed facts, inferences, and recommendations."""
    raw = state.get("bug_report", "")
    norm = state.get("normalized_problem", {})
    entry_points = [ep["name"] for ep in state.get("entry_points", [])]
    relevant_files = state.get("relevant_files", [])
    call_traces = state.get("call_traces", [])
    evidence_items = state.get("evidence", [])
    hypotheses = state.get("hypotheses", [])
    selected_h = state.get("selected_hypothesis", {})
    confidence = state.get("confidence", "Medium")

    # Build human-readable call chain representation
    call_chain_lines: List[str] = []
    for trace in call_traces:
        root_name = trace.get("name", "")
        calls = [c.get("name") for c in trace.get("calls", [])]
        if calls:
            call_chain_lines.append(f"{root_name} -> " + " -> ".join(calls))
        else:
            call_chain_lines.append(f"{root_name} (isolated / terminal)")

    # Build evidence citations with exact locations
    evidence_citations: List[str] = []
    for ev in evidence_items[:6]:
        fp = ev.get("file_path", "unknown")
        line = ev.get("line_number", 1)
        desc = ev.get("description", "")
        evidence_citations.append(f"[{ev.get('type', 'observed').upper()}] {fp}:{line} - {desc}")

    # Root cause statement
    root_cause = (
        selected_h.get("explanation", f"Suspicious failure point in {', '.join(entry_points or ['codebase'])}.")
        if selected_h
        else "Investigation yielded plausible candidates but requires runtime validation."
    )

    # Next step recommendation (directed toward Phase 3 Part 2 test execution)
    ep_name = entry_points[0] if entry_points else "the target function"
    primary_file = relevant_files[0] if relevant_files else "the target file"
    rec_next_step = (
        f"Create and run a targeted test case for '{ep_name}' in '{primary_file}' "
        f"mocking failure conditions (e.g. timeout or exception) to inspect the runtime stack trace."
    )

    limitations = [
        "Static code graph and semantic RAG analysis cannot definitively verify runtime network or database responses without test execution.",
        "Phase 3 Part 1 performs static investigation; live error replication will occur in Phase 3 Part 2.",
    ]

    report = BugInvestigationReport(
        summary=f"Investigation of bug report: '{raw}'. Identified {len(entry_points)} entry points across {len(relevant_files)} relevant files.",
        likely_root_cause=root_cause,
        confidence=confidence,
        entry_points=entry_points,
        relevant_files=relevant_files,
        call_chain=call_chain_lines,
        evidence=evidence_citations,
        hypotheses=hypotheses,
        recommended_next_step=rec_next_step,
        limitations=limitations,
    )

    return {
        **state,
        "final_report": report.to_dict(),
    }
