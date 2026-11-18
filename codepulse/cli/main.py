"""CodePulse Command-Line Interface (CLI)."""

from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Optional
import typer
from rich.console import Console
from rich.table import Table
from rich.tree import Tree
from rich.panel import Panel

from codepulse.backend.storage.sqlite_store import SQLiteStore
from codepulse.core.change_detector.coordinator import ChangeCoordinator
from codepulse.core.models import ChangeStatus, SymbolDiff, SymbolType
from codepulse.core.repository_scanner.scanner import RepositoryScanner
from codepulse.core.session_manager.manager import SessionManager
from codepulse.core.symbol_graph.graph import SymbolGraphManager
from codepulse.integrations.registry import default_registry

app = typer.Typer(
    name="codepulse",
    help="CodePulse — Local-first code change intelligence and visualization platform",
    add_completion=False,
)
agents_app = typer.Typer(name="agents", help="Manage AI coding agent adapters and hooks.")
app.add_typer(agents_app, name="agents")
console = Console()


def get_db_path(repo_root: Path) -> Path:
    return repo_root / ".codepulse" / "codepulse.db"


@app.command()
def init(
    path: Path = typer.Argument(Path("."), help="Path to repository root")
) -> None:
    """Initialize CodePulse in a target repository."""
    repo_dir = path.resolve()
    codepulse_dir = repo_dir / ".codepulse"
    codepulse_dir.mkdir(parents=True, exist_ok=True)
    db_file = codepulse_dir / "codepulse.db"

    store = SQLiteStore(db_file)
    store.register_repository("default", str(repo_dir))

    console.print(
        Panel.fit(
            f"[bold green]Initialized CodePulse![/bold green]\n"
            f"Repository: [cyan]{repo_dir}[/cyan]\n"
            f"Database:   [cyan]{db_file}[/cyan]",
            title="CodePulse Init",
        )
    )


@app.command()
def scan(
    path: Path = typer.Argument(Path("."), help="Path to repository root"),
    force: bool = typer.Option(False, "--force", "-f", help="Force re-parsing of all files"),
) -> None:
    """Scan repository source code and build local symbol graph."""
    repo_dir = path.resolve()
    db_file = get_db_path(repo_dir)
    store = SQLiteStore(db_file)
    scanner = RepositoryScanner(store, repo_id="default")

    console.print(f"[bold blue]Scanning repository:[/bold blue] {repo_dir}...")
    result = scanner.scan_repository(repo_dir, force=force)

    table = Table(title="CodePulse Scan Summary", show_header=True, header_style="bold magenta")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Scanned Files", str(result["scanned_files"]))
    table.add_row("Parsed Files", str(result["parsed_files"]))
    table.add_row("Skipped (Unchanged)", str(result["skipped_files"]))
    table.add_row("Deleted Files", str(result["deleted_files"]))
    table.add_row("Total Indexed Symbols", str(result["total_symbols"]))
    table.add_row("Total Relationships", str(result["total_relationships"]))
    table.add_row("Scan Duration", f"{result['duration_seconds']}s")

    console.print(table)

    if result["languages"]:
        lang_table = Table(title="Languages Detected", show_header=True, header_style="bold yellow")
        lang_table.add_column("Language", style="cyan")
        lang_table.add_column("File Count", style="green")
        for lang, count in result["languages"].items():
            lang_table.add_row(lang.capitalize(), str(count))
        console.print(lang_table)


@app.command()
def status(
    path: Path = typer.Argument(Path("."), help="Path to repository root")
) -> None:
    """Display repository status, index metrics, and language statistics."""
    repo_dir = path.resolve()
    db_file = get_db_path(repo_dir)

    if not db_file.exists():
        console.print(
            f"[bold red]CodePulse is not initialized in {repo_dir}.[/bold red]\n"
            f"Run [cyan]codepulse init[/cyan] first."
        )
        raise typer.Exit(code=1)

    store = SQLiteStore(db_file)
    metrics = store.get_metrics("default")

    table = Table(title=f"CodePulse Status: {repo_dir.name}", show_header=True, header_style="bold green")
    table.add_column("Property", style="cyan")
    table.add_column("Detail", style="white")

    table.add_row("Repository Path", str(repo_dir))
    table.add_row("Database", str(db_file))
    table.add_row("Active Files", str(metrics.file_count))
    table.add_row("Indexed Symbols", str(metrics.symbol_count))
    table.add_row("Relationships", str(metrics.relationship_count))
    table.add_row("Last Scanned", metrics.last_scanned_at or "Never")

    console.print(table)


