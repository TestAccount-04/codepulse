"""CodePulse Command-Line Interface (CLI)."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional
import typer
from rich.console import Console
from rich.table import Table
from rich.tree import Tree
from rich.panel import Panel

from codepulse.backend.storage.sqlite_store import SQLiteStore
from codepulse.core.repository_scanner.scanner import RepositoryScanner
from codepulse.core.symbol_graph.graph import SymbolGraphManager
from codepulse.core.models import SymbolType

app = typer.Typer(
    name="codepulse",
    help="CodePulse — Local-first code change intelligence and visualization platform",
    add_completion=False,
)
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


if __name__ == "__main__":
    app()
