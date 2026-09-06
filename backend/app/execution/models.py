from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class ExecutionStatus(str, Enum):
    """Status classification for a test execution attempt."""

    SUCCESS = "passed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CRASHED = "crashed"
    ENVIRONMENT_ERROR = "environment_error"
    SECURITY_VIOLATION = "security_violation"


@dataclass
class ExecutionConfig:
    """Security and resource limits for the sandbox execution environment."""

    max_output_size: int = 100 * 1024  # 100 KB max stdout/stderr
    per_test_timeout: float = 60.0  # seconds
    max_total_runtime: float = 180.0  # seconds
    max_test_runs: int = 5
    allow_network: bool = False
    max_memory_mb: int = 512
    python_binary: Optional[str] = None


@dataclass
class ParsedFailure:
    """Structured failure information extracted deterministically from test output / tracebacks."""

    test_name: str
    failure_type: str  # e.g., 'FAIL', 'ERROR', 'CRASH', 'ENVIRONMENT'
    exception_type: str  # e.g., 'KeyError', 'TypeError', 'ModuleNotFoundError'
    error_message: str
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    stack_trace: List[str] = field(default_factory=list)
    is_environment_error: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ExecutionResult:
    """Complete, structured representation of a test execution attempt."""

    command: str
    exit_code: int
    stdout: str
    stderr: str
    timed_out: bool
    duration: float
    working_directory: str
    test_framework: Optional[str] = None
    truncated_output: bool = False
    status: ExecutionStatus = ExecutionStatus.SUCCESS
    failures: List[ParsedFailure] = field(default_factory=list)
    error_summary: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["status"] = self.status.value
        data["failures"] = [f.to_dict() for f in self.failures]
        return data
