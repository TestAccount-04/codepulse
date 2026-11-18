# CodePulse — Security & Privacy Architecture

CodePulse is built on a **local-first** security model. It acts as an independent observability, intelligence, and review layer alongside coding agents (Claude Code, Cursor, Codex, Antigravity, etc.) without transmitting proprietary source code or credentials to external servers.

---

## 1. Local-First Security Principles

1. **No Mandatory Cloud Accounts or External APIs**:
   - CodePulse runs 100% locally on your workstation.
   - Core change detection, AST parsing, symbol indexing, blast-radius calculation, and review management operate without external network dependencies.
2. **Localhost Network Binding**:
   - The FastAPI REST API and WebSocket event hub bind strictly to `127.0.0.1` by default.
   - External network interfaces are never opened unless explicitly instructed via `--host`.
3. **No Telemetry or Code Transmission**:
   - CodePulse contains no telemetry, crash reporters, analytics trackers, or hidden analytics pings.
   - Repository source code, AST symbols, and diffs never leave the local machine.
4. **Local SQLite Persistence**:
   - All indexed repository data is stored in the target repository under `.codepulse/codepulse.db`.
   - SQLite WAL (Write-Ahead Logging) mode and foreign-key constraints ensure consistency without background daemon leaks.

---

## 2. Sensitive File & Secret Exclusions

CodePulse automatically excludes sensitive files and credential stores from indexing and change monitoring:

- **Environment & Keys**: `.env`, `.env.*`, `*.env`, `*.pem`, `*.key`, `*.pfx`, `*.p12`.
- **SSH & Cloud Credentials**: `id_rsa`, `id_rsa.pub`, `id_ed25519`, `credentials.json`, `*.credentials`, `service-account*.json`.
- **Databases & Caches**: `*.sqlite`, `*.sqlite3`, `*.db`, `*.log`, `__pycache__`, `.pytest_cache`.
- **VCS & Build Artifacts**: `.git`, `.venv`, `venv`, `node_modules`, `dist`, `build`.
- **Respects Repository `.gitignore`**: Any patterns defined in the project's `.gitignore` are parsed and respected by the scanner.

---

## 3. Path Traversal & Injection Safeguards

- **Strict Path Containment**: All endpoints accepting file paths or symbol paths normalize targets using `Path.resolve()` and verify that the target path `is_relative_to(root_path)`. Any attempt to reference files outside the repository boundary (e.g. `../../etc/passwd` or `..\\..\\`) immediately triggers a `400 Bad Request` rejection.
- **SQL Injection Prevention**: All queries in `SQLiteStore` use parameterized SQL statements (`?` placeholders). No user inputs or file contents are concatenated directly into SQL queries.

---

## 4. Git Safety Invariants

- **Review Acceptance**: As mandated by Section 12 of the specification, accepting a change **never automatically modifies repository files or Git state**.
- **Safe Rollback**: Rejection and rollback operations are Git-aware and non-destructive:
  - If only the rejected symbol was modified in the file, the file is restored to Git HEAD.
  - If multiple symbols or unrelated user edits exist in the file, CodePulse performs surgical symbol replacement, **preserving all unrelated user changes**.
  - If surgical isolation cannot be safely guaranteed, CodePulse refuses the automated rollback and alerts the developer to resolve manually.
- **Destructive Operations**: CodePulse never executes `git reset --hard`, `git clean -fdx`, or branch deletion.

---

## 5. Vulnerability Reporting

If you discover a security vulnerability in CodePulse, please submit an issue or security advisory via the official project repository.
