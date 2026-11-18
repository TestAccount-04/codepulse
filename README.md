# CodePulse

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

**CodePulse** is an open-source, local-first code change intelligence and visualization platform. It makes AI coding-agent activity visible, understandable, and reviewable in real time.

---

## Key Features

- **Repository Intelligence:** AST-powered parsing of Python, JavaScript, TypeScript, and Java via Tree-sitter.
- **Hierarchical Symbol Graph:** Maps repositories from folders down to classes, methods, functions, and imports.
- **Dependency & Call Graph:** Traces function calls, class inheritance, module imports, and potential blast-radius impact.
- **Local-First & Privacy-Preserving:** Operates 100% on your local machine using SQLite (WAL mode). No mandatory cloud services, accounts, or telemetry.
- **Agent-Independent Observability:** Seamlessly correlates activity across coding agents (Claude Code, Cursor, Codex CLI, Antigravity) and human edits.

---

## Quick Start

### 1. Installation

```bash
# Clone and install in editable mode
git clone https://github.com/your-org/codepulse.git
cd codepulse

# Using uv (recommended)
uv venv
uv pip install -e ".[dev]"
```

### 2. Basic CLI Commands

```bash
# Initialize CodePulse in your repository
codepulse init

# Scan repository and extract symbols into the local SQLite graph
codepulse scan

# View repository metrics and status
codepulse status

# Inspect the symbol graph
codepulse graph
```

---

## Documentation

- [Product Specification](spec.md)
- [Reference Analysis & Reuse Report](docs/REFERENCE_ANALYSIS.md)
- [Implementation Decisions](docs/implementation_decisions.md)
- [System Architecture](docs/architecture.md)
- [Third-Party Notices](THIRD_PARTY_NOTICES.md)

---

## License

CodePulse is licensed under the [MIT License](LICENSE).