@app.command()
def graph(
    path: Path = typer.Argument(Path("."), help="Path to repository root"),
    file_path: Optional[str] = typer.Option(None, "--file", "-F", help="Filter by file path"),
    symbol_name: Optional[str] = typer.Option(None, "--symbol", "-S", help="Inspect blast radius for a symbol"),
    tree_view: bool = typer.Option(False, "--tree", "-t", help="Display hierarchical symbol tree"),
) -> None:
    """Display symbol graph or inspect impact / blast-radius for a symbol."""
    repo_dir = path.resolve()
    db_file = get_db_path(repo_dir)

    if not db_file.exists():
        console.print("[bold red]CodePulse database not found. Run 'codepulse init' and 'codepulse scan' first.[/bold red]")
        raise typer.Exit(code=1)

    store = SQLiteStore(db_file)
    graph_mgr = SymbolGraphManager(store, repo_id="default")

    if symbol_name:
        # Search symbol
        symbols = store.list_symbols("default")
        matches = [s for s in symbols if s.name == symbol_name]
        if not matches:
            console.print(f"[bold red]Symbol '{symbol_name}' not found in index.[/bold red]")
            raise typer.Exit(code=1)

        for sym in matches:
            blast = graph_mgr.get_blast_radius(sym.id)
            panel_text = (
                f"[bold cyan]Symbol:[/bold cyan] {sym.name} ({sym.symbol_type.value})\n"
                f"[bold cyan]File:[/bold cyan]   {sym.file_path}:{sym.start_line}-{sym.end_line}\n"
                f"[bold cyan]ID:[/bold cyan]     {sym.id}\n\n"
                f"[bold yellow]Impact / Blast Radius (Upstream Callers):[/bold yellow] {blast['upstream_callers_count']}\n"
            )
            for caller in blast["upstream_callers"]:
                panel_text += f"  • [red]{caller}[/red]\n"
            if not blast["upstream_callers"]:
                panel_text += "  (No upstream callers detected)\n"

            panel_text += f"\n[bold yellow]Downstream Invocations:[/bold yellow] {blast['downstream_dependencies_count']}\n"
            for callee in blast["downstream_dependencies"]:
                panel_text += f"  • [green]{callee}[/green]\n"

            console.print(Panel(panel_text, title=f"Blast Radius Analysis: {sym.name}"))
        return

    if tree_view:
        tree_data = graph_mgr.get_hierarchical_tree()
        root_tree = Tree(f"[bold blue]{repo_dir.name}[/bold blue]")

        for fnode in tree_data.get("children", []):
            f_tree = root_tree.add(f"[cyan]{fnode['name']}[/cyan] ({fnode['language']})")
            for c in fnode.get("classes", []):
                c_tree = f_tree.add(f"[yellow]class {c['name']}[/yellow] (lines {c['start_line']}-{c['end_line']})")
                for m in c.get("methods", []):
                    c_tree.add(f"[green]def {m['name']}[/green]")
            for fn in fnode.get("functions", []):
                f_tree.add(f"[green]def {fn['name']}[/green] (lines {fn['start_line']}-{fn['end_line']})")

        console.print(root_tree)
        return

    # Default: list symbols table
    symbols = store.list_symbols("default", file_path=file_path)
    table = Table(title=f"Symbols Index ({len(symbols)} total)", show_header=True, header_style="bold cyan")
    table.add_column("Type", style="yellow", width=10)
    table.add_column("Name", style="bold white")
    table.add_column("File Path", style="cyan")
    table.add_column("Lines", style="dim", width=12)

    for sym in symbols[:50]:  # Limit output in terminal
        table.add_row(
            sym.symbol_type.value,
            sym.name,
            sym.file_path,
            f"{sym.start_line}-{sym.end_line}",
        )

    console.print(table)
    if len(symbols) > 50:
        console.print(f"[dim]... and {len(symbols) - 50} more symbols. Use --tree or --file to filter.[/dim]")


