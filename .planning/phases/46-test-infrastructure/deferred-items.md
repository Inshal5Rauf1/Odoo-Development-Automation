# Deferred Items - Phase 46

## Pre-existing Docker Mount Failures

5 Docker integration tests fail due to invalid mount configuration on the development machine (Docker daemon IS available, but `docker compose run` fails with "invalid mount config"). These are pre-existing failures unrelated to the test infrastructure fixes in 46-01.

Affected tests:
- `test_docker_integration.py::test_docker_install_real_module`
- `test_docker_integration.py::test_docker_run_tests_real_module`
- `test_golden_path.py::test_golden_path_docker_install`
- `test_golden_path.py::test_golden_path_docker_tests`
- `test_integration_multifeature.py::TestKitchenSinkDocker::test_kitchen_sink_docker_install`

Root cause: Docker mount path issue in docker-compose configuration, not a test guard issue. In CI without Docker, these skip correctly via the conftest fixture.
