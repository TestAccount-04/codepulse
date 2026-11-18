# CodePulse VS Code Extension

Lightweight Visual Studio Code extension integrating with the local **CodePulse** intelligence engine.

## Features

- **Activity Bar View**: Browse changed files and symbols modified by AI coding agents in real-time.
- **Review Decision Workflow**:
  - Accept changes (preserving repository files as specified in CodePulse specs).
  - Reject changes with **Safe Git Rollback** that surgical isolates symbol changes and protects unrelated user edits.
  - Mark symbols as reviewed.
  - Attach review annotations/notes to symbol changes.
- **Symbol Navigation**: One-click jump to changed symbols at their exact line number in the editor.
- **Impact & Grounded Explanations**: Inspect What / Why / Impact reports, blast-radius risk levels, and callers directly within VS Code.
- **Active Session Observability**: View current coding agent name, session status, and task description.
- **Web Dashboard Quick Access**: One-click opening of the interactive React Flow visual graph.

## Setup

1. Start the CodePulse local backend in your project repository:
   ```bash
   codepulse start
   ```
2. The extension connects to `http://127.0.0.1:8000` by default. You can configure this setting via `codepulse.backendUrl`.
