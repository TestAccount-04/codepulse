# CodePulse

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688.svg)](https://fastapi.tiangolo.com)
[![React Flow](https://img.shields.io/badge/React%20Flow-12.0+-ff0072.svg)](https://reactflow.dev/)
[![Tests](https://img.shields.io/badge/tests-40%20passed-brightgreen.svg)]()

**CodePulse** is an open-source, local-first code change intelligence and visualization platform. It makes AI coding-agent activity visible, understandable, and reviewable in real time.

---

## 🌟 Key Capabilities

1. **Repository Intelligence (Tree-sitter AST)**:
   - Deep structural parsing for Python, JavaScript, TypeScript, and Java.
   - Extracts classes, functions, methods, parameters, signatures, docstrings, imports, inheritance, and invocations.
2. **Real-Time Change Detection**:
   - Git baseline tracking combined with debounced filesystem monitoring.
   - Isolates symbol-level modifications from file-level diffs (detects added, modified, deleted, and renamed symbols).
3. **Interactive React Flow Dashboard**:
   - Modern dark-mode visual graph built with React Flow, Tailwind CSS, and Lucide icons.
   - Displays real-time file-to-symbol relationships, status colors, and animated modification edges.
4. **Agent Integration & Session Intelligence**:
   - Out-of-the-box adapters and hook management for **Claude Code**, **Cursor**, **Codex CLI**, **Antigravity**, and **Generic Git**.
   - Correlates file edits and commits with task prompt goals and session lifetimes.
5. **Blast-Radius Impact Analysis & Test Discovery**:
   - Computes multi-hop upstream callers and downstream dependencies via NetworkX.
   - Automatically surfaces impacted test files (`test_*.py`, `*.spec.ts`, `*Test.java`) and calculates risk scores (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`).
6. **Evidence-Grounded Change Explanations**:
   - 3-part structured explanations: **What changed**, **Why**, and **Impact**.
   - Fully functional without LLMs via deterministic AST analysis. Avoids fabricating reasons when evidence is missing.
7. **Comprehensive Review Experience**:
   - Dedicated review panel in both the Web Dashboard and VS Code.
   - Supports Mark Reviewed, Accept, and Reject.
   - **Spec §12 Safety Invariant**: Review acceptance never automatically alters repository files.
   - **Safe Git Rollback**: Surgically restores rejected symbols to Git HEAD while **preserving all unrelated user edits**.
8. **Lightweight VS Code Extension**:
   - Reuses the local CodePulse backend.
   - Activity Bar views for changed symbols, active session goals, and one-click jump-to-symbol in the editor.

---

## 🚀 Quick Start

### 1. Installation

```bash
# Clone the repository
git clone https://github.com/your-org/codepulse.git
cd codepulse

# Create virtual environment and install in editable mode
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

### 2. Initialize and Scan Repository

```bash
# Initialize CodePulse in your project
codepulse init

# Scan codebase to index symbols into local SQLite store
codepulse scan

# Check repository indexing metrics
codepulse status
```

### 3. Launch Local Server & Web Dashboard

```bash
# Start local API, WebSocket hub, and React dashboard on http://127.0.0.1:8000
codepulse start
```

---

## 💻 CLI Command Reference

| Command | Description |
| :--- | :--- |
| `codepulse init [path]` | Initialize CodePulse in a target repository (`.codepulse/`). |
| `codepulse scan [path] [--force]` | Scan source code and populate the local SQLite symbol graph. |
| `codepulse status [path]` | Display repository file counts, indexed symbols, and detected languages. |
| `codepulse changes [path]` | List all changed and impacted symbols currently in the workspace. |
| `codepulse watch [path]` | Start real-time filesystem watcher to log live AST diffs. |
| `codepulse graph [path] [--symbol S]` | Inspect hierarchical symbol tree or blast radius for a symbol. |
| `codepulse impact <symbol> [path]` | Run deep blast-radius analysis, caller discovery, and test discovery. |
| `codepulse explain <symbol> [path]` | Generate grounded What / Why / Impact change explanation. |
| `codepulse sessions [path]` | List historical and active AI coding agent sessions. |
| `codepulse agents list [path]` | Inspect status of Claude Code, Cursor, Codex, and Antigravity hooks. |
| `codepulse agents install <agent>` | Install integration hook for an agent in the repository. |
| `codepulse review [path]` | Open change review panel, inspect diffs, accept, or safely rollback. |
| `codepulse start [path] [--port P]` | Start local FastAPI server and interactive web dashboard. |

---

## 🧩 VS Code Extension

The CodePulse VS Code extension lives in `vscode-extension/`:

1. **Changed Symbols & Review View**: Displays files and changed symbols in the Activity Bar.
2. **Review Actions**: One-click Accept, Reject & Safe Rollback, and Add Review Note.
3. **Code Navigation**: Clicking any changed symbol jumps straight to its line in the editor.
4. **Active Session View**: Shows active agent name, session status, and current task goal.
5. **Output Channel**: Full Impact and Grounded Explanation reporting.

To build the extension:
```bash
cd vscode-extension
npm install
npm run build
```

---

## 🔒 Privacy & Security

CodePulse is strictly **local-first**:
- **Zero Cloud Transmission**: No source code, diffs, or symbol metadata are sent to external servers.
- **Localhost Default**: Binds to `127.0.0.1`.
- **Sensitive Exclusions**: Automatically excludes `.env`, `*.pem`, `*.key`, `id_rsa`, credentials, databases, and `.gitignore` patterns.
- **Path Traversal Protection**: Enforces directory boundary containment on all file endpoints.
- See [docs/SECURITY.md](docs/SECURITY.md) for details.

---

## ⚡ Performance & Scalability

- **WAL Mode SQLite**: Fast concurrent reads and batch transaction writes via `executemany`.
- **Incremental Skipping**: Scans only modified files using SHA-256 and `mtime` cache, achieving > 2,000 files/sec on incremental scans.
- **In-Memory Graph Traversal**: Sub-millisecond blast-radius calculations via NetworkX.
- See [docs/PERFORMANCE.md](docs/PERFORMANCE.md) for benchmarks.

---

## 🧪 Testing

CodePulse includes a comprehensive automated test suite with 40 unit, integration, performance, and end-to-end tests:

```bash
# Run full test suite
pytest -v
```

---

## 📚 Documentation Links

- [Master Product Specification](spec.md)
- [Reference Analysis & Reuse Report](docs/REFERENCE_ANALYSIS.md)
- [Implementation Decisions Log](docs/implementation_decisions.md)
- [System Architecture](docs/architecture.md)
- [Security & Privacy](docs/SECURITY.md)
- [Performance Benchmarks](docs/PERFORMANCE.md)
- [Third-Party Notices](THIRD_PARTY_NOTICES.md)

---

## 📄 License

CodePulse is licensed under the [MIT License](LICENSE).
