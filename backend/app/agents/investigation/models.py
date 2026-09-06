from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, TypedDict


@dataclass
class NormalizedProblem:
    """Structured internal representation of a bug report."""

    raw_report: str
    component: Optional[str] = None
    endpoint_or_operation: Optional[str] = None
    error_type: Optional[str] = None
    observed_behavior: Optional[str] = None
    investigation_target: str = ""
    known_facts: List[str] = field(default_factory=list)
    assumptions: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Hypothesis:
    """A plausible root-cause explanation backed by supporting, contradicting, and runtime evidence."""

    id: str  # e.g., 'H1', 'H2'
    title: str
    explanation: str
    supporting_evidence: List[str] = field(default_factory=list)
    contradicting_evidence: List[str] = field(default_factory=list)
    relevant_files: List[str] = field(default_factory=list)
    relevant_symbols: List[str] = field(default_factory=list)
    confidence: float = 0.0  # Estimated confidence between 0.0 and 1.0
    status: str = "inconclusive"  # 'strongly supported', 'supported', 'weakly supported', 'not supported', 'rejected', 'inconclusive'
    runtime_evidence: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class BugInvestigationReport:
    """Comprehensive, structured debugging report with runtime verification and proposed patch."""

    summary: str
    likely_root_cause: str
    confidence: str  # 'High', 'Medium', or 'Low'
    entry_points: List[str] = field(default_factory=list)
    relevant_files: List[str] = field(default_factory=list)
    call_chain: List[str] = field(default_factory=list)
    evidence: List[str] = field(default_factory=list)
    runtime_evidence: List[str] = field(default_factory=list)
    tests_executed: List[str] = field(default_factory=list)
    test_results: List[Dict[str, Any]] = field(default_factory=list)
    hypotheses: List[Dict[str, Any]] = field(default_factory=list)
    confirmed_hypotheses: List[str] = field(default_factory=list)
    rejected_hypotheses: List[str] = field(default_factory=list)

    # Phase 4: Patch Generation & Verification Fields
    patch_summary: Optional[str] = None
    files_changed: List[str] = field(default_factory=list)
    diff: Optional[str] = None
    verification_status: str = "INCONCLUSIVE"  # 'FIX_VERIFIED', 'PATCH_PROPOSED', 'PATCH_FAILED', 'INCONCLUSIVE', 'PRE_EXISTING_FAILURES'
    pre_existing_failures: List[str] = field(default_factory=list)
    new_failures: List[str] = field(default_factory=list)
    patch_iterations: int = 0
    patch_history: List[Dict[str, Any]] = field(default_factory=list)
    user_review_required: bool = True

    recommended_next_step: str = ""
    limitations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class BugInvestigationState(TypedDict, total=False):
    """LangGraph agent state throughout the bug investigation lifecycle."""

    bug_report: str
    repository: str
    repo_path: Optional[str]

    normalized_problem: Dict[str, Any]
    error_type: Optional[str]
    suspected_components: List[str]
    entry_points: List[Dict[str, Any]]

    evidence: List[Dict[str, Any]]
    relevant_files: List[str]
    relevant_symbols: List[str]
    call_traces: List[Dict[str, Any]]

    # Runtime verification & execution state
    test_runs: List[Dict[str, Any]]
    runtime_evidence: List[Dict[str, Any]]
    failures: List[Dict[str, Any]]
    confirmed_hypotheses: List[str]
    rejected_hypotheses: List[str]
    test_count: int
    total_test_runtime: float

    # Phase 4: Patching & Safe Verification state
    proposed_patch: Optional[Dict[str, Any]]
    patch_diff: Optional[str]
    patch_history: List[Dict[str, Any]]
    patch_iteration: int
    max_patch_iterations: int
    verification_result: Optional[Dict[str, Any]]
    final_status: str
    isolated_workspace_path: Optional[str]

    hypotheses: List[Dict[str, Any]]
    selected_hypothesis: Optional[Dict[str, Any]]
    confidence: str

    investigation_steps: List[Dict[str, Any]]
    step_count: int
    is_conclusive: bool

    final_report: Dict[str, Any]


