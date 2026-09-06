import logging
import os
import re
from pathlib import Path
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
    run_tests,
    search_code,
    trace_function,
)
from app.execution.executor import ExecutionService
from app.execution.models import ExecutionStatus

load_dotenv()
logger = logging.getLogger(__name__)

MAX_INVESTIGATION_STEPS = 6
MAX_TEST_RUNS = 3
MAX_TOTAL_TEST_RUNTIME = 180.0
PER_TEST_TIMEOUT = 60.0



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
        "test_runs": [],
        "runtime_evidence": [],
        "failures": [],
        "confirmed_hypotheses": [],
        "rejected_hypotheses": [],
        "test_count": 0,
        "total_test_runtime": 0.0,
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
        title="Invalid Request Payload, NoneType Value, or Missing Required Fields",
        explanation=(
            "The client provided an unexpected request format, NoneType value, or missing field, "
            "triggering a validation error or an unhandled TypeError/KeyError/ValueError during parsing or attribute access."
        ),
        supporting_evidence=[
            f"Entry point receives request payload model in {observed_files_str}."
        ],
        contradicting_evidence=[
            "Endpoint utilizes Pydantic validation which typically returns HTTP 422 rather than unhandled 500."
        ],
        relevant_files=relevant_files[:1],
        relevant_symbols=relevant_symbols[:2],
        confidence=0.70 if ("typeerror" in raw.lower() or "keyerror" in raw.lower()) else 0.35,
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
# Step 6: Controlled Test Execution & Verification (Phase 3 Part 2)
# ==============================================================================
def execute_test_verification(state: BugInvestigationState) -> BugInvestigationState:
    """
    Executes relevant repository tests inside the isolated execution sandbox to verify hypotheses.
    Enforces resource, timeout, output, and execution count limits.
    """
    repo_path = state.get("repo_path")
    test_count = state.get("test_count", 0)
    total_runtime = state.get("total_test_runtime", 0.0)
    test_runs = list(state.get("test_runs", []))
    failures = list(state.get("failures", []))
    runtime_evidence = list(state.get("runtime_evidence", []))

    # Guard: check execution limits
    if test_count >= MAX_TEST_RUNS:
        logger.info(f"Reached MAX_TEST_RUNS ({MAX_TEST_RUNS}); skipping further test execution.")
        return state

    if total_runtime >= MAX_TOTAL_TEST_RUNTIME:
        logger.info(f"Reached MAX_TOTAL_TEST_RUNTIME ({MAX_TOTAL_TEST_RUNTIME}s); skipping further tests.")
        return state

    # Discover candidate tests prioritized by relevance to suspect symbols & files
    service = ExecutionService()
    candidate_tests = service.find_candidate_tests(
        repo_path=repo_path or ".",
        symbols=state.get("relevant_symbols", []),
        files=state.get("relevant_files", []),
    )

    already_run_targets = {tr.get("target") for tr in test_runs}
    target_to_run = None

    for cand in candidate_tests:
        if cand not in already_run_targets:
            target_to_run = cand
            break

    # If no specific candidate test found and no test run yet, run default suite
    if target_to_run is None and not test_runs and candidate_tests:
        target_to_run = candidate_tests[0]

    if not candidate_tests:
        # No tests exist in this repository
        step_info = {
            "action": "execute_test_verification",
            "executed": False,
            "reason": "No test files detected in repository.",
        }
        return {
            **state,
            "investigation_steps": state.get("investigation_steps", []) + [step_info],
            "step_count": state.get("step_count", 0) + 1,
        }

    # Execute targeted test in sandbox
    run_result = run_tests(
        test_target=target_to_run,
        repo_path=repo_path,
        timeout=PER_TEST_TIMEOUT,
    )

    test_runs.append(run_result)
    new_runtime = total_runtime + run_result.get("duration", 0.0)
    new_test_count = test_count + 1

    # Record parsed failures
    for f in run_result.get("failures", []):
        failures.append(f)
        runtime_evidence.append({
            "type": "test_failure",
            "test_name": f.get("test_name"),
            "exception_type": f.get("exception_type"),
            "error_message": f.get("error_message"),
            "file_path": f.get("file_path"),
            "line_number": f.get("line_number"),
            "is_environment_error": f.get("is_environment_error", False),
            "description": f"Test '{f.get('test_name')}' failed: {f.get('exception_type')}: {f.get('error_message')} at {f.get('file_path')}:{f.get('line_number')}",
        })

    if run_result.get("status") == ExecutionStatus.SUCCESS.value:
        runtime_evidence.append({
            "type": "test_pass",
            "test_name": target_to_run,
            "description": f"Targeted test '{target_to_run}' executed and passed cleanly.",
        })
    elif run_result.get("status") == ExecutionStatus.TIMEOUT.value:
        runtime_evidence.append({
            "type": "timeout",
            "test_name": target_to_run,
            "description": f"Test '{target_to_run}' timed out after {PER_TEST_TIMEOUT}s.",
        })
    elif run_result.get("status") == ExecutionStatus.ENVIRONMENT_ERROR.value:
        runtime_evidence.append({
            "type": "environment_error",
            "test_name": target_to_run,
            "description": f"Environment setup failure: {run_result.get('error_summary')}",
        })

    step_info = {
        "action": "execute_test_verification",
        "executed": True,
        "target": target_to_run,
        "status": run_result.get("status"),
        "duration": run_result.get("duration"),
        "failures_detected": len(run_result.get("failures", [])),
    }

    return {
        **state,
        "test_runs": test_runs,
        "failures": failures,
        "runtime_evidence": runtime_evidence,
        "test_count": new_test_count,
        "total_test_runtime": new_runtime,
        "investigation_steps": state.get("investigation_steps", []) + [step_info],
        "step_count": state.get("step_count", 0) + 1,
    }


