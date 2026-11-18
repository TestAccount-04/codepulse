# CodePulse — Product & Technical Specification

**Document type:** Master Product and Implementation Specification  
**Product:** CodePulse  
**Goal:** Open-source, local-first code change intelligence and visualization platform  
**Development approach:** Reference-driven development with selective open-source reuse  
**Target development agents:** Claude Code, Codex, Antigravity, Cursor and other coding agents

---

# 1. Product Vision

CodePulse is an open-source developer tool that makes AI coding-agent activity visible, understandable and reviewable.

When a coding agent modifies a repository, developers should be able to see:

- Which folders, files, classes, functions and methods were affected.
- What changed in each affected component.
- Why the agent made those changes.
- How the changes affect other components.
- Which dependencies, callers and downstream components might be impacted.
- Which agent or session produced the changes.
- How the codebase evolved during a task.

The central experience is an interactive repository graph that highlights changes in real time.

CodePulse should work across different coding agents without requiring the developer to switch their primary development environment.

## 1.1 Core principle

CodePulse is not another AI coding agent.

It is an independent intelligence, observability and review layer that works alongside coding agents.

It should help developers answer:

1. What did the agent change?
2. Where did it change?
3. Why did it change?
4. What else might be affected?
5. Is the change safe and consistent with the task?
6. What should I review before accepting the changes?

# 2. Reference-Driven Development Strategy

## 2.1 Important development instruction

Do not build every component from scratch.

Before implementing a capability, inspect the open-source projects listed below and identify whether their existing implementation can be reused.

The goal is to save development time while maintaining CodePulse as an independent product.

The agent must:

1. Inspect the reference repository and its documentation.
2. Understand its architecture and implementation.
3. Inspect its actual license and relevant dependency licenses.
4. Identify reusable modules, APIs, libraries or algorithms.
5. Determine whether direct dependency integration, selective code reuse or independent implementation is best.
6. Reuse only the required components.
7. Implement CodePulse-specific functionality ourselves.
8. Document every meaningful reuse decision.

Do not blindly clone or copy entire repositories.

Do not assume a feature is reusable merely because a repository advertises it.

## 2.2 Reference repositories

### A. Code intelligence and repository graph

**code-review-graph**

Repository: https://github.com/tirth8205/code-review-graph

Investigate:

- Tree-sitter-based source parsing.
- Function and class extraction.
- Import and call relationships.
- SQLite graph storage.
- Incremental graph updates.
- Dependency and blast-radius analysis.
- Agent hooks and integrations.
- MCP interfaces.
- Existing CLI capabilities.

Potential use: accelerate CodePulse's repository intelligence and symbol graph implementation.

### B. Agent change attribution

**Posthook**

Repository: https://github.com/Bilanc/posthook

Investigate:

- Git instrumentation.
- Agent session tracking.
- File and line attribution.
- Claude Code hooks.
- Cursor hooks.
- Codex CLI hooks.
- SQLite storage.
- Session-to-commit association.

Potential use: agent activity attribution and session history.

### C. Code structure visualization

**Codesight**

Repository: https://github.com/spirituslab/codesight

Investigate:

- Tree-sitter code structure visualization.
- Directory-to-function navigation.
- Dependency and call graph visualization.
- Interactive graph exploration.
- VS Code integration.

Potential use: reference for graph navigation and code structure visualization.

### D. Live agent change tracing

**VibeTracer**

Repository: https://github.com/omeedcs/vibetracer

Investigate:

- Real-time edit tracking.
- Agent activity timelines.
- Edit attribution.
- Replay and rewind concepts.
- Change history.
- Agent trace export.

Potential use: live change timeline and session activity visualization.

### E. Agent session and Git workflow management

**Atlas**

Repository: https://github.com/tryatlas/atlas

Investigate:

- Multi-agent session tracking.
- Commit association.
- Agent activity history.
- CLI and desktop architecture.
- Integration patterns for multiple coding agents.

Potential use: agent session management concepts.

### F. Additional references

Inspect these only when they offer a concrete benefit:

- GitNexus: https://github.com/abhigyanpatwari/GitNexus
- CodeMap: https://github.com/POLPROG-TECH/CodeMap
- CodeCharta: https://github.com/MaibornWolff/codecharta
- GRASP: https://github.com/ashfordeOU/grasp
- git-sim: https://github.com/initialcommit-com/git-sim
- AgentDiff: https://github.com/codeprakhar25/agentdiff
- Graft: https://github.com/naouaro/graft
- OpenQodex: https://github.com/openqodex/openqodex

