import json
import logging
import os
import re
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from google import genai

from app.patching.diff import generate_unified_diff
from app.patching.models import FilePatch, Patch, PatchStatus

load_dotenv()
logger = logging.getLogger(__name__)


class PatchGenerator:
    """
    Synthesizes minimal, evidence-backed code patches targeting the exact root cause
    confirmed by static investigation and runtime test execution.
    """

    @classmethod
    def generate_patch(
        cls,
        bug_report: str,
        root_cause: str,
        repo_path: str,
        failures: Optional[List[Dict[str, Any]]] = None,
        relevant_files: Optional[List[str]] = None,
        runtime_evidence: Optional[List[Dict[str, Any]]] = None,
        iteration: int = 1,
        previous_attempts: Optional[List[Dict[str, Any]]] = None,
    ) -> Optional[Patch]:
        """
        Generates a structured Patch targeting the identified failure point.
        Uses LLM synthesis when available and falls back to deterministic minimal templates.
        """
        repo_root = Path(repo_path).resolve()

        # 1. Identify primary target file and line
        target_file_rel: Optional[str] = None
        target_line: Optional[int] = None
        exception_type: str = ""
        error_message: str = ""

        if failures:
            f = failures[0]
            target_file_rel = f.get("file_path")
            target_line = f.get("line_number")
            exception_type = f.get("exception_type", "")
            error_message = f.get("error_message", "")

        if not target_file_rel and relevant_files:
            target_file_rel = relevant_files[0]

        if not target_file_rel:
            logger.warning("No target file identified for patch generation.")
            return None

        # Clean file path relative to repo_root
        target_file_path = (repo_root / target_file_rel).resolve()
        if not target_file_path.is_file():
            # Search for matching file name in repo
            fname = Path(target_file_rel).name
            candidates = list(repo_root.rglob(fname))
            if candidates:
                target_file_path = candidates[0]
                target_file_rel = str(target_file_path.relative_to(repo_root))
            else:
                logger.warning(f"Target file does not exist: {target_file_path}")
                return None

        try:
            original_content = target_file_path.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            logger.error(f"Failed to read target file {target_file_path}: {e}")
            return None

        # 2. Try LLM synthesis first if API key is present
        patch_proposal = cls._synthesize_with_llm(
            bug_report=bug_report,
            root_cause=root_cause,
            file_rel=target_file_rel,
            target_line=target_line,
            file_content=original_content,
            exception_type=exception_type,
            error_message=error_message,
            iteration=iteration,
            previous_attempts=previous_attempts,
        )

        # 3. Fallback to deterministic synthesis if LLM unavailable/failed
        if not patch_proposal:
            patch_proposal = cls._synthesize_deterministic(
                file_rel=target_file_rel,
                target_line=target_line,
                file_content=original_content,
                exception_type=exception_type,
                error_message=error_message,
                iteration=iteration,
            )

        if not patch_proposal:
            return None

        # 4. Construct FilePatch and Patch models
        file_patch = FilePatch(
            file_path=target_file_rel,
            original_content=original_content,
            proposed_content=patch_proposal.get("proposed_content", ""),
            start_line=patch_proposal.get("start_line"),
            end_line=patch_proposal.get("end_line"),
            target_content=patch_proposal.get("target_content"),
            replacement=patch_proposal.get("replacement"),
        )

        # Pre-compute diff for display
        patch_obj = Patch(
            patch_id=f"PATCH-{uuid.uuid4().hex[:8].upper()}",
            files_changed=[file_patch],
            description=patch_proposal.get("description", f"Fix {exception_type or 'bug'} in {target_file_rel}"),
            reason=patch_proposal.get("reason", root_cause),
            confidence=patch_proposal.get("confidence", 0.85),
            status=PatchStatus.PROPOSED,
            iteration=iteration,
        )

        # Compute initial diff representation
        from app.patching.applier import PatchApplier
        proposed_text = PatchApplier._compute_new_content(file_patch, original_content)
        file_patch.proposed_content = proposed_text
        patch_obj.diff = generate_unified_diff(original_content, proposed_text, target_file_rel)

        return patch_obj

    @classmethod
    def _synthesize_with_llm(
        cls,
        bug_report: str,
        root_cause: str,
        file_rel: str,
        target_line: Optional[int],
        file_content: str,
        exception_type: str,
        error_message: str,
        iteration: int,
        previous_attempts: Optional[List[Dict[str, Any]]],
    ) -> Optional[Dict[str, Any]]:
        """Invokes Gemini API to generate a minimal structured patch proposal."""
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            return None

        # Build context lines
        lines = file_content.splitlines()
        start_context = max(1, (target_line or 1) - 10)
        end_context = min(len(lines), (target_line or 1) + 10)
        annotated_snippet = "\n".join(
            f"{i + 1:4d} | {lines[i]}" for i in range(start_context - 1, end_context)
        )

        prev_info = ""
        if previous_attempts:
            prev_info = f"\nPrevious failed patch attempts: {json.dumps(previous_attempts, default=str)}"

        prompt = (
            f"You are an expert software engineer fixing a bug in an existing repository.\n\n"
            f"Bug Report: {bug_report}\n"
            f"Root Cause: {root_cause}\n"
            f"Exception: {exception_type}: {error_message}\n"
            f"Failing File: {file_rel} (around line {target_line})\n\n"
            f"Code snippet:\n{annotated_snippet}\n{prev_info}\n\n"
            f"Task: Generate a minimal, surgical patch to fix this bug. Do NOT rewrite the entire file.\n"
            f"Respond ONLY with a valid JSON object matching this schema:\n"
            f"{{\n"
            f'  "start_line": <integer>,\n'
            f'  "end_line": <integer>,\n'
            f'  "target_content": "<exact lines being replaced>",\n'
            f'  "replacement": "<exact replacement code>",\n'
            f'  "description": "<short description of fix>",\n'
            f'  "reason": "<why this fixes the root cause>",\n'
            f'  "confidence": <float between 0.0 and 1.0>\n'
            f"}}"
        )

        try:
            client = genai.Client(api_key=api_key)
            response = client.models.generate_content(
                model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip(),
                contents=prompt,
            )
            text = response.text.strip()
            # Clean markdown code fence if present
            if text.startswith("```"):
                text = re.sub(r"^```(?:json)?\n?", "", text)
                text = re.sub(r"\n?```$", "", text)

            data = json.loads(text.strip())
            if "start_line" in data and "replacement" in data:
                return data
        except Exception as e:
            logger.debug(f"LLM patch synthesis failed: {e}")

        return None

    @classmethod
    def _synthesize_deterministic(
        cls,
        file_rel: str,
        target_line: Optional[int],
        file_content: str,
        exception_type: str,
        error_message: str,
        iteration: int,
    ) -> Optional[Dict[str, Any]]:
        """
        Deterministic, rule-based minimal patch synthesis when LLM is unavailable.
        Handles common bug patterns: NoneType subscript, KeyError, missing guard.
        """
        lines = file_content.splitlines()
        line_idx = (target_line - 1) if (target_line and 1 <= target_line <= len(lines)) else 0
        current_line = lines[line_idx] if lines else ""
        indent = re.match(r"^\s*", current_line).group(0)

        # Pattern 1: TypeError: 'NoneType' object is not subscriptable (e.g. user['name'] or obj[key])
        if "typeerror" in exception_type.lower() or "nonetype" in error_message.lower():
            # Matches obj[something]
            sub_match = re.search(r"([A-Za-z_][A-Za-z0-9_]*)\s*\[([^\]]+)\]", current_line)
            if sub_match:
                var_name = sub_match.group(1)
                key_expr = sub_match.group(2)

                if iteration == 1:
                    # Strategy 1: Safely guard variable before access
                    replacement = (
                        f"{indent}if {var_name} is None:\n"
                        f"{indent}    return None\n"
                        f"{current_line}"
                    )
                    return {
                        "start_line": line_idx + 1,
                        "end_line": line_idx + 1,
                        "target_content": current_line,
                        "replacement": replacement,
                        "description": f"Add None check for '{var_name}' before subscript access",
                        "reason": f"Prevents TypeError when '{var_name}' is None.",
                        "confidence": 0.90,
                    }
                else:
                    # Strategy 2: Safe dictionary .get with fallback
                    safe_expr = f"({var_name}.get({key_expr}) if isinstance({var_name}, dict) else None)"
                    replaced_line = current_line.replace(sub_match.group(0), safe_expr)
                    return {
                        "start_line": line_idx + 1,
                        "end_line": line_idx + 1,
                        "target_content": current_line,
                        "replacement": replaced_line,
                        "description": f"Use safe .get() lookup for '{var_name}'",
                        "reason": f"Safely retrieves {key_expr} without raising TypeError.",
                        "confidence": 0.88,
                    }

        # Pattern 2: KeyError (e.g. headers['Authorization'] -> headers.get('Authorization'))
        if "keyerror" in exception_type.lower():
            sub_match = re.search(r"([A-Za-z_][A-Za-z0-9_]*)\s*\[([^\]]+)\]", current_line)
            if sub_match:
                var_name = sub_match.group(1)
                key_expr = sub_match.group(2)
                safe_expr = f"{var_name}.get({key_expr})"
                replaced_line = current_line.replace(sub_match.group(0), safe_expr)
                return {
                    "start_line": line_idx + 1,
                    "end_line": line_idx + 1,
                    "target_content": current_line,
                    "replacement": replaced_line,
                    "description": f"Replace dict bracket index with safe .get({key_expr})",
                    "reason": f"Avoids KeyError when key {key_expr} is absent from {var_name}.",
                    "confidence": 0.90,
                }

        # Pattern 3: ZeroDivisionError
        if "zerodivisionerror" in exception_type.lower():
            div_match = re.search(r"/\s*([A-Za-z_][A-Za-z0-9_]*)", current_line)
            if div_match:
                denom = div_match.group(1)
                replacement = (
                    f"{indent}if {denom} == 0:\n"
                    f"{indent}    return 0\n"
                    f"{current_line}"
                )
                return {
                    "start_line": line_idx + 1,
                    "end_line": line_idx + 1,
                    "target_content": current_line,
                    "replacement": replacement,
                    "description": f"Add zero-divisor guard for '{denom}'",
                    "reason": "Prevents ZeroDivisionError.",
                    "confidence": 0.92,
                }

        # Generic defensive fallback: if statement guard on target line
        generic_replacement = (
            f"{indent}try:\n"
            f"    {current_line.strip()}\n"
            f"{indent}except Exception:\n"
            f"{indent}    pass"
        )
        return {
            "start_line": line_idx + 1,
            "end_line": line_idx + 1,
            "target_content": current_line,
            "replacement": generic_replacement,
            "description": f"Safely catch unhandled exception in {file_rel}",
            "reason": "Guards execution against unexpected runtime failure.",
            "confidence": 0.60,
        }
