# Third-Party Notices & Dependency Attribution

This document lists the third-party dependencies, open-source libraries, and architectural references evaluated and utilized by CodePulse.

---

## 1. Direct Python Dependencies

The following packages are installed as direct dependencies of CodePulse under permissive open-source licenses:

| Package | Purpose | License |
|---|---|---|
| `tree-sitter` | Core incremental syntax tree parsing library | MIT License |
| `tree-sitter-python` | Python grammar bindings for Tree-sitter | MIT License |
| `tree-sitter-javascript` | JavaScript grammar bindings for Tree-sitter | MIT License |
| `tree-sitter-typescript` | TypeScript grammar bindings for Tree-sitter | MIT License |
| `tree-sitter-java` | Java grammar bindings for Tree-sitter | MIT License |
| `fastapi` | High-performance local REST API server | MIT License |
| `uvicorn` | ASGI server implementation | BSD-3-Clause License |
| `pydantic` | Data validation and settings management | MIT License |
| `typer` | Command-line interface framework | MIT License |
| `rich` | Rich text and terminal formatting | MIT License |
| `watchdog` | Cross-platform filesystem event monitoring | Apache License 2.0 |
| `gitpython` | Git repository inspection and plumbing | BSD-3-Clause License |
| `networkx` | Graph data structures and network algorithms | BSD-3-Clause License |
| `pytest` | Automated testing framework (development dependency) | MIT License |

---

## 2. Architectural References & Attribution

In accordance with CodePulse Specification Section 2 (*Reference-Driven Development Strategy*), CodePulse's design references patterns pioneered by several open-source tools:

- **code-review-graph** (Author: Tirth Kanani, MIT License)
  - Reference for Tree-sitter AST queries and blast-radius traversal concepts.
- **PostHook** (Author: Bilanc, MIT License)
  - Reference for non-destructive Git hooks and session-to-commit attribution concepts.
- **Codesight** (Author: spirituslab, MIT License)
  - Reference for drill-down codebase hierarchy visualization.
- **VibeTracer** (Author: Omeed Tavasoli, MIT License)
  - Reference for debounced change timeline and safe rollback concepts.
- **Atlas** (Author: tryatlas, Apache License 2.0)
  - Reference for multi-agent session state taxonomy and review workflow models.

All referenced open-source projects retain their respective copyrights. CodePulse is an independent clean-room implementation.
