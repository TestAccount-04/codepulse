"""Tests for CodePulse CLI commands."""

from pathlib import Path
from typer.testing import CliRunner
from codepulse.cli.main import app

runner = CliRunner()


def test_cli_lifecycle(tmp_path: Path):
    # 1. Test init
    init_res = runner.invoke(app, ["init", str(tmp_path)])
    assert init_res.exit_code == 0
    assert "Initialized CodePulse" in init_res.output
    assert (tmp_path / ".codepulse" / "codepulse.db").exists()

    # 2. Create sample files
    (tmp_path / "hello.py").write_text("def say_hello():\n    return 'world'\n", encoding="utf-8")

    # 3. Test scan
    scan_res = runner.invoke(app, ["scan", str(tmp_path)])
    assert scan_res.exit_code == 0
    assert "Scanned Files" in scan_res.output
    assert "say_hello" in scan_res.output or "CodePulse Scan Summary" in scan_res.output

    # 4. Test status
    status_res = runner.invoke(app, ["status", str(tmp_path)])
    assert status_res.exit_code == 0
    assert "Active Files" in status_res.output

    # 5. Test graph
    graph_res = runner.invoke(app, ["graph", str(tmp_path)])
    assert graph_res.exit_code == 0
    assert "say_hello" in graph_res.output