GitNexus has been described as using a PolyForm Noncommercial license. Do not make it a required dependency or reuse its code without a license review and explicit approval for the intended distribution model.

## 2.3 Reuse decision rules

For every reference project, classify the potential reuse:

| Decision | Meaning |
|---|---|
| Reuse dependency | Integrate the package or library |
| Reuse module | Adapt a specific implementation where licensing permits |
| Integrate through API | Consume an existing service or interface |
| Reference only | Study its architecture and independently implement the capability |
| Reject | Not useful, incompatible or unsuitable |

Prefer established dependencies over copied code when practical.

If code is copied or adapted, preserve applicable copyright notices and license obligations.

Never remove attribution or license notices.

Do not introduce a dependency with incompatible licensing into the distributable product.

## 2.4 Mandatory reference analysis document

Create:

`docs/REFERENCE_ANALYSIS.md`

For each inspected project, document:

- Repository name and GitHub URL.
- License and verification date.
- Main technologies.
- Relevant modules and source paths.
- Capabilities that can be reused.
- Integration options.
- Dependency and compatibility concerns.
- Limitations.
- Final decision.
- Reason for the decision.

Also create:

`docs/implementation_decisions.md`

Record important architectural choices, including why we chose to reuse or independently implement each capability.

Create:

`THIRD_PARTY_NOTICES.md`

Document third-party dependencies, reused code, licenses, copyright notices and modifications.

**Important:** Do not spend excessive time studying every reference. Start with the most relevant projects, produce a practical comparison, and move into implementation.

# 3. Product Ownership and Boundaries

CodePulse must have its own:

- Product identity and branding.
- Repository and source code.
- Core data model.
- Internal APIs.
- Graph visualization experience.
- Task and session correlation logic.
- Change explanation system.
- Review workflow.
- Configuration and settings.
- Documentation and roadmap.

External projects are implementation accelerators, not the foundation of our product identity.

Keep external dependencies modular and replaceable.

Do not make CodePulse dependent on a single reference project's internal implementation unless there is a clear technical reason.

# 4. Product Architecture

Use a local-first, agent-independent architecture.

The system should contain:

1. Repository intelligence engine.
2. Change detection engine.
3. Agent integration layer.
4. Session management.
5. Dependency and impact analysis.
6. Change explanation engine.
7. Backend API.
8. Interactive browser dashboard.
9. VS Code extension.
10. CLI.

Conceptual architecture:

```text
                  CODING AGENTS
       Claude | Codex | Cursor | Antigravity
                        |
                  Agent Adapters
                        |
                        v
+---------------------------------------------+
|                 CODEPULSE                    |
|                                             |
|  Change Detection       Session Manager     |
|         |                     |             |
|         v                     v             |
|  Repository Scanner     Task Correlation    |
|         |                     |             |
|         v                     v             |
|  Symbol Graph          Change Explanation   |
|         |                     |             |
|         v                     v             |
|  Dependency Analysis    Impact Analysis     |
|         |                     |             |
|         +----------+----------+             |
|                    |                        |
|              Core Data Store                |
|                    |                        |
|              Local API / WebSocket           |
+--------------------+------------------------+
                     |
             +-------+-------+
             |               |
             v               v
       Web Dashboard     VS Code Extension
```

## 4.1 Technology preferences

Use the following as the starting stack. Adjust only when reference analysis demonstrates a meaningful improvement.

### Core

- Python 3.11+
- FastAPI
- Pydantic
- SQLite
- Tree-sitter
- Git CLI or GitPython
- Watchdog
- NetworkX where useful

### Frontend

- React
- TypeScript
- Vite
- React Flow for interactive graphs
- Tailwind CSS or an equivalent maintainable styling system

### Realtime

- WebSockets.
- Local filesystem monitoring.
- Incremental Git snapshots.

### Testing

- Pytest.
- Playwright.
- Frontend unit tests.
- Integration tests.

Avoid unnecessary infrastructure, paid services and cloud dependencies.

# 5. Repository Intelligence Engine

CodePulse must understand a repository's structure.

The scanner should identify:

```text
Repository
  |
  +-- Folder
       |
       +-- File
            |
            +-- Class
            |    |
            |    +-- Method
            |    +-- Attribute
            |
            +-- Function
            |
            +-- Import
            |
            +-- Dependency
```

