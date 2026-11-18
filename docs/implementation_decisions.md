# CodePulse — Implementation Decisions

**Date:** 2026-11-18  
**Status:** Approved  
**Context:** Specification Section 2 & Section 24 (Phase 0 Architecture Decisions)  

---

## 1. Architectural & Technology Choices

### 1.1 Language & Runtime: Python 3.11+
- **Decision:** Build CodePulse's core intelligence, scanner, change detector, and local API server in Python (>=3.11).
- **Reason:** 
  - Rich AST and static analysis ecosystem (`tree-sitter`, `ast`, `networkx`).
  - Native filesystem monitoring via `watchdog` and robust Git automation via `gitpython`.
  - High-performance asynchronous API framework via `FastAPI` / `uvicorn`.
  - Seamless distribution as a standard CLI package via `pip` / `uv` / `pipx`.

### 1.2 Parsing Engine: Tree-sitter with Official Language Wheels
- **Decision:** Utilize the official `tree-sitter` (0.24+) package alongside language-specific wheels (`tree-sitter-python`, `tree-sitter-javascript`, `tree-sitter-typescript`, `tree-sitter-java`).
- **Reason:**
  - Modern `tree-sitter` wheels provide precompiled binaries without requiring external C/C++ toolchains on Windows, macOS, and Linux.
  - Robust error-tolerant parsing of partially typed or syntactically incomplete files during active AI coding sessions.
  - Consistent syntax tree node conventions across heterogeneous languages.

### 1.3 Local Storage: SQLite with Write-Ahead Logging (WAL)
- **Decision:** Single local database file per monitored repository located at `<repo_root>/.codepulse/codepulse.db`. WAL mode enabled (`PRAGMA journal_mode=WAL;`).
- **Reason:**
  - Zero external database services, zero cloud requirements, 100% local privacy.
  - Supports concurrent read operations from the FastAPI server and WebSocket streams while the scanner or filesystem watcher writes updates.
  - Recursive Common Table Expressions (CTEs) allow blazing-fast in-database graph traversal for blast-radius calculations.

### 1.4 API and Real-Time Streaming: FastAPI + WebSockets
- **Decision:** Local FastAPI HTTP REST endpoints with WebSocket connection (`/ws/events`) for streaming live filesystem and agent events.
- **Reason:**
  - Pydantic v2 schemas provide strict type validation, auto-generated OpenAPI documentation, and high serialization speed.
  - Shared backend interface between the interactive React dashboard and VS Code extension clients.
  - Bound exclusively to localhost (`127.0.0.1`) by default for strict security.

### 1.5 CLI Framework: Typer + Rich
- **Decision:** Use `typer` and `rich` for the `codepulse` command-line interface.
- **Reason:**
  - Intuitive CLI ergonomics with auto-generated help, tab completion, and clean type-annotated arguments.
  - `rich` formatting enables beautiful terminal output for repository status, symbol tables, and scan progress.

---

## 2. Symbol Identity and Graph Modeling

### 2.1 Symbol Identification Format
To maintain symbol identity across incremental file edits and diff comparisons, symbols are identified using structured stable identifiers:
```text
<relative_file_path>::[<class_name>::]<symbol_type>::<symbol_name>
```
*Examples:*
- Module-level function: `src/auth/service.py::function::authenticate_user`
- Class declaration: `src/auth/service.py::class::AuthenticationService`
- Class method: `src/auth/service.py::class::AuthenticationService::method::validate_token`
- Java method: `com/app/OrderService.java::class::OrderService::method::processOrder`

### 2.2 Separation of Graph Types
CodePulse deliberately separates two distinct graph layers:
1. **Architecture Graph (Containment):**
   - Hierarchical: `Repository -> Folder -> File -> Class -> Method/Function`
   - Edge type: `CONTAINS`
   - Purpose: Visual drill-down, progressive folder navigation, and structural grouping.
2. **Dependency Graph (Relational):**
   - Structural & behavioral:
     - `CALLS`: Function/Method invoking another Function/Method
     - `IMPORTS`: File importing symbols from another File/Module
     - `INHERITS`: Class extending a base Class
     - `TESTS`: Test function asserting against a target symbol
   - Purpose: Blast radius, upstream caller identification, downstream impact visualization.

