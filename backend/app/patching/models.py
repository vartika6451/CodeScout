from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class PatchStatus(str, Enum):
    """Lifecycle status of a generated patch."""

    PROPOSED = "proposed"
    APPLIED = "applied"
    VERIFIED = "verified"
    FAILED = "failed"
    REVERTED = "reverted"


class VerificationStatus(str, Enum):
    """Result status of patch verification through test execution."""

    FIX_VERIFIED = "FIX_VERIFIED"
    PATCH_PROPOSED = "PATCH_PROPOSED"
    PATCH_FAILED = "PATCH_FAILED"
    INCONCLUSIVE = "INCONCLUSIVE"
    PRE_EXISTING_FAILURES = "PRE_EXISTING_FAILURES"


@dataclass
class FilePatch:
    """Individual file modification proposed within a patch."""

    file_path: str
    original_content: str
    proposed_content: str
    start_line: Optional[int] = None
    end_line: Optional[int] = None
    target_content: Optional[str] = None
    replacement: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Patch:
    """Structured representation of a proposed code modification."""

    patch_id: str
    files_changed: List[FilePatch]
    description: str
    reason: str
    diff: str = ""
    confidence: float = 0.0
    status: PatchStatus = PatchStatus.PROPOSED
    iteration: int = 1

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["status"] = self.status.value
        data["files_changed"] = [fp.to_dict() for fp in self.files_changed]
        return data


@dataclass
class PatchVerificationResult:
    """Comprehensive test verification outcome for an applied patch."""

    patch_id: str
    status: VerificationStatus
    targeted_test_result: Optional[Dict[str, Any]] = None
    related_test_results: List[Dict[str, Any]] = field(default_factory=list)
    pre_existing_failures: List[str] = field(default_factory=list)
    fixed_failures: List[str] = field(default_factory=list)
    new_regressions: List[str] = field(default_factory=list)
    diff: str = ""
    iterations_used: int = 1

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["status"] = self.status.value
        return data


@dataclass
class PatchAttempt:
    """Historical record of an individual patch iteration attempt."""

    iteration: int
    patch_id: str
    description: str
    diff: str
    verification_status: str
    fixed_failures: List[str] = field(default_factory=list)
    new_regressions: List[str] = field(default_factory=list)
    error_summary: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
