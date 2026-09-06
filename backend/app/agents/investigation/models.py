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
    """A plausible root-cause explanation backed by supporting and contradicting evidence."""

    id: str  # e.g., 'H1', 'H2'
    title: str
    explanation: str
    supporting_evidence: List[str] = field(default_factory=list)
    contradicting_evidence: List[str] = field(default_factory=list)
    relevant_files: List[str] = field(default_factory=list)
    relevant_symbols: List[str] = field(default_factory=list)
    confidence: float = 0.0  # Estimated confidence between 0.0 and 1.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class BugInvestigationReport:
    """Comprehensive, structured debugging report."""

    summary: str
    likely_root_cause: str
    confidence: str  # 'High', 'Medium', or 'Low'
    entry_points: List[str] = field(default_factory=list)
    relevant_files: List[str] = field(default_factory=list)
    call_chain: List[str] = field(default_factory=list)
    evidence: List[str] = field(default_factory=list)
    hypotheses: List[Dict[str, Any]] = field(default_factory=list)
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

    hypotheses: List[Dict[str, Any]]
    selected_hypothesis: Optional[Dict[str, Any]]
    confidence: str

    investigation_steps: List[Dict[str, Any]]
    step_count: int
    is_conclusive: bool

    final_report: Dict[str, Any]
