"""Static validation for Blue-Green deployment files."""

from __future__ import annotations

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]


def test_compose_defines_blue_green_and_proxy() -> None:
    compose_path = ROOT / "deploy" / "compose.blue-green.yml"
    compose = yaml.safe_load(compose_path.read_text(encoding="utf-8"))

    assert set(compose["services"]) == {"blue", "green", "proxy"}
    assert (
        compose["services"]["proxy"]["depends_on"]["blue"]["condition"]
        == "service_healthy"
    )
    assert (
        compose["services"]["proxy"]["depends_on"]["green"]["condition"]
        == "service_healthy"
    )


def test_dockerfile_uses_streamlit_health_endpoint() -> None:
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")

    assert "1.1_interface/streamlit_app.py" in dockerfile
    assert "/_stcore/health" in dockerfile
    assert "--server.address=0.0.0.0" in dockerfile


def test_nginx_templates_target_correct_slots() -> None:
    blue = (
        ROOT / "deploy" / "nginx" / "blue.conf.template"
    ).read_text(encoding="utf-8")
    green = (
        ROOT / "deploy" / "nginx" / "green.conf.template"
    ).read_text(encoding="utf-8")

    assert "server blue:8501;" in blue
    assert r'return 200 "blue\n";' in blue
    assert "server green:8501;" in green
    assert r'return 200 "green\n";' in green


def test_private_files_are_excluded_from_build_context() -> None:
    dockerignore = (ROOT / ".dockerignore").read_text(encoding="utf-8")

    assert ".env" in dockerignore
    assert ".streamlit/secrets.toml" in dockerignore
    assert "service-account" in dockerignore


def test_blue_green_workflow_runs_verification_script() -> None:
    workflow = (
        ROOT / ".github" / "workflows" / "blue-green.yml"
    ).read_text(encoding="utf-8")

    assert "ubuntu-latest" in workflow
    assert "bash deploy/verify-blue-green.sh" in workflow