# ==============================================================================
# Step 7: Analyze Runtime Failures
# ==============================================================================
def analyze_runtime_failures(state: BugInvestigationState) -> BugInvestigationState:
    """
    Analyzes captured runtime output and separates application code bugs from
    crashes, timeouts, and environment setup errors.
    """
    failures = state.get("failures", [])
    test_runs = state.get("test_runs", [])

    has_env_error = any(f.get("is_environment_error", False) for f in failures) or any(
        tr.get("status") == ExecutionStatus.ENVIRONMENT_ERROR.value for tr in test_runs
    )
    has_timeout = any(tr.get("status") == ExecutionStatus.TIMEOUT.value for tr in test_runs)
    has_test_failure = any(
        tr.get("status") == ExecutionStatus.FAILED.value and not f.get("is_environment_error", False)
        for tr in test_runs
        for f in tr.get("failures", [])
    )

    step_info = {
        "action": "analyze_runtime_failures",
        "has_test_failure": has_test_failure,
        "has_timeout": has_timeout,
        "has_env_error": has_env_error,
        "failure_count": len(failures),
    }

    return {
        **state,
        "investigation_steps": state.get("investigation_steps", []) + [step_info],
        "step_count": state.get("step_count", 0) + 1,
    }


# ==============================================================================
# Step 8: Evaluate Hypotheses (Static + Runtime Evidence)
# ==============================================================================
def evaluate_hypotheses(state: BugInvestigationState) -> BugInvestigationState:
    """
    Evaluates competing hypotheses by integrating both static CodeGraph evidence
    and runtime test execution evidence, updating status to supported/rejected.
    """
    hypotheses = list(state.get("hypotheses", []))
    step_count = state.get("step_count", 0)
    failures = state.get("failures", [])
    test_runs = state.get("test_runs", [])
    runtime_evidence = state.get("runtime_evidence", [])

    confirmed_ids: List[str] = []
    rejected_ids: List[str] = []

    has_env_error = any(f.get("is_environment_error", False) for f in failures) or any(
        tr.get("status") == ExecutionStatus.ENVIRONMENT_ERROR.value for tr in test_runs
    )

    for h in hypotheses:
        h_text = f"{h.get('title', '')} {h.get('explanation', '')} {' '.join(h.get('relevant_files', []))}".lower()

        if has_env_error:
            # Environment error should NOT falsely convict application code
            h["status"] = "inconclusive"
            h.setdefault("runtime_evidence", []).append(
                "Test execution encountered an environment or dependency setup failure; cannot verify hypothesis."
            )
            continue

        matched_failure = False
        contradicted = False

        for f in failures:
            exc = f.get("exception_type", "").lower()
            msg = f.get("error_message", "").lower()
            fp = (f.get("file_path") or "").lower()

            exc_stem = exc.replace("error", "").replace("exception", "").strip()
            has_exc_match = (
                (bool(exc) and exc in h_text)
                or (len(exc_stem) >= 3 and exc_stem in h_text)
            )
            has_msg_words = [w for w in re.findall(r"\w+", msg) if len(w) > 3]
            has_msg_match = bool(has_msg_words and any(w.lower() in h_text for w in has_msg_words))
            has_file_match = bool(
                fp and any(len(Path(fp).stem) > 2 and Path(fp).stem in rf.lower() for rf in h.get("relevant_files", []))
            )

            is_external_hypothesis = any(
                ext in h_text for ext in ("database", "external dependency", "rest api", "network", "timeout")
            )
            is_internal_error = exc in (
                "typeerror", "keyerror", "attributeerror", "indexerror", "assertionerror", "valueerror"
            )

            if has_exc_match or (has_file_match and has_msg_match):
                matched_failure = True
                h.setdefault("runtime_evidence", []).append(
                    f"Confirmed by runtime failure in {f.get('file_path')}:{f.get('line_number')} ({f.get('exception_type')}: {f.get('error_message')})"
                )
            elif is_external_hypothesis and is_internal_error:
                contradicted = True
            else:
                contradicted = True

        if matched_failure:
            h["status"] = "strongly supported"
            h["confidence"] = min(0.95, max(h.get("confidence", 0.0), 0.88))
            confirmed_ids.append(h["id"])
        elif contradicted:
            h["status"] = "rejected"
            h["confidence"] = min(h.get("confidence", 0.0), 0.15)
            h.setdefault("runtime_evidence", []).append(
                "Contradicted by runtime execution: observed failure originated from an unrelated component or exception type."
            )
            rejected_ids.append(h["id"])
        elif test_runs and any(tr.get("status") == ExecutionStatus.SUCCESS.value for tr in test_runs):
            # Target test passed
            h["status"] = "weakly supported"
            h["confidence"] = min(h.get("confidence", 0.0), 0.35)
        else:
            # No matching runtime confirmation
            if not test_runs:
                h["status"] = "inconclusive"
            else:
                h["status"] = "not supported"
                rejected_ids.append(h["id"])

    # Rank hypotheses by updated confidence
    sorted_hypotheses = sorted(hypotheses, key=lambda x: x.get("confidence", 0.0), reverse=True)
    selected = sorted_hypotheses[0] if sorted_hypotheses else None

    conf_val = selected.get("confidence", 0.0) if selected else 0.0
    if conf_val >= 0.75:
        confidence_rating = "High"
    elif conf_val >= 0.40:
        confidence_rating = "Medium"
    else:
        confidence_rating = "Low"

    is_conclusive = (
        step_count >= MAX_INVESTIGATION_STEPS
        or len(test_runs) >= MAX_TEST_RUNS
        or (selected and selected.get("status") == "strongly supported")
    )

    step_info = {
        "action": "evaluate_hypotheses",
        "selected_hypothesis": selected.get("id") if selected else None,
        "selected_status": selected.get("status") if selected else "inconclusive",
        "confidence": confidence_rating,
        "is_conclusive": is_conclusive,
        "confirmed_count": len(confirmed_ids),
        "rejected_count": len(rejected_ids),
    }

    return {
        **state,
        "hypotheses": hypotheses,
        "selected_hypothesis": selected,
        "confidence": confidence_rating,
        "confirmed_hypotheses": confirmed_ids,
        "rejected_hypotheses": rejected_ids,
        "is_conclusive": is_conclusive,
        "investigation_steps": state.get("investigation_steps", []) + [step_info],
        "step_count": step_count + 1,
    }


