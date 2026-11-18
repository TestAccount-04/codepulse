# CodePulse — Reference Repository Analysis

**Date:** 2026-11-18  
**Document status:** Complete (Phase 0 Deliverable)  
**Authors:** CodePulse Engineering Team  

---

## 1. Executive Summary

In accordance with Section 2 of the CodePulse Specification (*Reference-Driven Development Strategy*), this document evaluates open-source projects in the code intelligence, agent tracing, repository graph, and code review spaces. The goal is to accelerate development through selective reuse of proven engineering patterns, algorithms, and dependencies while preserving CodePulse's product independence, modularity, and clean licensing.

---

## 2. Reuse Classification Rules

Every candidate is evaluated against five discrete classifications:

| Decision | Meaning |
|---|---|
| **Reuse dependency** | Directly integrate the package or library via package manager |
| **Reuse module** | Adapt a specific implementation where licensing and architecture permit |
| **Integrate through API** | Consume an existing service, CLI, or MCP interface |
| **Reference only** | Study architectural design, algorithms, or schemas; implement independently |
| **Reject** | Incompatible license, unmaintained, or out of scope |

---

## 3. Primary Reference Evaluations

### 3.1 code-review-graph

- **Repository:** [https://github.com/tirth8205/code-review-graph](https://github.com/tirth8205/code-review-graph)
- **License:** MIT License (Verified: November 2026)
- **Main Technologies:** Python 3.10+, Tree-sitter, SQLite, NetworkX, FastMCP / Model Context Protocol.
- **Relevant Modules / Source Paths:**
  - `code_review_graph/parser/`: Tree-sitter query mappings across languages (Python, JS, TS, Java, etc.).
  - `code_review_graph/graph/`: SQLite graph schema, node/edge creation, incremental graph update logic.
  - `code_review_graph/analyzer/`: Blast-radius and caller-callee dependency traversal algorithms.
  - `code_review_graph/mcp/`: Server implementation exposing tools to Claude Code / Windsurf / Cursor.
- **Capabilities Can Be Reused / Adapted:**
  - Tree-sitter AST queries for symbol extraction (functions, classes, methods, imports, calls).
  - Graph schema modeling for symbol hierarchy (File -> Class -> Method) and relational links (Calls, Imports, Inherits).
  - Incremental graph update patterns: invalidating and re-indexing only modified files instead of rebuilding the full repository graph.
  - Blast-radius calculation concepts using SQLite recursive Common Table Expressions (CTEs) and NetworkX.
- **Dependency & Compatibility Concerns:**
  - Tree-sitter 0.22+ to 0.26+ packaging changes in Python (language libraries moved to individual `tree-sitter-<lang>` wheels). CodePulse standardizes on modern `tree-sitter` wheels.
- **Limitations:**
  - Designed primarily as an MCP backend for reducing LLM token context; lacks a visual web dashboard, interactive React Flow visualization, agent lifecycle hooks, or visual review UI.
- **Final Decision:** **Reference only & Reuse patterns** (Adapt parser patterns & query abstractions into CodePulse's native `core/repository_scanner` and `core/symbol_graph`, maintaining clean independent architecture).
- **Reason:** While `code-review-graph` provides valuable parsing patterns, CodePulse requires a unified SQLite schema supporting real-time agent attribution, Git snapshots, and WebSocket pub/sub that differ from a pure MCP server.

---

### 3.2 Posthook

- **Repository:** [https://github.com/Bilanc/posthook](https://github.com/Bilanc/posthook)
- **License:** MIT License (Verified: November 2026)
- **Main Technologies:** Python / Go / Shell, Git plumbing (`git notes`, hooks, shadow trees), SQLite.
- **Relevant Modules / Source Paths:**
  - `hooks/`: Git pre-commit, post-commit, and agent hook installers for Claude Code, Cursor, Codex CLI.
  - `attribution/`: Line-level AI-vs-human attribution engine using git shadow branches and SQLite session logs.
  - `session/`: Session boundary detection, tool invocation interception, and prompt association.
- **Capabilities Can Be Reused / Adapted:**
  - Non-destructive Git instrumentation concepts using `git notes` or local SQLite session logs to associate changes with agent sessions without polluting commit history.
  - Hook installation scripts and lifecycle interceptors for Claude Code and Cursor.
  - Session-to-commit linking heuristics.
- **Dependency & Compatibility Concerns:**
  - Direct git hook hijacking can conflict with developer pre-commit suites (e.g. `pre-commit` framework, Husky). Must ensure CodePulse hooks chain cleanly without clobbering existing hooks.
- **Limitations:**
  - Focuses on lines of code metrics and telemetry rather than semantic symbol-level AST impact (classes, methods, blast radius, interactive graph).
- **Final Decision:** **Reference only & Adapt hook modules** in Phase 4 (`integrations/`).
- **Reason:** The hook installation mechanisms and session attribution heuristics will be adapted into CodePulse's `integrations/` layer, while keeping AST symbol parsing and review UI as CodePulse's core.

---

### 3.3 Codesight

- **Repository:** [https://github.com/spirituslab/codesight](https://github.com/spirituslab/codesight)
- **License:** MIT License (Verified: November 2026)
- **Main Technologies:** TypeScript, Tree-sitter (WASM/Node), VS Code Extension API, Webview graph renderer.
- **Relevant Modules / Source Paths:**
  - `src/parser/`: Tree-sitter queries for call graphs and directory hierarchies.
  - `src/webview/`: Interactive drill-down graph visualization from repository -> directory -> file -> function.
  - `src/mcp/`: Claude Code MCP tool declarations.
- **Capabilities Can Be Reused / Adapted:**
  - UI drill-down paradigms: folder expansion, symbol clustering, focus modes.
  - Visual distinction between structural hierarchy (containment) and relational dependency (calls/imports).
- **Dependency & Compatibility Concerns:**
  - Written in TypeScript for VS Code webviews; CodePulse's core intelligence engine is local Python/FastAPI with a React web dashboard and VS Code extension client.
- **Limitations:**
  - Single-user VS Code bound; lacks real-time agent session tracking, live change detection timeline, and review accept/reject workflow.
- **Final Decision:** **Reference only** (Inform frontend React Flow hierarchy navigation and Phase 6 VS Code extension).
- **Reason:** Codesight validates the drillable hierarchical graph UX. We will implement our web dashboard using React + React Flow consuming the CodePulse FastAPI backend.

---

### 3.4 VibeTracer

- **Repository:** [https://github.com/omeedcs/vibetracer](https://github.com/omeedcs/vibetracer)
- **License:** MIT License (Verified: November 2026)
- **Main Technologies:** Python / Rust, Terminal User Interface (Textual/curses), Watchdog, Git diff streaming.
- **Relevant Modules / Source Paths:**
  - `tracer/`: Real-time filesystem watcher debouncing, diff stream generation.
  - `timeline/`: Chronological event log with scrubber/rewind capabilities.
  - `restore/`: Surgical rollback of single-file or symbol edits.
- **Capabilities Can Be Reused / Adapted:**
  - Real-time debounced filesystem event processing using `watchdog`.
  - Chronological activity timeline model: recording timestamped change events (file modified, method added, diff captured).
  - Safe rollback concepts: restoring exact prior states via Git patches without blowing away uncommitted user work.
- **Dependency & Compatibility Concerns:**
  - TUI-oriented architecture; CodePulse requires browser-first and VS Code web interfaces backed by WebSockets.
- **Limitations:**
  - No symbol-level AST awareness; works at raw text/file diff levels.
- **Final Decision:** **Reference only & Adapt timeline model** in Phase 2 (`core/change_detector/`) and Phase 3 (`dashboard/`).
- **Reason:** VibeTracer's debounced change stream and safe rollback principles fit CodePulse's live timeline requirements.

---

### 3.5 Atlas

- **Repository:** [https://github.com/tryatlas/atlas](https://github.com/tryatlas/atlas)
- **License:** Apache License 2.0 (Verified: November 2026)
- **Main Technologies:** TypeScript / Go / Rust, multi-agent orchestrator, Git workflow manager.
- **Relevant Modules / Source Paths:**
  - Multi-agent coordination and session metadata tracking.
  - Commit association and automated review verification rules.
- **Capabilities Can Be Reused / Adapted:**
  - Multi-agent session taxonomy (Agent ID, Session ID, Prompt metadata, Tool executions, Commit association).
  - Status progression for reviews (Pending -> Under Review -> Accepted / Rejected).
- **Dependency & Compatibility Concerns:**
  - Large orchestration surface area beyond CodePulse's local-first observability scope.
- **Limitations:**
  - Heavy orchestration platform rather than a lightweight observer.
- **Final Decision:** **Reference only** for session and review state machine models.
- **Reason:** Provides a clean model for session metadata and review lifecycle states.

---

## 4. Secondary Reference Evaluations

| Candidate | URL | License | Decision | Reason |
|---|---|---|---|---|
| **GitNexus** | `abhigyanpatwari/GitNexus` | **PolyForm Noncommercial 1.0.0** | **REJECT** | **Restricted license.** PolyForm Noncommercial is incompatible with permissive open-source distribution. No code or dependencies may be reused. Architecture studied for zero-server indexing concepts only. |
| **CodeMap** | `POLPROG-TECH/CodeMap` | MIT | Reference only | C++ / Python call graph visualization ideas. |
| **CodeCharta** | `MaibornWolff/codecharta` | BSD-3-Clause | Reference only | City-metaphor 3D codebase visualization; too heavyweight for real-time diffs. |
| **git-sim** | `initialcommit-com/git-sim` | MIT | Reference only | Visualizing Git branch / commit topologies using Manim/SVG. |
| **AgentDiff** | `codeprakhar25/agentdiff` | MIT | Reference only | Prompt-to-diff correlation concepts. |
| **Graft** | `naouaro/graft` | MIT | Reference only | Dependency graph modeling in Python. |
| **OpenQodex** | `openqodex/openqodex` | Apache-2.0 | Reference only | Agent hook and telemetry format examples. |

---

## 5. Summary of Architecture & Component Decisions

1. **Repository Scanner & Symbol Extraction (`core/repository_scanner`):**
   - Standardize on official `tree-sitter` and modern wheels (`tree-sitter-python`, `tree-sitter-javascript`, `tree-sitter-typescript`, `tree-sitter-java`).
   - Modular language parser interface allowing new language plugins with zero core disruption.
2. **Symbol Graph & Storage (`core/symbol_graph`, `backend/storage`):**
   - Single local SQLite database (`.codepulse/codepulse.db`) per repository with WAL mode enabled.
   - Distinct storage of containment hierarchy (Architecture) and relational calls/imports (Dependencies).
3. **Change Detection (`core/change_detector`):**
   - Dual-engine: `watchdog` for debounced real-time filesystem events + Git CLI/GitPython for repository state baselines, staged diffs, and uncommitted tracking.
4. **Agent Attribution (`integrations/` & `core/session_manager`):**
   - Pluggable adapters (Claude Code, Cursor, Codex, Antigravity, Generic Git).
   - Strict evidence-based attribution: unknown edits are marked `unknown`, never falsely attributed.
5. **Impact & Blast Radius (`core/impact_analyzer`):**
   - SQLite recursive queries and NetworkX directed graph analysis for configurable depth traversal.