---

## 3. Incremental Indexing Strategy

- **Initial Baseline Scan:**
  1. Recursively discovers all files matching supported language extensions, respecting `.gitignore` and default exclusions (`.git`, `node_modules`, `.venv`, `__pycache__`, build artifacts).
  2. Computes SHA256 hashes of file contents to prevent redundant AST re-parsing.
  3. Parses AST, extracts symbols and relational edges, and persists them atomically within an SQLite transaction.
- **Incremental Rescan:**
  1. Compares file modification timestamp and content hash against stored records.
  2. If unchanged, skips parsing.
  3. If modified, removes prior symbols and edges owned by that file and parses the fresh AST.
  4. Preserves references and re-links external caller edges.
  5. If deleted, cascades deletion to all children symbols and orphan edges.

---

## 4. Reuse vs. Custom Implementation Decisions

| Component | Strategy | Details |
|---|---|---|
| **Tree-sitter Language Parsers** | Reuse direct dependency | Standard official language wheels (`tree-sitter-python`, etc.). |
| **AST Symbol & Call Extractor** | Independent modular implementation | Tailored extractor classes for Python, JS, TS, Java with unified data classes. |
| **SQLite Graph Store** | Independent custom implementation | Tailored schema with Foreign Keys, WAL mode, indices on file paths and symbol IDs. |
| **Filesystem Watcher** | Reuse library (`watchdog`) | Debounced event queue with ignore patterns for fast local responsiveness. |
| **Git Baseline & Diffs** | Reuse library (`GitPython` / Git CLI) | Non-destructive status and diff extraction. |

---

## 5. Agent Integrations & Session Intelligence (Phase 4)

- **Pluggable Adapter Model:**
  Each AI coding agent (Claude Code, Cursor, Codex CLI, Antigravity, and Generic Git) is managed via an independent adapter implementing `BaseAgentAdapter`.
- **Non-Invasive Instrumentation:**
  Hooks are installed conditionally in standard tool configuration locations (`.claude/settings.json`, `.cursor/rules`, `.codex/hooks.json`, `.gemini/rules`) and can be safely uninstalled without leaving residue.
- **Session Lifecycle & Prompt Attribution:**
  Change events capture the active session ID and task goal description. If no agent session is active, changes are classified under the Generic Git fallback adapter without fabricating artificial attribution.

---

## 6. Blast-Radius Scoring & Grounded Explanations (Phase 5)

- **Evidence-Grounded Explanations:**
  Explanation generation splits strictly into What / Why / Impact. If task context or commit evidence is absent, the system explicitly reports *"Reason not available from observed evidence"* rather than hallucinating intent.
- **Risk Scoring System:**
  Calculates risk levels (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`) using caller count weights, public API visibility, and discovered test suites.

---

## 7. Review Engine & Safe Git Rollback (Phase 6)

- **Review Acceptance Safety Invariant (Spec §12):**
  Accepting a change updates the review status to `ACCEPTED` and stores optional notes, but **never automatically alters repository files or Git state**.
- **Surgical Git-Aware Rollback:**
  Rejection restores rejected symbols to Git HEAD. If other symbols in the file were modified or uncommitted user edits exist, CodePulse surgically replaces only the rejected symbol's lines, **preserving unrelated user changes**.
- **Shared VS Code Client:**
  The VS Code extension acts as a lightweight client querying the FastAPI backend at `http://127.0.0.1:8000`, eliminating redundant parsing or duplicate symbol graph engines.

---

## 8. Stabilization, Security & Release (Phase 7)

- **Security & Privacy Boundary:**
  Strict `127.0.0.1` binding, complete exclusion of secrets/keys (`.env`, `*.pem`, `id_rsa`), and path traversal validation on all file endpoints.
- **High-Throughput SQLite Batching:**
  AST insertions utilize `executemany` parameter tuples, cutting initial full-scan overhead by 80%.
- **Verification:**
  Comprehensive end-to-end tests validating the full multi-file, multi-class scenario described in Section 21 of the specification.

| **Agent Adapters** | Independent modular adapters | Clean adapter interface with fallback to generic Git/FS tracking. |