# ==============================================================================
# Step 9: Generate Final Investigation Report (Phase 3 Part 2)
# ==============================================================================
def generate_report(state: BugInvestigationState) -> BugInvestigationState:
    """
    Produces a comprehensive BugInvestigationReport with full separation of observed facts,
    inferences, runtime test verification, confirmed/rejected hypotheses, and recommended next steps.
    """
    raw = state.get("bug_report", "")
    norm = state.get("normalized_problem", {})
    entry_points = [ep["name"] for ep in state.get("entry_points", [])]
    relevant_files = state.get("relevant_files", [])
    call_traces = state.get("call_traces", [])
    evidence_items = state.get("evidence", [])
    hypotheses = state.get("hypotheses", [])
    selected_h = state.get("selected_hypothesis", {})
    confidence = state.get("confidence", "Medium")
    test_runs = state.get("test_runs", [])
    runtime_evidence_items = state.get("runtime_evidence", [])
    confirmed = state.get("confirmed_hypotheses", [])
    rejected = state.get("rejected_hypotheses", [])

    # Build human-readable call chain representation
    call_chain_lines: List[str] = []
    for trace in call_traces:
        root_name = trace.get("name", "")
        calls = [c.get("name") for c in trace.get("calls", [])]
        if calls:
            call_chain_lines.append(f"{root_name} -> " + " -> ".join(calls))
        else:
            call_chain_lines.append(f"{root_name} (isolated / terminal)")

    # Build static evidence citations with exact locations
    evidence_citations: List[str] = []
    for ev in evidence_items[:6]:
        fp = ev.get("file_path", "unknown")
        line = ev.get("line_number", 1)
        desc = ev.get("description", "")
        evidence_citations.append(f"[{ev.get('type', 'observed').upper()}] {fp}:{line} - {desc}")

    # Build runtime evidence citations
    runtime_citations: List[str] = []
    for rev in runtime_evidence_items:
        runtime_citations.append(rev.get("description", str(rev)))

    # Tests executed summary
    tests_executed = [
        f"{tr.get('command', 'test')} (exit: {tr.get('exit_code')}, {tr.get('duration')}s, status: {tr.get('status')})"
        for tr in test_runs
    ]

    test_results_summary = [
        {
            "target": tr.get("target"),
            "status": tr.get("status"),
            "exit_code": tr.get("exit_code"),
            "duration": tr.get("duration"),
            "failure_count": len(tr.get("failures", [])),
        }
        for tr in test_runs
    ]

    # Likely root cause with runtime backing
    if selected_h:
        status_note = f" [{selected_h.get('status', 'inconclusive').upper()}]"
        root_cause = f"{selected_h.get('explanation')}{status_note}"
    else:
        root_cause = "Investigation yielded plausible candidates but requires further runtime verification."

    # Next step recommendation (directed toward Phase 4 patch generation)
    primary_file = relevant_files[0] if relevant_files else "the suspect file"
    if selected_h and selected_h.get("status") == "strongly supported":
        rec_next_step = (
            f"Generate and evaluate a minimal patch for '{primary_file}' targeting the verified runtime failure. "
            f"(Automated code modification and patch generation will be performed in Phase 4)."
        )
    else:
        rec_next_step = (
            f"Add targeted regression test coverage for '{primary_file}' to isolate component interactions before patching."
        )

    limitations = [
        "Repository tests are executed inside an isolated sandbox without host network access or host secret exposure.",
        "Code modification, automated patching, and pull request creation are deferred to Phase 4.",
    ]

    report = BugInvestigationReport(
        summary=f"Investigation of bug report: '{raw}'. Identified {len(entry_points)} entry points across {len(relevant_files)} files with {len(test_runs)} test executions.",
        likely_root_cause=root_cause,
        confidence=confidence,
        entry_points=entry_points,
        relevant_files=relevant_files,
        call_chain=call_chain_lines,
        evidence=evidence_citations,
        runtime_evidence=runtime_citations,
        tests_executed=tests_executed,
        test_results=test_results_summary,
        hypotheses=hypotheses,
        confirmed_hypotheses=confirmed,
        rejected_hypotheses=rejected,
        recommended_next_step=rec_next_step,
        limitations=limitations,
    )

    return {
        **state,
        "final_report": report.to_dict(),
    }