Initial language support:

- Python
- Java
- JavaScript
- TypeScript

Design the parser architecture so that additional languages can be added through independent language adapters.

## 5.1 Required capabilities

- Repository scanning.
- File and folder hierarchy.
- Class and function extraction.
- Method-level extraction.
- Import relationships.
- Call relationships where statically identifiable.
- Inheritance relationships.
- Test relationships where identifiable.
- Incremental updates.
- File-to-symbol mapping.
- Symbol identity across file changes.
- Parse error handling.

Use Tree-sitter or an appropriate existing implementation.

Do not implement a second parsing engine if a suitable reusable component already meets the requirements.

## 5.2 Graph types

Maintain two related but distinct graph views.

**Architecture graph**

Shows repository hierarchy:

Repository → Folder → File → Class → Method.

**Dependency graph**

Shows relationships:

Function → Calls → Function.

Class → Inherits → Class.

File → Imports → File.

Symbol → Tested by → Test.

Do not combine unrelated relationship types into an unreadable graph.

# 6. Change Detection Engine

This is one of the most important components.

CodePulse must detect changes regardless of which coding agent produced them.

Use two complementary mechanisms.

### A. Filesystem monitoring

Detect:

- File creation.
- File modification.
- File deletion.
- File rename where identifiable.
- Rapid successive edits.
- Directory changes.

Use filesystem monitoring as the universal fallback.

### B. Git-based tracking

Use Git to understand:

- Initial repository state.
- Existing uncommitted modifications.
- New modifications.
- Staged changes.
- Deleted files.
- Renames.
- Commits.
- Branch changes.

Do not assume all agent changes are committed.

### C. Agent hooks

Where supported, use native hooks to obtain:

- Agent name.
- Session ID.
- Task or prompt metadata where available.
- Tool execution events.
- File operation context.

Filesystem and Git tracking must continue to work even if hooks are unavailable.

## 6.1 Baseline and attribution

At startup:

1. Capture the initial Git state.
2. Identify existing uncommitted changes.
3. Begin filesystem monitoring.
4. Start or associate an agent session where possible.
5. Record subsequent changes.
6. Correlate changes with available session metadata.

Clearly distinguish:

- Pre-existing changes.
- Changes observed after CodePulse monitoring began.
- Changes attributed to a known agent session.
- Changes with unknown origin.

Never falsely attribute a change to an AI agent simply because it happened during an agent session.

# 7. Method-Level Change Intelligence

When a file changes, CodePulse should identify which symbols were affected.

Examples:

- New method.
- Modified method.
- Deleted method.
- Renamed method.
- New class.
- Modified class.
- Changed imports.
- Structural changes.

Use AST or Tree-sitter structural comparison where practical.

A change to one method should not automatically mark every method in the file as modified.

When precise attribution is impossible, report the uncertainty.

## 7.1 Change status colors

Use a consistent color system:

| Status | Suggested color |
|---|---|
| Added | Green |
| Modified | Yellow / Orange |
| Deleted | Red |
| Renamed | Blue |
| Impacted dependency | Purple |
| Unchanged | Neutral |

Provide a legend in the dashboard.

Do not confuse directly changed symbols with indirectly impacted symbols.

# 8. Interactive Graph Dashboard

The graph is the primary CodePulse experience.

The user should be able to explore the repository from high-level architecture to individual methods.

## 8.1 Navigation

Support:

- Repository overview.
- Folder expansion.
- File expansion.
- Class expansion.
- Method expansion.
- Dependency exploration.
- Upstream and downstream navigation.
- Search.
- Zoom and pan.
- Focus mode.
- Graph filtering.

Avoid rendering thousands of nodes at once.

Use progressive expansion and filtering.

## 8.2 Change visualization

When an agent modifies code:

- Highlight the affected file.
- Highlight the affected class.
- Highlight the affected methods.
- Show change status.
- Show the change summary.
- Show the associated task or session.
- Allow the user to open the actual diff.

The graph must update while the agent is working.

## 8.3 Node details

Selecting a node should open a details panel containing:

- Symbol name.
- File path.
- Symbol type.
- Change status.
- Change summary.
- Relevant diff.
- Related dependencies.
- Upstream callers.
- Downstream dependencies.
- Associated session.
- Last observed change.

The user should be able to navigate from a graph node directly to the corresponding source code.

