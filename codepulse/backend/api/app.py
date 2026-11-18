"""FastAPI local REST and WebSocket API server for CodePulse."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from codepulse.backend.storage.sqlite_store import SQLiteStore
from codepulse.backend.websocket.manager import ws_manager
from codepulse.core.change_detector.coordinator import ChangeCoordinator
from codepulse.core.models import ChangeStatus, SymbolDiff, SymbolType
from codepulse.core.repository_scanner.scanner import RepositoryScanner
from codepulse.core.session_manager.manager import SessionManager
from codepulse.core.symbol_graph.graph import SymbolGraphManager
from codepulse.integrations.registry import default_registry


class CreateSessionRequest(BaseModel):
    agent_name: str
    task_description: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class UpdateSessionRequest(BaseModel):
    task_description: str


def create_app(
    repo_root: Optional[Path] = None,
    db_path: Optional[Path] = None,
) -> FastAPI:
    root_path = Path(repo_root or ".").resolve()
    actual_db = Path(db_path or (root_path / ".codepulse" / "codepulse.db")).resolve()

    store = SQLiteStore(actual_db)
    coordinator = ChangeCoordinator(root_path, store, repo_id="default")
    graph_mgr = SymbolGraphManager(store, repo_id="default")
    session_mgr = SessionManager(store, repo_id="default")

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # Capture baseline on start
        coordinator.capture_baseline()

        # Wire live watcher to WebSocket broadcasting
        loop = asyncio.get_running_loop()

        def on_diff(diffs: List[SymbolDiff]) -> None:
            msg = {
                "type": "symbols_changed",
                "diffs": [d.model_dump() for d in diffs],
                "timestamp": loop.time(),
            }
            asyncio.run_coroutine_threadsafe(ws_manager.broadcast(msg), loop)

        coordinator.start_watching(on_change_callback=on_diff)
        yield
        coordinator.stop_watching()

    app = FastAPI(
        title="CodePulse API",
        version="0.1.0",
        description="Local-first code change intelligence API",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # State handles
    app.state.store = store
    app.state.coordinator = coordinator
    app.state.graph_mgr = graph_mgr
    app.state.root_path = root_path

    @app.get("/api/status")
    def get_status() -> Dict[str, Any]:
        metrics = store.get_metrics("default")
        git_info = coordinator.git_tracker.get_uncommitted_changes()
        return {
            "repository": str(root_path),
            "database": str(actual_db),
            "is_git_repo": coordinator.git_tracker.is_git_repo,
            "head_commit": coordinator.git_tracker.get_head_commit(),
            "branch": coordinator.git_tracker.get_current_branch(),
            "metrics": metrics.model_dump(),
            "uncommitted_files": git_info,
        }

    @app.post("/api/scan")
    def trigger_scan(force: bool = Query(False)) -> Dict[str, Any]:
        scanner = RepositoryScanner(store, repo_id="default")
        result = scanner.scan_repository(root_path, force=force)
        return {"status": "success", "result": result}

    @app.get("/api/files")
    def list_files() -> List[Dict[str, Any]]:
        files = store.list_files("default", include_deleted=False)
        result = []
        for f in files:
            symbols = store.get_symbols_by_file("default", f.path)
            result.append({
                "path": f.path,
                "language": f.language,
                "size_bytes": f.size_bytes,
                "sha256": f.sha256,
                "symbol_count": len(symbols),
            })
        return result

    @app.get("/api/symbols")
    def list_symbols(
        file_path: Optional[str] = Query(None),
        symbol_type: Optional[SymbolType] = Query(None),
        status: Optional[ChangeStatus] = Query(None),
    ) -> List[Dict[str, Any]]:
        symbols = store.list_symbols("default", symbol_type=symbol_type, file_path=file_path)
        if status:
            symbols = [s for s in symbols if s.change_status == status]
        return [s.model_dump() for s in symbols]

    @app.get("/api/symbols/{symbol_id:path}/blast-radius")
    def get_blast_radius(symbol_id: str, depth: int = Query(3)) -> Dict[str, Any]:
        return graph_mgr.get_blast_radius(symbol_id, max_depth=depth)

    @app.get("/api/symbols/{symbol_id:path}")
    def get_symbol(symbol_id: str) -> Dict[str, Any]:
        sym = store.get_symbol_by_id("default", symbol_id)
        if not sym:
            raise HTTPException(status_code=404, detail="Symbol not found")
        return sym.model_dump()

    @app.get("/api/graph/tree")
    def get_graph_tree() -> Dict[str, Any]:
        return graph_mgr.get_hierarchical_tree()

    @app.get("/api/graph/flow")
    def get_graph_flow() -> Dict[str, Any]:
        """Generates visual node and edge layout for React Flow interactive canvas."""
        symbols = store.list_symbols("default")
        relationships = store.get_relationships("default")

        nodes: List[Dict[str, Any]] = []
        edges: List[Dict[str, Any]] = []

        # Group symbols by file for organized layout
        files_map: Dict[str, List[Any]] = {}
        for s in symbols:
            files_map.setdefault(s.file_path, []).append(s)

        x_offset = 0
        y_offset = 0
        col_width = 380

        for f_idx, (fpath, file_symbols) in enumerate(files_map.items()):
            col_x = (f_idx % 4) * col_width
            row_y = (f_idx // 4) * 500
            file_node_id = f"{fpath}::file::{fpath}"

            # File container node
            nodes.append({
                "id": file_node_id,
                "type": "fileNode",
                "position": {"x": col_x, "y": row_y},
                "data": {
                    "label": fpath,
                    "name": fpath,
                    "type": "file",
                    "file_path": fpath,
                    "symbol_count": len(file_symbols),
                },
            })

            # Position children vertically relative to file
            for sym_idx, sym in enumerate(file_symbols):
                if sym.symbol_type == SymbolType.FILE:
                    continue

                node_id = sym.id
                sym_y = row_y + 80 + (sym_idx * 75)

                nodes.append({
                    "id": node_id,
                    "type": "symbolNode",
                    "position": {"x": col_x + 20, "y": sym_y},
                    "data": {
                        "label": sym.name,
                        "name": sym.name,
                        "type": sym.symbol_type.value,
                        "signature": sym.signature,
                        "status": sym.change_status.value,
                        "file_path": sym.file_path,
                        "start_line": sym.start_line,
                        "end_line": sym.end_line,
                        "docstring": sym.docstring,
                    },
                })

        # Edges
        for rel in relationships:
            # Animate edges if source or target is modified/impacted
            is_active = False
            edges.append({
                "id": f"e_{rel.source_id}_{rel.target_id}_{rel.relationship_type.value}",
                "source": rel.source_id,
                "target": rel.target_id,
                "label": rel.relationship_type.value,
                "animated": is_active,
                "data": {"type": rel.relationship_type.value},
            })

        return {"nodes": nodes, "edges": edges}

    @app.get("/api/changes")
    def get_changes() -> List[Dict[str, Any]]:
        changed = store.list_changed_symbols("default")
        return [s.model_dump() for s in changed]

    @app.get("/api/events")
    def get_events(limit: int = Query(50)) -> List[Dict[str, Any]]:
        events = store.list_change_events("default", limit=limit)
        return [e.model_dump() for e in events]

    @app.get("/api/diff/{file_path:path}")
    def get_diff(file_path: str) -> Dict[str, Any]:
        diff_text = coordinator.git_tracker.get_file_diff(file_path)
        return {"file_path": file_path, "diff": diff_text}

    # Session Management
    @app.get("/api/sessions")
    def list_sessions(limit: int = Query(50)) -> List[Dict[str, Any]]:
        sessions = session_mgr.list_sessions(limit=limit)
        return [s.model_dump() for s in sessions]

    @app.post("/api/sessions")
    def create_session(req: CreateSessionRequest) -> Dict[str, Any]:
        session = session_mgr.start_session(
            agent_name=req.agent_name,
            task_description=req.task_description,
            metadata=req.metadata,
        )
        return session.model_dump()

    @app.get("/api/sessions/{session_id}")
    def get_session_details(session_id: str) -> Dict[str, Any]:
        summary = session_mgr.get_session_summary(session_id)
        if not summary:
            raise HTTPException(status_code=404, detail="Session not found")
        return summary

    @app.patch("/api/sessions/{session_id}")
    def update_session_task(session_id: str, req: UpdateSessionRequest) -> Dict[str, Any]:
        session_mgr.update_task_description(session_id, req.task_description)
        return {"status": "updated", "session_id": session_id}

    @app.post("/api/sessions/{session_id}/end")
    def end_session(session_id: str, status: str = Query("completed")) -> Dict[str, Any]:
        session_mgr.end_session(session_id, status=status)
        return {"status": "ended", "session_id": session_id}

    # Agent Adapters
    @app.get("/api/agents")
    def list_agents() -> List[Dict[str, Any]]:
        return default_registry.get_status(root_path)

    @app.post("/api/agents/{agent_name}/install")
    def install_agent_hook(agent_name: str) -> Dict[str, Any]:
        adapter = default_registry.get_adapter(agent_name)
        if not adapter:
            raise HTTPException(status_code=404, detail=f"Adapter {agent_name} not found")
        success = adapter.install_hook(root_path)
        return {"agent": agent_name, "installed": success}

    @app.post("/api/agents/{agent_name}/uninstall")
    def uninstall_agent_hook(agent_name: str) -> Dict[str, Any]:
        adapter = default_registry.get_adapter(agent_name)
        if not adapter:
            raise HTTPException(status_code=404, detail=f"Adapter {agent_name} not found")
        success = adapter.uninstall_hook(root_path)
        return {"agent": agent_name, "uninstalled": success}

    @app.websocket("/ws/events")
    async def websocket_events(websocket: WebSocket) -> None:
        await ws_manager.connect(websocket)
        try:
            while True:
                # Keep alive and receive any client ping
                data = await websocket.receive_text()
                if data == "ping":
                    await websocket.send_text('{"type": "pong"}')
        except WebSocketDisconnect:
            ws_manager.disconnect(websocket)

    # Static files for dashboard frontend if compiled
    dist_dir = root_path / "dashboard" / "dist"
    if dist_dir.is_dir():
        app.mount("/", StaticFiles(directory=str(dist_dir), html=True), name="dashboard")

    return app
