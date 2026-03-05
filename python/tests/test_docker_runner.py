"""Tests for Docker runner with mocked subprocess."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, call, patch

from odoo_gen_utils.validation.docker_runner import (
    check_docker_available,
    docker_install_module,
    docker_run_tests,
    get_compose_file,
)
from odoo_gen_utils.validation.types import InstallResult, TestResult


# --- check_docker_available tests ---


class TestCheckDockerAvailablePresent:
    """When docker CLI is present, returns True."""

    @patch("odoo_gen_utils.validation.docker_runner.subprocess.run")
    @patch("odoo_gen_utils.validation.docker_runner.shutil.which")
    def test_docker_available(self, mock_which: MagicMock, mock_run: MagicMock) -> None:
        mock_which.return_value = "/usr/bin/docker"
        mock_run.return_value = MagicMock(returncode=0)
        assert check_docker_available() is True
        mock_which.assert_called_once_with("docker")


class TestCheckDockerAvailableMissing:
    """When docker CLI is missing, returns False."""

    @patch("odoo_gen_utils.validation.docker_runner.shutil.which")
    def test_docker_not_available(self, mock_which: MagicMock) -> None:
        mock_which.return_value = None
        assert check_docker_available() is False


# --- get_compose_file tests ---


class TestGetComposeFilePath:
    """get_compose_file returns path to docker/docker-compose.yml."""

    def test_compose_file_path(self) -> None:
        result = get_compose_file()
        assert isinstance(result, Path)
        assert result.name == "docker-compose.yml"
        assert "docker" in str(result)


# --- docker_install_module tests ---


class TestDockerInstallModuleSuccess:
    """Successful install returns InstallResult(success=True)."""

    @patch("odoo_gen_utils.validation.docker_runner._teardown")
    @patch("odoo_gen_utils.validation.docker_runner._run_compose")
    @patch("odoo_gen_utils.validation.docker_runner.check_docker_available")
    def test_docker_install_success(
        self,
        mock_available: MagicMock,
        mock_run: MagicMock,
        mock_teardown: MagicMock,
    ) -> None:
        mock_available.return_value = True
        # First call: start db only (not full stack)
        # Second call: run --rm (not exec) for install
        success_log = (
            "2026-03-02 10:00:00,000 1 INFO test_db "
            "odoo.modules.loading: 1 modules loaded, 0 modules updated, 0 tests\n"
            "2026-03-02 10:00:01,000 1 INFO test_db "
            "odoo.modules.loading: Modules loaded.\n"
        )
        mock_run.side_effect = [
            MagicMock(stdout="", stderr="", returncode=0),  # up -d --wait db
            MagicMock(stdout=success_log, stderr="", returncode=0),  # run --rm
        ]

        module_path = Path("/tmp/test_mod")
        result = docker_install_module(module_path, compose_file=Path("/tmp/compose.yml"))

        assert isinstance(result, InstallResult)
        assert result.success is True
        assert result.error_message == ""


class TestDockerInstallUsesRunNotExec:
    """docker_install_module uses 'run --rm' pattern, not 'exec'."""

    @patch("odoo_gen_utils.validation.docker_runner._teardown")
    @patch("odoo_gen_utils.validation.docker_runner._run_compose")
    @patch("odoo_gen_utils.validation.docker_runner.check_docker_available")
    def test_first_call_starts_db_only(
        self,
        mock_available: MagicMock,
        mock_run: MagicMock,
        mock_teardown: MagicMock,
    ) -> None:
        mock_available.return_value = True
        success_log = (
            "2026-03-02 10:00:00,000 1 INFO test_db "
            "odoo.modules.loading: Modules loaded.\n"
        )
        mock_run.side_effect = [
            MagicMock(stdout="", stderr="", returncode=0),
            MagicMock(stdout=success_log, stderr="", returncode=0),
        ]

        docker_install_module(Path("/tmp/test_mod"), compose_file=Path("/tmp/compose.yml"))

        # First call must start only db service
        first_call_args = mock_run.call_args_list[0]
        assert "db" in first_call_args[0][1], (
            f"First _run_compose call should include 'db' for db-only startup, "
            f"got args: {first_call_args[0][1]}"
        )

    @patch("odoo_gen_utils.validation.docker_runner._teardown")
    @patch("odoo_gen_utils.validation.docker_runner._run_compose")
    @patch("odoo_gen_utils.validation.docker_runner.check_docker_available")
    def test_second_call_uses_run_rm_not_exec(
        self,
        mock_available: MagicMock,
        mock_run: MagicMock,
        mock_teardown: MagicMock,
    ) -> None:
        mock_available.return_value = True
        success_log = (
            "2026-03-02 10:00:00,000 1 INFO test_db "
            "odoo.modules.loading: Modules loaded.\n"
        )
        mock_run.side_effect = [
            MagicMock(stdout="", stderr="", returncode=0),
            MagicMock(stdout=success_log, stderr="", returncode=0),
        ]

        docker_install_module(Path("/tmp/test_mod"), compose_file=Path("/tmp/compose.yml"))

        # Second call must use 'run --rm', not 'exec'
        second_call_args = mock_run.call_args_list[1]
        install_args = second_call_args[0][1]
        assert "run" in install_args, (
            f"Second _run_compose call should use 'run', got args: {install_args}"
        )
        assert "--rm" in install_args, (
            f"Second _run_compose call should include '--rm', got args: {install_args}"
        )
        assert "exec" not in install_args, (
            f"Second _run_compose call should NOT use 'exec', got args: {install_args}"
        )


class TestDockerInstallModuleFailure:
    """Failed install returns InstallResult(success=False)."""

    @patch("odoo_gen_utils.validation.docker_runner._teardown")
    @patch("odoo_gen_utils.validation.docker_runner._run_compose")
    @patch("odoo_gen_utils.validation.docker_runner.check_docker_available")
    def test_docker_install_failure(
        self,
        mock_available: MagicMock,
        mock_run: MagicMock,
        mock_teardown: MagicMock,
    ) -> None:
        mock_available.return_value = True
        error_log = (
            "2026-03-02 10:00:00,000 1 ERROR test_db "
            "odoo.modules.registry: Failed to load module test_mod\n"
        )
        mock_run.side_effect = [
            MagicMock(stdout="", stderr="", returncode=0),  # up
            MagicMock(stdout=error_log, stderr="", returncode=1),  # exec
        ]

        module_path = Path("/tmp/test_mod")
        result = docker_install_module(module_path, compose_file=Path("/tmp/compose.yml"))

        assert isinstance(result, InstallResult)
        assert result.success is False
        assert result.error_message != ""


class TestDockerInstallTeardown:
    """docker compose down -v is ALWAYS called, even on failure."""

    @patch("odoo_gen_utils.validation.docker_runner._teardown")
    @patch("odoo_gen_utils.validation.docker_runner._run_compose")
    @patch("odoo_gen_utils.validation.docker_runner.check_docker_available")
    def test_teardown_always_called(
        self,
        mock_available: MagicMock,
        mock_run: MagicMock,
        mock_teardown: MagicMock,
    ) -> None:
        mock_available.return_value = True
        mock_run.side_effect = Exception("Subprocess failed")

        module_path = Path("/tmp/test_mod")
        result = docker_install_module(module_path, compose_file=Path("/tmp/compose.yml"))

        # Teardown must be called even though run raised
        mock_teardown.assert_called_once()
        assert result.success is False


# --- docker_run_tests tests ---


class TestDockerRunTestsSuccess:
    """Successful test run returns tuple of TestResult with passed=True."""

    @patch("odoo_gen_utils.validation.docker_runner._teardown")
    @patch("odoo_gen_utils.validation.docker_runner._run_compose")
    @patch("odoo_gen_utils.validation.docker_runner.check_docker_available")
    def test_docker_run_tests_success(
        self,
        mock_available: MagicMock,
        mock_run: MagicMock,
        mock_teardown: MagicMock,
    ) -> None:
        mock_available.return_value = True
        test_log = (
            "2026-03-02 10:00:00,000 1 INFO test_db "
            "odoo.addons.test_mod.tests.test_model: test_create ... ok\n"
            "2026-03-02 10:00:00,050 1 INFO test_db "
            "odoo.addons.test_mod.tests.test_model: test_read ... ok\n"
            "2026-03-02 10:00:00,100 1 INFO test_db "
            "odoo.addons.test_mod.tests.test_model: Ran 2 tests in 0.1s\n"
        )
        mock_run.side_effect = [
            MagicMock(stdout="", stderr="", returncode=0),  # up
            MagicMock(stdout=test_log, stderr="", returncode=0),  # exec
        ]

        module_path = Path("/tmp/test_mod")
        results = docker_run_tests(module_path, compose_file=Path("/tmp/compose.yml"))

        assert len(results) == 2
        assert all(isinstance(r, TestResult) for r in results)
        assert all(r.passed is True for r in results)


class TestDockerRunTestsFailure:
    """Test run with failures returns TestResult with passed=False."""

    @patch("odoo_gen_utils.validation.docker_runner._teardown")
    @patch("odoo_gen_utils.validation.docker_runner._run_compose")
    @patch("odoo_gen_utils.validation.docker_runner.check_docker_available")
    def test_docker_run_tests_failure(
        self,
        mock_available: MagicMock,
        mock_run: MagicMock,
        mock_teardown: MagicMock,
    ) -> None:
        mock_available.return_value = True
        test_log = (
            "2026-03-02 10:00:00,000 1 INFO test_db "
            "odoo.addons.test_mod.tests.test_model: test_create ... ok\n"
            "2026-03-02 10:00:00,100 1 FAIL test_db "
            "odoo.addons.test_mod.tests.test_model: test_invalid\n"
            "AssertionError: expected True got False\n"
            "2026-03-02 10:00:00,200 1 INFO test_db "
            "odoo.addons.test_mod.tests.test_model: Ran 2 tests in 0.2s\n"
        )
        mock_run.side_effect = [
            MagicMock(stdout="", stderr="", returncode=0),  # up
            MagicMock(stdout=test_log, stderr="", returncode=1),  # exec
        ]

        module_path = Path("/tmp/test_mod")
        results = docker_run_tests(module_path, compose_file=Path("/tmp/compose.yml"))

        passed = [r for r in results if r.passed]
        failed = [r for r in results if not r.passed]
        assert len(passed) == 1
        assert len(failed) == 1


class TestDockerRunTestsTeardown:
    """docker compose down -v is ALWAYS called after test run."""

    @patch("odoo_gen_utils.validation.docker_runner._teardown")
    @patch("odoo_gen_utils.validation.docker_runner._run_compose")
    @patch("odoo_gen_utils.validation.docker_runner.check_docker_available")
    def test_teardown_always_called(
        self,
        mock_available: MagicMock,
        mock_run: MagicMock,
        mock_teardown: MagicMock,
    ) -> None:
        mock_available.return_value = True
        mock_run.side_effect = Exception("Test exec failed")

        module_path = Path("/tmp/test_mod")
        results = docker_run_tests(module_path, compose_file=Path("/tmp/compose.yml"))

        mock_teardown.assert_called_once()


# --- Docker not available tests ---


class TestDockerNotAvailableInstall:
    """When Docker unavailable, install returns graceful degradation."""

    @patch("odoo_gen_utils.validation.docker_runner.check_docker_available")
    def test_docker_not_available_install(self, mock_available: MagicMock) -> None:
        mock_available.return_value = False

        result = docker_install_module(Path("/tmp/test_mod"))

        assert isinstance(result, InstallResult)
        assert result.success is False
        assert "Docker not available" in result.error_message


class TestDockerNotAvailableTests:
    """When Docker unavailable, run_tests returns empty tuple."""

    @patch("odoo_gen_utils.validation.docker_runner.check_docker_available")
    def test_docker_not_available_tests(self, mock_available: MagicMock) -> None:
        mock_available.return_value = False

        results = docker_run_tests(Path("/tmp/test_mod"))

        assert results == ()


# --- Timeout test ---


class TestDockerTimeout:
    """When subprocess times out, returns failure result."""

    @patch("odoo_gen_utils.validation.docker_runner._teardown")
    @patch("odoo_gen_utils.validation.docker_runner._run_compose")
    @patch("odoo_gen_utils.validation.docker_runner.check_docker_available")
    def test_docker_install_timeout(
        self,
        mock_available: MagicMock,
        mock_run: MagicMock,
        mock_teardown: MagicMock,
    ) -> None:
        mock_available.return_value = True
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="docker", timeout=300)

        module_path = Path("/tmp/test_mod")
        result = docker_install_module(module_path, compose_file=Path("/tmp/compose.yml"))

        assert isinstance(result, InstallResult)
        assert result.success is False
        assert "Timeout" in result.error_message or "timeout" in result.error_message.lower()
        mock_teardown.assert_called_once()