# 9. Task and Session Intelligence

CodePulse must understand the context of an agent's work.

For each session, store:

- Session ID.
- Agent name.
- Repository.
- Task description, when available.
- Start time.
- End time.
- Files changed.
- Symbols changed.
- Change events.
- Associated commits.
- Review status.

Example:

```text
Session: Implement customer authentication

Agent: Claude Code

Files modified: 4
Classes affected: 2
Methods affected: 7

Changes:
+ Added validate_token()
~ Modified authenticate_user()
~ Modified login_controller()
+ Added refresh_session()
```

Support multiple sessions and agents.

If task descriptions are unavailable, allow users to add or edit a session description manually.

# 10. Change Explanation Engine

For every significant change, provide a concise explanation.

Example:

```text
Method: authenticate_user()

Status: Modified

What changed:
Added token-expiration validation before
creating an authenticated session.

Why:
The task required preventing expired tokens
from being accepted.

Impact:
Callers of authenticate_user() may now receive
an authentication failure for expired tokens.
```

Explanations must be grounded in:

- Actual code diffs.
- AST changes.
- Task descriptions.
- Dependency relationships.
- Agent-provided context where available.

Do not invent explanations.

If the reason cannot be established, say:

"Reason not available from observed evidence."

## 10.1 LLM integration

LLM-based explanations should be optional.

The core system must remain functional without an LLM.

Support configurable providers in the future, but do not require a cloud model for basic tracking, graph generation or diff analysis.

Keep sensitive source code local by default.

# 11. Dependency and Impact Analysis

When a method changes, CodePulse should identify potentially affected components.

Example:

```text
authenticate_user()
       |
       +-- login_controller()
       |
       +-- api_authentication()
       |
       +-- session_manager()
       |
       +-- authentication_tests()
```

Show:

- Direct callers.
- Indirect callers.
- Imported dependencies.
- Inheritance relationships.
- Related tests.
- Potential downstream impact.

Allow configurable impact depth.

Clearly distinguish statically established relationships from inferred or uncertain relationships.

Do not claim that a dependent component is broken merely because it is connected to a modified method.

# 12. Review Experience

CodePulse should provide a dedicated review panel.

For each changed symbol, show:

- Original code.
- Updated code.
- Structural change summary.
- Task context.
- Impact analysis.
- Associated agent session.
- Review annotations.

Support:

- Mark as reviewed.
- Accept.
- Reject.
- Add review notes.
- Open source file.
- Open Git diff.

Important: Review acceptance must not automatically modify the repository.

For rejection or rollback, use a safe, explicit Git-aware operation.

Never overwrite unrelated user changes.

# 13. Live Activity Timeline

Provide a chronological activity feed.

Example:

```text
10:01:12  Agent session started
10:01:18  Modified auth_service.py
10:01:19  Modified authenticate_user()
10:01:23  Added refresh_session()
10:01:31  Modified login_controller.py
10:01:35  Dependency impact updated
10:01:42  Agent session completed
```

Support filtering by:

- Agent.
- Session.
- File.
- Symbol.
- Change type.
- Time.

Provide historical session browsing.

# 14. Agent Integrations

CodePulse should be agent-independent.

Initial integration targets:

1. Claude Code.
2. Codex CLI.
3. Cursor.
4. Antigravity.
5. Generic Git/filesystem fallback.

Implement each integration as an independent adapter.

Use native hooks when documented and supported.

Do not depend on private APIs or undocumented internal behavior.

An adapter should be able to:

- Detect agent availability where practical.
- Register supported hooks.
- Receive lifecycle events.
- Capture session metadata.
- Associate observed changes with sessions.
- Uninstall cleanly.

Agent integrations must be optional.

CodePulse must still function without any agent integration.

## 14.1 Skills and commands

Provide CodePulse-specific agent skills where supported:

- `codepulse-analyze`
- `codepulse-review`
- `codepulse-explain`

These should allow an agent to query CodePulse's repository graph and explain changes.

A skill is not the change-detection engine. The core filesystem and Git monitoring mechanisms remain responsible for observing changes.

# 15. Backend and API

Use FastAPI initially.

Expose local APIs for:

- Repository registration.
- Repository scanning.
- Graph retrieval.
- Symbol lookup.
- Dependency lookup.
- Change events.
- Session management.
- Review annotations.
- Activity history.
- Agent integration status.

Use WebSockets for live updates.

