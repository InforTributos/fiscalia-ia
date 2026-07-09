"""Tests E2E para Docker: build, run, healthcheck.

Requiere Docker Desktop instalado y el socket accesible.
Se salta automaticamente si docker no esta disponible.
"""

import logging
import subprocess

import pytest

logger = logging.getLogger(__name__)
pytestmark = [pytest.mark.e2e, pytest.mark.docker]


def _check_docker():
    try:
        subprocess.run(["docker", "info"], capture_output=True, text=True, timeout=10)
        return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


@pytest.mark.skipif(not _check_docker(), reason="Docker no disponible")
def test_docker_build():
    """Dockerfile compila sin errores (multi-stage, python:3.11-slim)."""
    result = subprocess.run(
        ["docker", "build", "-t", "fiscalia-ia-test", "-f", "Dockerfile", "."],
        capture_output=True, text=True, timeout=180,
    )
    assert result.returncode == 0, f"Build fallo:\n{result.stderr}"


@pytest.mark.skipif(not _check_docker(), reason="Docker no disponible")
def test_docker_run_exits_with_db_error():
    """Container arranca pero sale con error de BD (esperado sin PostgreSQL)."""
    subprocess.run(
        ["docker", "rm", "-f", "fiscalia-test-ctn"],
        capture_output=True, timeout=10,
    )

    result = subprocess.run(
        ["docker", "run", "--name", "fiscalia-test-ctn",
         "-e", "SECRET_KEY=test",
         "-e", "POSTGRES_HOST=host.docker.internal",
         "-e", "POSTGRES_USER=test",
         "-e", "POSTGRES_PASSWORD=test",
         "-e", "POSTGRES_DB=test",
         "-e", "LOG_LEVEL=WARNING",
         "fiscalia-ia-test"],
        capture_output=True, text=True, timeout=15,
    )

    subprocess.run(["docker", "rm", "-f", "fiscalia-test-ctn"],
                   capture_output=True, timeout=10)

    assert result.returncode != 0, "El container deberia fallar sin PostgreSQL"
    assert "password authentication failed" in result.stderr or \
           "could not connect to server" in result.stderr or \
           "connection refused" in result.stderr, \
           f"Error inesperado (no es de BD):\n{result.stderr}"
