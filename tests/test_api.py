"""Tests for CodePulse FastAPI endpoints and WebSocket event stream."""

from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from codepulse.backend.api.app import create_app
from codepulse.backend.storage.sqlite_store import SQLiteStore


@pytest.fixture
def api_client(tmp_path: Path):
    db_file = tmp_path / ".codepulse" / "codepulse.db"
    store = SQLiteStore(db_file)
    store.register_repository("default", str(tmp_path))

    # Add sample source file
    src_dir = tmp_path / "src"
    src_dir.mkdir(parents=True)
    (src_dir / "service.py").write_text(
        "class AuthService:\n    def login(self, token: str):\n        return True\n",
        encoding="utf-8",
    )

    app = create_app(repo_root=tmp_path, db_path=db_file)
    with TestClient(app) as client:
        yield client


def test_api_status_endpoint(api_client: TestClient):
    response = api_client.get("/api/status")
    assert response.status_code == 200
    data = response.json()
    assert "metrics" in data
    assert "repository" in data


def test_api_scan_and_files_endpoints(api_client: TestClient):
    scan_resp = api_client.post("/api/scan?force=true")
    assert scan_resp.status_code == 200
    scan_data = scan_resp.json()
    assert scan_data["status"] == "success"

    files_resp = api_client.get("/api/files")
    assert files_resp.status_code == 200
    files_data = files_resp.json()
    assert len(files_data) >= 1
    assert any("service.py" in f["path"] for f in files_data)


def test_api_symbols_and_blast_radius(api_client: TestClient):
    api_client.post("/api/scan")

    symbols_resp = api_client.get("/api/symbols")
    assert symbols_resp.status_code == 200
    symbols = symbols_resp.json()
    assert len(symbols) >= 1

    login_sym = next(s for s in symbols if s["name"] == "login")
    assert login_sym is not None

    blast_resp = api_client.get(f"/api/symbols/{login_sym['id']}/blast-radius")
    assert blast_resp.status_code == 200
    blast_data = blast_resp.json()
    assert "upstream_callers" in blast_data


def test_api_graph_tree_and_flow(api_client: TestClient):
    api_client.post("/api/scan")

    tree_resp = api_client.get("/api/graph/tree")
    assert tree_resp.status_code == 200
    assert "children" in tree_resp.json()

    flow_resp = api_client.get("/api/graph/flow")
    assert flow_resp.status_code == 200
    flow_data = flow_resp.json()
    assert "nodes" in flow_data
    assert "edges" in flow_data
    assert len(flow_data["nodes"]) >= 1


def test_api_websocket_connection(api_client: TestClient):
    with api_client.websocket_connect("/ws/events") as websocket:
        websocket.send_text("ping")
        data = websocket.receive_text()
        assert "pong" in data


def test_api_session_and_agents_endpoints(api_client: TestClient):
    # Test create session
    create_resp = api_client.post(
        "/api/sessions",
        json={"agent_name": "claude-code", "task_description": "API test session"},
    )
    assert create_resp.status_code == 200
    session_data = create_resp.json()
    assert session_data["agent_name"] == "claude-code"
    session_id = session_data["id"]

    # Test list sessions
    list_resp = api_client.get("/api/sessions")
    assert list_resp.status_code == 200
    sessions = list_resp.json()
    assert any(s["id"] == session_id for s in sessions)

    # Test session details
    detail_resp = api_client.get(f"/api/sessions/{session_id}")
    assert detail_resp.status_code == 200
    assert detail_resp.json()["session_id"] == session_id

    # Test agents list
    agents_resp = api_client.get("/api/agents")
    assert agents_resp.status_code == 200
    agents = agents_resp.json()
    assert len(agents) >= 5

    # Test agent hook install
    install_resp = api_client.post("/api/agents/claude-code/install")
    assert install_resp.status_code == 200
    assert install_resp.json()["installed"] is True