Define stable API contracts so the browser dashboard and VS Code extension share the same backend.

Keep API authentication and network binding secure.

Default to localhost access.

# 16. VS Code Extension

The extension should reuse the CodePulse backend.

Do not implement a separate repository intelligence engine inside the extension.

Initial features:

- Repository status.
- Active session information.
- Changed file and symbol list.
- Change summaries.
- Impact analysis.
- Review status.
- Navigation to changed symbols.
- Access to the browser dashboard.

Keep the extension lightweight.

# 17. CLI

Provide a CLI using Typer or an equivalent Python CLI framework.

Proposed commands:

```bash
codepulse init
codepulse scan
codepulse watch
codepulse start
codepulse stop
codepulse status
codepulse sessions
codepulse review
codepulse graph
codepulse agents list
codepulse agents install
codepulse agents uninstall
```

Commands should be documented and have helpful error messages.

# 18. Data Storage

Use SQLite initially.

Proposed entities:

- repositories
- folders
- files
- symbols
- relationships
- sessions
- changes
- change_events
- snapshots
- reviews
- agent_integrations

Store stable symbol identifiers where practical.

Track repository and snapshot versions so historical graph states can be reconstructed.

Do not store unnecessary copies of source code.

Provide a configurable retention policy for activity history.

# 19. Project Structure

Use a modular structure similar to:

```text
CodePulse/
│
├── SPEC.md
├── README.md
├── LICENSE
├── THIRD_PARTY_NOTICES.md
│
├── docs/
│   ├── architecture.md
│   ├── REFERENCE_ANALYSIS.md
│   ├── implementation_decisions.md
│   ├── api.md
│   └── development.md
│
├── core/
│   ├── repository_scanner/
│   ├── change_detector/
│   ├── symbol_graph/
│   ├── dependency_analyzer/
│   ├── impact_analyzer/
│   ├── session_manager/
│   ├── explanation_engine/
│   └── review_engine/
│
├── integrations/
│   ├── claude_code/
│   ├── codex/
│   ├── cursor/
│   ├── antigravity/
│   └── generic_git/
│
├── backend/
│   ├── api/
│   ├── websocket/
│   └── storage/
│
├── dashboard/
│
├── vscode-extension/
│
├── cli/
│
├── tests/
│
└── scripts/
```

The building agent may adjust the structure after reference analysis, but it must preserve clear module boundaries.

# 20. Privacy and Security

CodePulse is local-first.

Requirements:

- No mandatory cloud account.
- No mandatory external API.
- No telemetry by default.
- No source-code upload by default.
- Local SQLite storage.
- Local dashboard by default.
- Configurable data retention.
- Secure handling of agent metadata.
- No destructive Git operations without explicit user action.
- Never overwrite unrelated user changes.
- Respect `.gitignore` and configurable exclusions.
- Avoid scanning secrets and sensitive directories unnecessarily.

# 21. Testing Strategy

Test with real repositories and simulated agent changes.

## Repository scanning

- Folder discovery.
- File discovery.
- Class extraction.
- Method extraction.
- Dependency extraction.
- Incremental updates.
- Multiple language support.

## Change detection

- New files.
- Modified files.
- Deleted files.
- Renamed files.
- Multiple edits.
- Existing uncommitted changes.
- Changes from unknown agents.

## Graph

- Correct hierarchy.
- Correct relationships.
- Incremental graph updates.
- Filtering.
- Large repositories.
- Graph performance.

## Agent integration

- Hook installation.
- Hook removal.
- Session association.
- Missing hook fallback.
- Multiple simultaneous sessions where supported.

## Review

- Correct diff association.
- Review annotations.
- Safe rejection.
- No unrelated file modification.

## End-to-end scenario

Give an AI coding agent a task that changes:

- Three files.
- Two classes.
- Five methods.

Verify that CodePulse:

1. Detects the changes.
2. Identifies the affected symbols.
3. Associates the changes with the session where evidence permits.
4. Updates the graph.
5. Shows the diffs.
6. Explains the changes.
7. Calculates dependency impact.
8. Records the session history.

# 22. Development Roadmap

Build incrementally. Each phase must have working code and tests.

## Phase 0 — Reference Analysis and Architecture

- Inspect code-review-graph.
- Inspect Posthook.
- Inspect Codesight.
- Inspect VibeTracer.
- Review other references only where useful.
- Verify licenses.
- Identify reusable modules.
- Produce `docs/REFERENCE_ANALYSIS.md`.
- Produce `docs/implementation_decisions.md`.
- Finalize the initial architecture.
- Set up the project repository.