@app.command()
def changes(
    path: Path = typer.Argument(Path("."), help="Path to repository root"),
    limit: int = typer.Option(50, "--limit", "-n", help="Max events to display"),
) -> None:
    """List detected symbol modifications and change history."""
    repo_dir = path.resolve()
    db_file = get_db_path(repo_dir)

    if not db_file.exists():
        console.print("[bold red]CodePulse is not initialized. Run 'codepulse init' and 'codepulse scan' first.[/bold red]")
        raise typer.Exit(code=1)

    store = SQLiteStore(db_file)
    events = store.list_change_events("default", limit=limit)
    changed_symbols = store.list_changed_symbols("default")

    if changed_symbols:
        table = Table(title="Current Changed / Impacted Symbols", show_header=True, header_style="bold yellow")
        table.add_column("Status", width=12)
        table.add_column("Type", width=10)
        table.add_column("Symbol", style="bold white")
        table.add_column("File Path", style="cyan")

        color_map = {
            ChangeStatus.ADDED: "[green]Added[/green]",
            ChangeStatus.MODIFIED: "[yellow]Modified[/yellow]",
            ChangeStatus.DELETED: "[red]Deleted[/red]",
            ChangeStatus.RENAMED: "[blue]Renamed[/blue]",
            ChangeStatus.IMPACTED: "[magenta]Impacted[/magenta]",
            ChangeStatus.UNCHANGED: "[dim]Unchanged[/dim]",
        }

        for sym in changed_symbols:
            table.add_row(
                color_map.get(sym.change_status, sym.change_status.value),
                sym.symbol_type.value,
                sym.name,
                sym.file_path,
            )
        console.print(table)

    if events:
        event_table = Table(title=f"Recent Activity Events ({len(events)})", show_header=True, header_style="bold cyan")
        event_table.add_column("Time", style="dim", width=20)
        event_table.add_column("Event", width=12)
        event_table.add_column("Agent", width=12)
        event_table.add_column("Summary", style="white")

        for ev in events:
            ev_color = {
                "added": "[green]added[/green]",
                "modified": "[yellow]modified[/yellow]",
                "deleted": "[red]deleted[/red]",
                "renamed": "[blue]renamed[/blue]",
            }.get(ev.event_type, ev.event_type)

            event_table.add_row(
                ev.timestamp[:19].replace("T", " "),
                ev_color,
                ev.agent_name,
                ev.summary or ev.file_path,
            )
        console.print(event_table)

    if not changed_symbols and not events:
        console.print("[green]No uncommitted or recorded changes found. Repository is clean.[/green]")


@app.command()
def watch(
    path: Path = typer.Argument(Path("."), help="Path to repository root")
) -> None:
    """Start real-time monitoring of repository changes and symbol updates."""
    repo_dir = path.resolve()
    db_file = get_db_path(repo_dir)

    if not db_file.exists():
        console.print("[bold red]CodePulse is not initialized. Run 'codepulse init' and 'codepulse scan' first.[/bold red]")
        raise typer.Exit(code=1)

    store = SQLiteStore(db_file)
    coordinator = ChangeCoordinator(repo_dir, store, repo_id="default")

    console.print(f"[bold cyan]CodePulse Change Watcher active on:[/bold cyan] {repo_dir}")
    baseline = coordinator.capture_baseline()
    console.print(f"[dim]Git Head: {baseline.get('head_commit') or 'none'} | Monitoring started[/dim]")

    def on_change(diffs: list[SymbolDiff]) -> None:
        for d in diffs:
            color = {
                ChangeStatus.ADDED: "green",
                ChangeStatus.MODIFIED: "yellow",
                ChangeStatus.DELETED: "red",
                ChangeStatus.RENAMED: "blue",
            }.get(d.status, "white")
            console.print(
                f"[{color}][{d.status.value.upper()}][/{color}] {d.symbol_type.value} [bold]{d.symbol_name}[/bold] in [cyan]{d.file_path}[/cyan]"
            )

    coordinator.start_watching(on_change_callback=on_change)
    console.print("[yellow]Press Ctrl+C to stop watching.[/yellow]")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        console.print("\n[bold blue]Stopping CodePulse watcher...[/bold blue]")
        coordinator.stop_watching()
        console.print("[green]Watcher stopped cleanly.[/green]")


@app.command()
def sessions(
    path: Path = typer.Argument(Path("."), help="Path to repository root"),
    limit: int = typer.Option(20, "--limit", "-n", help="Max sessions to display"),
) -> None:
    """Display active and historical AI coding agent sessions."""
    repo_dir = path.resolve()
    db_file = get_db_path(repo_dir)

    if not db_file.exists():
        console.print("[bold red]CodePulse is not initialized. Run 'codepulse init' and 'codepulse scan' first.[/bold red]")
        raise typer.Exit(code=1)

    store = SQLiteStore(db_file)
    session_mgr = SessionManager(store, repo_id="default")
    session_list = session_mgr.list_sessions(limit=limit)

    table = Table(title=f"Agent Sessions ({len(session_list)})", show_header=True, header_style="bold cyan")
    table.add_column("Session ID", style="dim", width=14)
    table.add_column("Agent", style="bold white", width=14)
    table.add_column("Status", width=10)
    table.add_column("Started", style="dim", width=20)
    table.add_column("Task Description", style="yellow")

    for s in session_list:
        status_color = "[green]active[/green]" if s.status == "active" else "[dim]completed[/dim]"
        table.add_row(
            s.id[:12] + "...",
            s.agent_name,
            status_color,
            s.started_at[:19].replace("T", " "),
            s.task_description or "(No description provided)",
        )

    console.print(table)


