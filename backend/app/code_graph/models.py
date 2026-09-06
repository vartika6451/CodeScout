from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ImportInfo:
    """Represents an import statement in Python source code."""

    module: Optional[str]
    name: str
    alias: Optional[str] = None
    is_from_import: bool = False
    line_number: Optional[int] = None
    end_line_number: Optional[int] = None

    @property
    def imported_as(self) -> str:
        """Returns the local identifier bound by this import."""
        return self.alias if self.alias else self.name


@dataclass
class Function:
    """Represents a function or method definition."""

    name: str
    file_path: str
    line_number: int
    end_line_number: Optional[int] = None
    calls: List[str] = field(default_factory=list)
    is_async: bool = False
    is_method: bool = False
    class_name: Optional[str] = None


@dataclass
class Class:
    """Represents a class definition."""

    name: str
    file_path: str
    line_number: int
    end_line_number: Optional[int] = None
    base_classes: List[str] = field(default_factory=list)
    methods: List[Function] = field(default_factory=list)


@dataclass
class File:
    """Represents the structural breakdown of a single Python source file."""

    file_path: str
    imports: List[ImportInfo] = field(default_factory=list)
    functions: List[Function] = field(default_factory=list)  # Top-level functions
    classes: List[Class] = field(default_factory=list)

    @property
    def all_functions(self) -> List[Function]:
        """Returns both top-level functions and class methods."""
        all_funcs = list(self.functions)
        for cls in self.classes:
            all_funcs.extend(cls.methods)
        return all_funcs


@dataclass
class RepositoryAnalysis:
    """Aggregated structural information for an entire repository."""

    repo_path: str
    files: List[File] = field(default_factory=list)
    parse_failures: Dict[str, str] = field(default_factory=dict)

    @property
    def files_analyzed(self) -> int:
        return len(self.files)

    @property
    def classes_found(self) -> int:
        return sum(len(f.classes) for f in self.files)

    @property
    def functions_found(self) -> int:
        """Total functions across the repository including methods."""
        return sum(len(f.all_functions) for f in self.files)

    @property
    def top_level_functions_found(self) -> int:
        return sum(len(f.functions) for f in self.files)

    @property
    def methods_found(self) -> int:
        return sum(sum(len(c.methods) for c in f.classes) for f in self.files)

    @property
    def imports_found(self) -> int:
        return sum(len(f.imports) for f in self.files)

    @property
    def function_calls_found(self) -> int:
        return sum(sum(len(fn.calls) for fn in f.all_functions) for f in self.files)

    @property
    def parse_failures_count(self) -> int:
        return len(self.parse_failures)

    def summary(self) -> Dict[str, Any]:
        return {
            "files_analyzed": self.files_analyzed,
            "classes_found": self.classes_found,
            "functions_found": self.functions_found,
            "top_level_functions_found": self.top_level_functions_found,
            "methods_found": self.methods_found,
            "imports_found": self.imports_found,
            "function_calls_found": self.function_calls_found,
            "parse_failures": self.parse_failures_count,
        }
