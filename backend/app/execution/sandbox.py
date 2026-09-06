import logging
import os
import re
import resource
import signal
import subprocess
import sys
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from app.execution.models import ExecutionConfig, ExecutionResult, ExecutionStatus

logger = logging.getLogger(__name__)

# Disallowed characters in test target strings to prevent injection or shell abuse
FORBIDDEN_CHARS_PATTERN = re.compile(r"[\;&\|`\$\>\<\\\n\r\t\x00]")


class BaseSandbox(ABC):
    """Abstract interface for sandboxed repository test execution."""

    @abstractmethod
    def execute(
        self,
        command: List[str],
        working_directory: str,
        config: ExecutionConfig,
        framework: Optional[str] = None,
    ) -> ExecutionResult:
        pass


class SubprocessSandbox(BaseSandbox):
    """
    Hardened process-level sandbox for running untrusted repository tests.
    Enforces process isolation, strict environment sanitization (wiping all host secrets),
    working directory confinement, resource limits, timeouts, and output capping.
    """

    @staticmethod
    def validate_target(target: Optional[str], repo_path: str) -> Tuple[bool, Optional[str]]:
        """
        Validates that a test target is safe, does not escape the repository,
        and contains no command-injection payloads.
        """
        if not target:
            return True, None

        # 1. Reject shell metacharacters
        if FORBIDDEN_CHARS_PATTERN.search(target):
            return False, f"Target contains forbidden shell metacharacters: {target!r}"

        # 2. Reject path traversal
        if ".." in target or target.startswith("/") or target.startswith("\\"):
            return False, f"Path traversal or absolute path not allowed: {target!r}"

        # 3. Reject command chaining / arbitrary shell attempts
        disallowed_prefixes = ("rm ", "sudo ", "curl ", "wget ", "sh ", "bash ", "eval ")
        if any(target.strip().lower().startswith(p) for p in disallowed_prefixes):
            return False, f"Target attempts to execute unauthorized commands: {target!r}"

        # 4. Resolve relative path within repo
        # Note: target might contain test item selector like 'tests/test_foo.py::test_bar'
        file_part = target.split("::")[0].strip()
        if file_part.endswith(".py"):
            target_path = (Path(repo_path) / file_part).resolve()
            repo_resolved = Path(repo_path).resolve()
            try:
                target_path.relative_to(repo_resolved)
            except ValueError:
                return False, f"Target file escapes repository root: {target!r}"

        return True, None

    def _sanitize_environment(self, repo_path: str, config: ExecutionConfig) -> Dict[str, str]:
        """
        Creates an isolated, pristine environment dictionary.
        Strictly strips all host credentials, API keys, database URLs, and CodeScout secrets.
        """
        clean_env: Dict[str, str] = {}

        # Whitelist minimal system variables if present
        for var in ("PATH", "LANG", "LC_ALL", "TMPDIR", "TERM"):
            val = os.environ.get(var)
            if val:
                clean_env[var] = val

        # Ensure minimal PATH fallback
        if "PATH" not in clean_env:
            clean_env["PATH"] = "/usr/local/bin:/usr/bin:/bin"

        # Python sandbox flags
        clean_env["PYTHONPATH"] = str(Path(repo_path).resolve())
        clean_env["PYTHONDONTWRITEBYTECODE"] = "1"
        clean_env["PYTHONUNBUFFERED"] = "1"

        # Network isolation via dead proxy sinks if allow_network is False
        if not config.allow_network:
            clean_env["http_proxy"] = "http://127.0.0.1:0"
            clean_env["https_proxy"] = "http://127.0.0.1:0"
            clean_env["all_proxy"] = "http://127.0.0.1:0"
            clean_env["NO_PROXY"] = ""
            clean_env["PIP_NO_INDEX"] = "1"
            clean_env["CURL_CA_BUNDLE"] = ""

        # Double check: ensure no sensitive keys leaked through
        forbidden_substrings = ("KEY", "SECRET", "TOKEN", "PASSWORD", "DATABASE", "POSTGRES", "GEMINI", "AWS")
        for key in list(clean_env.keys()):
            if any(sub in key.upper() for sub in forbidden_substrings):
                del clean_env[key]

        return clean_env

    def _set_resource_limits(self, config: ExecutionConfig):
        """Preexec hook to set process session and POSIX resource limits."""
        # Create a new process session so the entire process group can be killed on timeout
        try:
            os.setsid()
        except Exception:
            pass

        # Apply POSIX resource limits where supported
        try:
            # CPU time limit (soft=timeout, hard=timeout+5)
            cpu_sec = int(config.per_test_timeout)
            resource.setrlimit(resource.RLIMIT_CPU, (cpu_sec, cpu_sec + 5))
        except Exception:
            pass

        try:
            # Process limit to prevent fork bombs (if supported on platform)
            if hasattr(resource, "RLIMIT_NPROC"):
                resource.setrlimit(resource.RLIMIT_NPROC, (256, 256))
        except Exception:
            pass

    def execute(
        self,
        command: List[str],
        working_directory: str,
        config: ExecutionConfig,
        framework: Optional[str] = None,
    ) -> ExecutionResult:
        """
        Executes a test command inside the isolated subprocess sandbox.
        Never executes via shell.
        """
        repo_dir = str(Path(working_directory).resolve())
        clean_env = self._sanitize_environment(repo_dir, config)
        cmd_str = " ".join(command)

        start_time = time.time()
        timed_out = False
        truncated = False
        exit_code = 1
        stdout_bytes = b""
        stderr_bytes = b""

        proc = None
        try:
            # Use os.setsid on POSIX to enable killpg
            preexec = (lambda: self._set_resource_limits(config)) if os.name == "posix" else None

            proc = subprocess.Popen(
                command,
                cwd=repo_dir,
                env=clean_env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=preexec,
                close_fds=True,
                shell=False,  # Security requirement: NEVER use shell=True
            )

            try:
                stdout_bytes, stderr_bytes = proc.communicate(timeout=config.per_test_timeout)
                exit_code = proc.returncode
            except subprocess.TimeoutExpired:
                timed_out = True
                exit_code = 124  # Standard timeout exit code
                # Terminate the entire process group
                if os.name == "posix":
                    try:
                        os.killpg(proc.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                else:
                    proc.kill()

                # Read remaining output if any
                try:
                    stdout_bytes, stderr_bytes = proc.communicate(timeout=2)
                except Exception:
                    pass

        except FileNotFoundError as e:
            return ExecutionResult(
                command=cmd_str,
                exit_code=127,
                stdout="",
                stderr=f"Executable or runner not found: {e}",
                timed_out=False,
                duration=time.time() - start_time,
                working_directory=repo_dir,
                test_framework=framework,
                status=ExecutionStatus.ENVIRONMENT_ERROR,
                error_summary=f"Execution environment failure: {e}",
            )
        except Exception as e:
            return ExecutionResult(
                command=cmd_str,
                exit_code=1,
                stdout="",
                stderr=f"Sandbox execution error: {e}",
                timed_out=False,
                duration=time.time() - start_time,
                working_directory=repo_dir,
                test_framework=framework,
                status=ExecutionStatus.CRASHED,
                error_summary=f"Sandbox crash: {e}",
            )

        duration = round(time.time() - start_time, 3)

        # Enforce output caps
        if len(stdout_bytes) > config.max_output_size:
            stdout_bytes = stdout_bytes[: config.max_output_size]
            stdout_str = stdout_bytes.decode("utf-8", errors="replace") + f"\n\n[Output truncated at {config.max_output_size // 1024} KB limit]"
            truncated = True
        else:
            stdout_str = stdout_bytes.decode("utf-8", errors="replace")

        if len(stderr_bytes) > config.max_output_size:
            stderr_bytes = stderr_bytes[: config.max_output_size]
            stderr_str = stderr_bytes.decode("utf-8", errors="replace") + f"\n\n[Stderr truncated at {config.max_output_size // 1024} KB limit]"
            truncated = True
        else:
            stderr_str = stderr_bytes.decode("utf-8", errors="replace")

        # Determine execution status
        if timed_out:
            status = ExecutionStatus.TIMEOUT
            error_summary = f"Test execution timed out after {config.per_test_timeout} seconds."
        elif exit_code == 0:
            status = ExecutionStatus.SUCCESS
            error_summary = None
        else:
            # Check for missing modules or setup issues in stderr/stdout
            combined_output = stdout_str + "\n" + stderr_str
            if "ModuleNotFoundError:" in combined_output or "ImportError:" in combined_output:
                status = ExecutionStatus.ENVIRONMENT_ERROR
                error_summary = "Environment/setup error: Missing module or import dependency."
            else:
                status = ExecutionStatus.FAILED
                error_summary = f"Test run failed with exit code {exit_code}."

        return ExecutionResult(
            command=cmd_str,
            exit_code=exit_code,
            stdout=stdout_str,
            stderr=stderr_str,
            timed_out=timed_out,
            duration=duration,
            working_directory=repo_dir,
            test_framework=framework,
            truncated_output=truncated,
            status=status,
            error_summary=error_summary,
        )


class DockerSandbox(BaseSandbox):
    """
    Containerized execution sandbox using Docker when available.
    Falls back to SubprocessSandbox if Docker is not installed or unreachable.
    """

    def __init__(self, fallback_sandbox: Optional[BaseSandbox] = None):
        self.fallback = fallback_sandbox or SubprocessSandbox()

    @staticmethod
    def is_docker_available() -> bool:
        try:
            res = subprocess.run(
                ["docker", "info"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=2,
            )
            return res.returncode == 0
        except Exception:
            return False

    def execute(
        self,
        command: List[str],
        working_directory: str,
        config: ExecutionConfig,
        framework: Optional[str] = None,
    ) -> ExecutionResult:
        if not self.is_docker_available():
            logger.info("Docker daemon not available; falling back to SubprocessSandbox.")
            return self.fallback.execute(command, working_directory, config, framework)

        # Build secure docker container invocation with read-only repo mount and no network
        repo_dir = str(Path(working_directory).resolve())
        docker_cmd = [
            "docker",
            "run",
            "--rm",
            "--network",
            "none" if not config.allow_network else "bridge",
            "--memory",
            f"{config.max_memory_mb}m",
            "--cpus",
            "1.0",
            "--pids-limit",
            "100",
            "-v",
            f"{repo_dir}:/workspace:ro",
            "-w",
            "/workspace",
            "python:3.12-slim",
        ] + command

        # Subprocess execution for docker command itself
        try:
            start_time = time.time()
            res = subprocess.run(
                docker_cmd,
                capture_output=True,
                timeout=config.per_test_timeout,
                text=True,
            )
            duration = round(time.time() - start_time, 3)
            return ExecutionResult(
                command=" ".join(docker_cmd),
                exit_code=res.returncode,
                stdout=res.stdout[: config.max_output_size],
                stderr=res.stderr[: config.max_output_size],
                timed_out=False,
                duration=duration,
                working_directory=repo_dir,
                test_framework=framework,
                status=ExecutionStatus.SUCCESS if res.returncode == 0 else ExecutionStatus.FAILED,
            )
        except subprocess.TimeoutExpired:
            return ExecutionResult(
                command=" ".join(docker_cmd),
                exit_code=124,
                stdout="",
                stderr="Docker execution timed out",
                timed_out=True,
                duration=config.per_test_timeout,
                working_directory=repo_dir,
                test_framework=framework,
                status=ExecutionStatus.TIMEOUT,
            )
        except Exception as e:
            return self.fallback.execute(command, working_directory, config, framework)