@agents_app.command("list")
def agents_list(
    path: Path = typer.Argument(Path("."), help="Path to repository root")
) -> None:
    """List supported AI agent integrations and their status."""
    repo_dir = path.resolve()
    status_list = default_registry.get_status(repo_dir)

    table = Table(title="AI Agent Adapters", show_header=True, header_style="bold magenta")
    table.add_column("Adapter", style="cyan")
    table.add_column("Display Name", style="white")
    table.add_column("CLI Detected", width=14)
    table.add_column("Hook Active", width=14)

    for a in status_list:
        inst_badge = "[green]Yes[/green]" if a["installed"] else "[dim]No[/dim]"
        hook_badge = "[green]Active[/green]" if a["hooked"] else "[dim]Inactive[/dim]"
        table.add_row(a["name"], a["display_name"], inst_badge, hook_badge)

    console.print(table)


@agents_app.command("install")
def agents_install(
    agent_name: str = typer.Argument(..., help="Name of agent (e.g. claude-code, cursor, codex, antigravity, generic-git)"),
    path: Path = typer.Argument(Path("."), help="Path to repository root"),
) -> None:
    """Install integration hook for a specific coding agent."""
    repo_dir = path.resolve()
    adapter = default_registry.get_adapter(agent_name)
    if not adapter:
        console.print(f"[bold red]Unknown agent adapter '{agent_name}'. Run 'codepulse agents list' to view supported adapters.[/bold red]")
        raise typer.Exit(code=1)

    success = adapter.install_hook(repo_dir)
    if success:
        console.print(f"[bold green]Successfully installed hook for {adapter.display_name} in {repo_dir}[/bold green]")
    else:
        console.print(f"[bold red]Failed to install hook for {adapter.display_name}.[/bold red]")


@agents_app.command("uninstall")
def agents_uninstall(
    agent_name: str = typer.Argument(..., help="Name of agent to uninstall hook for"),
    path: Path = typer.Argument(Path("."), help="Path to repository root"),
) -> None:
    """Uninstall integration hook for a specific coding agent."""
    repo_dir = path.resolve()
    adapter = default_registry.get_adapter(agent_name)
    if not adapter:
        console.print(f"[bold red]Unknown agent adapter '{agent_name}'.[/bold red]")
        raise typer.Exit(code=1)

    success = adapter.uninstall_hook(repo_dir)
    if success:
        console.print(f"[bold green]Successfully uninstalled hook for {adapter.display_name}.[/bold green]")
    else:
        console.print(f"[yellow]No active hook found for {adapter.display_name}.[/yellow]")


@app.command()
def start(
    path: Path = typer.Argument(Path("."), help="Path to repository root"),
    host: str = typer.Option("127.0.0.1", "--host", "-h", help="Host interface to bind"),
    port: int = typer.Option(8000, "--port", "-p", help="Port to listen on"),
) -> None:
    """Start CodePulse local HTTP server and WebSocket hub."""
    repo_dir = path.resolve()
    db_file = get_db_path(repo_dir)

    if not db_file.exists():
        console.print("[bold red]CodePulse is not initialized. Run 'codepulse init' and 'codepulse scan' first.[/bold red]")
        raise typer.Exit(code=1)

    import uvicorn
    from codepulse.backend.api.app import create_app

    console.print(
        Panel.fit(
            f"[bold green]Starting CodePulse Server[/bold green]\n"
            f"Repository: [cyan]{repo_dir}[/cyan]\n"
            f"API Server: [bold blue]http://{host}:{port}[/bold blue]\n"
            f"WebSocket:  [bold cyan]ws://{host}:{port}/ws/events[/bold cyan]\n"
            f"Dashboard:  [bold white]http://{host}:{port}[/bold white]",
            title="CodePulse Hub",
        )
    )
    api_app = create_app(repo_root=repo_dir, db_path=db_file)
    uvicorn.run(api_app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    app()