Deliverable: documented architecture and reuse decisions.

## Phase 1 — Foundation and Repository Intelligence

- Project setup.
- CLI.
- Configuration.
- SQLite.
- Repository scanner.
- Tree-sitter integration.
- Symbol extraction.
- Graph generation.
- Basic tests.

Deliverable: scan a repository and retrieve its architecture graph.

## Phase 2 — Change Detection

- Git baseline.
- Filesystem monitoring.
- Change event storage.
- File-level diff.
- Symbol-level diff.
- Incremental graph updates.

Deliverable: observe code changes and identify affected symbols.

## Phase 3 — Interactive Dashboard

- React dashboard.
- Repository graph.
- Hierarchical navigation.
- Change colors.
- Details panel.
- Diff viewer.
- Live WebSocket updates.

Deliverable: see changes visually while editing code.

## Phase 4 — Agent Integration

- Claude Code adapter.
- Codex adapter.
- Cursor adapter.
- Antigravity adapter.
- Generic fallback.
- Session tracking.
- Agent activity timeline.

Deliverable: attribute changes to agent sessions when reliable evidence exists.

## Phase 5 — Impact and Explanation

- Dependency graph.
- Upstream/downstream analysis.
- Blast-radius calculation.
- Test relationship discovery.
- Evidence-grounded explanations.
- Optional LLM integration.

Deliverable: understand why a change happened and what it might affect.

## Phase 6 — Review and VS Code

- Review panel.
- Annotations.
- Accept/reject workflow.
- Safe rollback support.
- VS Code extension.

Deliverable: complete code change review workflow.

## Phase 7 — Stabilization and Release

- End-to-end tests.
- Large repository performance.
- Security review.
- Documentation.
- Installation experience.
- Packaging.
- Open-source release.

Deliverable: usable CodePulse release.

# 23. Mandatory Implementation Rules for the Building Agent

Follow these rules throughout development.

1. Read this specification completely before coding.
2. Analyze relevant reference repositories before implementing their capabilities.
3. Do not rebuild existing functionality without a reason.
4. Do not clone entire reference projects into CodePulse.
5. Do not copy code without verifying its license.
6. Keep CodePulse's core independent of optional external integrations.
7. Use a modular architecture.
8. Implement incrementally.
9. Write tests alongside each module.
10. Do not leave major features as placeholder implementations while claiming completion.
11. Do not fabricate agent attribution or change explanations.
12. Do not introduce paid services or mandatory cloud dependencies.
13. Keep the application functional without an LLM.
14. Preserve user changes and Git history.
15. Update documentation when architecture changes.
16. Record major implementation decisions.
17. Maintain `THIRD_PARTY_NOTICES.md`.
18. Run tests before marking a phase complete.
19. Report completed functionality, limitations and remaining work honestly.
20. Do not move to the next phase until the current phase's acceptance criteria pass.

# 24. First Implementation Assignment

Start with Phase 0 and Phase 1.

Do not immediately attempt to build the complete dashboard or all agent integrations.

First:

1. Inspect the reference repositories.
2. Produce the reference analysis.
3. Verify licenses.
4. Identify the most useful reusable components.
5. Decide the internal interfaces.
6. Set up the CodePulse project.
7. Implement repository scanning.
8. Extract files, classes, functions and methods.
9. Build the initial symbol and dependency graph.
10. Store the graph in SQLite.
11. Add automated tests.
12. Demonstrate the result on a real repository.

At the end, provide:

- Architecture summary.
- Reference reuse report.
- Project structure.
- Installation instructions.
- Commands to run.
- Test results.
- Implemented features.
- Known limitations.
- Next-phase implementation plan.

Do not start Phase 2 until Phase 1 is working and validated.

---

# 25. Definition of Success

CodePulse succeeds when a developer can start an AI coding session and see, in one place:

- What the agent is changing.
- Which files, classes and methods are changing.
- How the repository structure is affected.
- Why the changes were made, when evidence is available.
- Which components may be impacted.
- Which agent session produced the changes.
- What needs human review.

The experience should feel like a live visual control center for AI-assisted software development.

**Final product principle: Build CodePulse, reuse proven engineering, avoid unnecessary reinvention, and keep ownership of the product's core experience and architecture.**