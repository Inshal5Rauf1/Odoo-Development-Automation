"""Docker lifecycle management for Odoo module validation.

Manages ephemeral Docker Compose environments (Odoo 17 + PostgreSQL 16)
for module installation and test execution. Containers are always torn
down after validation, even on errors.
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
from pathlib import Path

from odoo_gen_utils.validation.log_parser import parse_install_log, parse_test_log
from odoo_gen_utils.validation.types import InstallResult, TestResult

logger = logging.getLogger(__name__)


def check_docker_available() -> bool:
    """Check if Docker CLI is present and functional.

    Returns:
        True if docker is installed and the daemon is reachable.
    """
    if shutil.which("docker") is None:
        return False

    try:
        result = subprocess.run(
            ["docker", "info"],
            capture_output=True,
            timeout=10,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, OSError):
        return False


def get_compose_file() -> Path:
    """Return the path to docker/docker-compose.yml shipped with the extension.

    Navigates from validation/ up to the project root's docker/ directory.
    """
    return (
        Path(__file__).parent.parent.parent.parent.parent
        / "docker"
        / "docker-compose.yml"
    )


def _run_compose(
    compose_file: Path,
    args: list[str],
    env: dict[str, str],
    timeout: int = 120,
) -> subprocess.CompletedProcess[str]:
    """Run a docker compose command with the given arguments.

    Args:
        compose_file: Path to docker-compose.yml.
        args: Arguments to pass after 'docker compose -f <file>'.
        env: Environment variables to merge with os.environ.
        timeout: Subprocess timeout in seconds.

    Returns:
        CompletedProcess with stdout and stderr captured as text.
    """
    cmd = ["docker", "compose", "-f", str(compose_file), *args]
    merged_env = {**os.environ, **env}
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
        env=merged_env,
    )


def _teardown(compose_file: Path, env: dict[str, str]) -> None:
    """Tear down Docker containers and volumes.

    Runs 'docker compose down -v --remove-orphans'. This function
    catches all exceptions because teardown must never raise.
    """
    try:
        cmd = [
            "docker",
            "compose",
            "-f",
            str(compose_file),
            "down",
            "-v",
            "--remove-orphans",
        ]
        merged_env = {**os.environ, **env}
        subprocess.run(
            cmd,
            capture_output=True,
            timeout=60,
            env=merged_env,
        )
    except Exception:
        logger.warning("Failed to tear down Docker containers", exc_info=True)


def docker_install_module(
    module_path: Path,
    compose_file: Path | None = None,
    timeout: int = 300,
) -> InstallResult:
    """Install an Odoo module in an ephemeral Docker environment.

    Starts Odoo 17 + PostgreSQL 16 containers, runs module installation,
    parses the log output for success/failure, and tears down containers.

    Args:
        module_path: Path to the Odoo module directory.
        compose_file: Path to docker-compose.yml. Uses default if None.
        timeout: Timeout in seconds for the install command.

    Returns:
        InstallResult with success status, log output, and error message.
    """
    if not check_docker_available():
        return InstallResult(
            success=False,
            log_output="",
            error_message="Docker not available",
        )

    if compose_file is None:
        compose_file = get_compose_file()

    module_name = module_path.name
    env = {
        "MODULE_PATH": str(module_path.resolve()),
        "MODULE_NAME": module_name,
    }

    try:
        # Start services and wait for health checks
        _run_compose(compose_file, ["up", "-d", "--wait"], env, timeout=120)

        # Install the module
        result = _run_compose(
            compose_file,
            [
                "exec",
                "-T",
                "odoo",
                "odoo",
                "-i",
                module_name,
                "-d",
                "test_db",
                "--stop-after-init",
                "--no-http",
                "--log-level=info",
            ],
            env,
            timeout=timeout,
        )

        combined_output = result.stdout + result.stderr
        success, error_msg = parse_install_log(combined_output)

        return InstallResult(
            success=success,
            log_output=combined_output,
            error_message=error_msg,
        )
    except subprocess.TimeoutExpired:
        return InstallResult(
            success=False,
            log_output="",
            error_message=f"Timeout after {timeout}s waiting for module install",
        )
    except Exception as exc:
        return InstallResult(
            success=False,
            log_output="",
            error_message=str(exc),
        )
    finally:
        _teardown(compose_file, env)


def docker_run_tests(
    module_path: Path,
    compose_file: Path | None = None,
    timeout: int = 600,
) -> tuple[TestResult, ...]:
    """Run Odoo module tests in an ephemeral Docker environment.

    Starts Odoo 17 + PostgreSQL 16 containers, runs module tests with
    --test-enable, parses per-test results from the log output, and
    tears down containers.

    Args:
        module_path: Path to the Odoo module directory.
        compose_file: Path to docker-compose.yml. Uses default if None.
        timeout: Timeout in seconds for the test command.

    Returns:
        Tuple of TestResult, one per test found. Empty tuple if Docker
        is not available or no tests found.
    """
    if not check_docker_available():
        return ()

    if compose_file is None:
        compose_file = get_compose_file()

    module_name = module_path.name
    env = {
        "MODULE_PATH": str(module_path.resolve()),
        "MODULE_NAME": module_name,
    }

    try:
        # Start only the database service to avoid a second Odoo process
        # conflicting with the test runner on the same database.
        _run_compose(compose_file, ["up", "-d", "--wait", "db"], env, timeout=120)

        # Run tests in a fresh container (no entrypoint server conflict).
        # --test-tags filters to only this module's tests, avoiding the
        # 900+ base module tests that would otherwise run.
        result = _run_compose(
            compose_file,
            [
                "run",
                "--rm",
                "-T",
                "odoo",
                "odoo",
                "-i",
                module_name,
                "-d",
                "test_db",
                "--test-enable",
                f"--test-tags={module_name}",
                "--stop-after-init",
                "--no-http",
                "--log-level=test",
            ],
            env,
            timeout=timeout,
        )

        combined_output = result.stdout + result.stderr
        return parse_test_log(combined_output)
    except subprocess.TimeoutExpired:
        logger.warning("Docker test run timed out after %ds", timeout)
        return ()
    except Exception:
        logger.warning("Docker test run failed", exc_info=True)
        return ()
    finally:
        _teardown(compose_file, env)
