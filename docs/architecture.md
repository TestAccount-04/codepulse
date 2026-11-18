# CodePulse — Architecture Specification

**Status:** Living Architecture Document  
**Version:** 0.1.0 (Phase 0 & Phase 1)  

---

## 1. High-Level System Architecture

CodePulse is structured as an agent-independent, local-first intelligence layer that monitors code changes, tracks AI agent activity, maintains an interactive symbol and dependency graph, and calculates the blast-radius impact of code modifications.

```text
                           DEVELOPMENT WORKFLOW
              AI Coding Agents (Claude, Cursor, Codex, Antigravity)
                                   & Humans
                                      │
                                      ▼
                        Filesystem & Git Repository
                                      │
             ┌────────────────────────┴────────────────────────┐
             ▼                                                 ▼
    [Watchdog Events]                                   [Git Status & Diffs]
             │                                                 │
             └────────────────────────┬────────────────────────┘
                                      ▼
                       ┌─────────────────────────────┐
                       │    Change Detection Engine  │
                       │    (Debounced event stream) │
                       └──────────────┬──────────────┘
                                      ▼
                       ┌─────────────────────────────┐
                       │  Repository Scanner Engine  │
                       │   (Tree-sitter AST queries) │
                       └──────────────┬──────────────┘
                                      ▼
                       ┌─────────────────────────────┐
                       │     Symbol & Dependency     │
                       │        Graph Manager        │
                       └──────────────┬──────────────┘
                                      ▼
                       ┌─────────────────────────────┐
                       │    Local SQLite Database    │
                       │    (.codepulse/codepulse.db)│
                       └──────────────┬──────────────┘
                                      │
                      ┌───────────────┴───────────────┐
                      ▼                               ▼
          [FastAPI REST Endpoints]        [WebSocket Event Bus]
                      │                               │
                      └───────────────┬───────────────┘
                                      ▼
                       ┌─────────────────────────────┐
                       │      Client Interfaces      │
                       │  CLI / Dashboard / VS Code  │
                       └─────────────────────────────┘
```

---

## 2. Core Entities & Data Model

### 2.1 Symbols (`symbols` table)
Represents extracted programming artifacts:
- `id`: Stable string identifier (`<file_path>::[<class_name>::]<symbol_type>::<symbol_name>`)
- `repo_id`: Identifier of the repository
- `file_path`: Relative path within repository
- `name`: Identifier name (e.g., `authenticate_user`)
- `symbol_type`: Enum: `file`, `class`, `function`, `method`, `interface`
- `parent_symbol_id`: Foreign key to parent symbol (e.g. parent class for a method)
- `start_line`: 1-based start line in source file
- `end_line`: 1-based end line in source file
- `start_byte`: Byte offset start
- `end_byte`: Byte offset end
- `signature`: Extracted signature / parameters
- `docstring`: Extracted documentation or comments
- `content_hash`: SHA256 hash of the symbol body

### 2.2 Relational Edges (`relationships` table)
Models semantic relationships between nodes:
- `id`: Primary key
- `source_id`: Source symbol ID
- `target_id`: Target symbol ID (or unresolved target name)
- `relationship_type`: 
  - `CONTAINS`: Structural containment (File contains Class, Class contains Method)
  - `CALLS`: Function or method invocations
  - `IMPORTS`: Module and symbol imports
  - `INHERITS`: Class inheritance and interface implementation
  - `TESTS`: Test relationship
- `metadata`: JSON object containing line number, import alias, or confidence score

### 2.3 Files & Folders (`files` table)
- `path`: Relative path within repository
- `sha256`: File content hash
- `mtime`: Modification timestamp
- `size_bytes`: File size
- `language`: Detected language (`python`, `javascript`, `typescript`, `java`)
- `is_deleted`: Soft-delete flag for tracking deletions

### 2.4 Change Events (`change_events` table)
- `id`: Unique event ID
- `timestamp`: UTC ISO timestamp
- `event_type`: `added`, `modified`, `deleted`, `renamed`
- `file_path`: Relative path
- `symbol_id`: Associated symbol (if resolved)
- `session_id`: Associated agent session ID (nullable)
- `agent_name`: Name of agent (or `human` / `unknown`)
- `diff_content`: Unified diff text
- `summary`: Human-readable summary of the modification

### 2.5 Agent Sessions (`sessions` table)
- `id`: UUID or agent-provided session token
- `agent_name`: e.g. `claude-code`, `cursor`, `codex`, `antigravity`, `generic`
- `task_description`: Natural language prompt or task goal
- `started_at`: UTC ISO timestamp
- `ended_at`: UTC ISO timestamp (nullable)
- `status`: `active`, `completed`, `aborted`
- `metadata`: JSON object with extra context

---

## 3. Repository Scanner & Tree-Sitter Integration

The repository scanner decomposes codebases into structured symbol hierarchies using language-specific Tree-sitter parsers:

1. **File Traversal:** Walks directory tree, ignoring patterns in `.gitignore` and default exclusions (`.git`, `.venv`, `node_modules`, `build`, `dist`, `.codepulse`).
2. **Grammar Dispatcher:** Dispatches to the appropriate language parser based on file extension:
   - Python (`.py`): Module, Class, Function, Method, Import, Call expressions
   - JavaScript (`.js`, `.jsx`, `.mjs`): Class, Function, Method, ArrowFunction, ES/CommonJS Imports, Calls
   - TypeScript (`.ts`, `.tsx`): Class, Interface, Function, Method, TypeAlias, Imports, Calls
   - Java (`.java`): Package, Class, Interface, Method, Constructor, Imports, MethodInvocations
3. **AST Querying & Extraction:** Recursively walks AST nodes, extracts signatures, line spans, docstrings, and builds symbol records.
4. **Relationship Linking:**
   - Containment edges are generated automatically from AST hierarchy.
   - Import edges are recorded with resolved module paths where possible.
   - Call edges are recorded from invocation expressions and resolved against symbol tables in the repository.

---

## 4. SQLite Storage Schema & Optimization

The database uses SQLite 3 with:
- `PRAGMA journal_mode = WAL;` (Concurrent readers during writes)
- `PRAGMA synchronous = NORMAL;` (Safe and optimal performance)
- `PRAGMA foreign_keys = ON;` (Referential integrity)
- Composite indices on `(file_path, symbol_type)`, `(source_id, relationship_type)`, and `(target_id, relationship_type)`.

---

## 5. CLI Interface Specification

The `codepulse` CLI provides an intuitive entry point:

- `codepulse init [path]`: Initializes `.codepulse` configuration and SQLite database in the target repository.
- `codepulse scan [path]`: Performs an initial or incremental scan of the repository and indexes all symbols and dependencies.
- `codepulse status [path]`: Displays repository metrics: files scanned, symbols indexed, relationships, active sessions, and recent changes.
- `codepulse graph [path]`: Generates and displays symbol summaries or exports graph data (JSON / DOT / Summary table).
- `codepulse sessions [path]`: Lists active and historical agent sessions.
