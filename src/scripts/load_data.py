#!/usr/bin/env python3
"""
Load and validate the synthetic campus dataset.

Usage:
    python -m src.scripts.load_data
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from clarion.config import config
from clarion.ingest import load_all


def main():
    console = Console()
    
    console.print(Panel.fit(
        "[bold blue]🔔 Clarion - Data Loader[/bold blue]\n"
        "Loading synthetic campus dataset...",
        border_style="blue"
    ))
    
    # Validate data files exist
    console.print("\n[bold]Checking data files...[/bold]")
    missing = config.data_files.validate()
    
    if missing:
        console.print(f"[red]❌ Missing files:[/red]")
        for f in missing:
            console.print(f"   - {f}")
        console.print("\n[yellow]Please ensure the synthetic data is in data/raw/trustsec_copilot_synth_campus/[/yellow]")
        return 1
    
    console.print("[green]✓ All data files present[/green]\n")
    
    # Load all data
    console.print("[bold]Loading data...[/bold]")
    try:
        data = load_all(include_flow_truth=True)
    except Exception as e:
        console.print(f"[red]❌ Error loading data: {e}[/red]")
        return 1
    
    console.print("[green]✓ Data loaded successfully[/green]\n")
    
    # Display summary
    table = Table(title="📊 Dataset Summary")
    table.add_column("Dataset", style="cyan")
    table.add_column("Records", justify="right", style="green")
    table.add_column("Columns", justify="right", style="yellow")
    
    summary = data.summary()
    dataframes = {
        "switches": data.switches,
        "interfaces": data.interfaces,
        "ad_users": data.ad_users,
        "ad_groups": data.ad_groups,
        "ad_group_membership": data.ad_group_membership,
        "endpoints": data.endpoints,
        "ip_assignments": data.ip_assignments,
        "ise_sessions": data.ise_sessions,
        "services": data.services,
        "sgts": data.sgts,
        "flows": data.flows,
        "flow_truth": data.flow_truth,
    }
    
    total_records = 0
    for name, df in dataframes.items():
        if df is not None:
            records = len(df)
            cols = len(df.columns)
            table.add_row(name, f"{records:,}", str(cols))
            total_records += records
    
    console.print(table)
    console.print(f"\n[bold]Total records:[/bold] {total_records:,}\n")
    
    # Show sample data
    console.print("[bold]Sample Flow Record:[/bold]")
    sample = data.flows.iloc[0].to_dict()
    for key, value in sample.items():
        console.print(f"  [cyan]{key}:[/cyan] {value}")
    
    console.print("\n[bold]Sample User:[/bold]")
    sample = data.ad_users.iloc[0].to_dict()
    for key, value in sample.items():
        console.print(f"  [cyan]{key}:[/cyan] {value}")
    
    console.print("\n[bold]Sample ISE Session:[/bold]")
    sample = data.ise_sessions.iloc[0].to_dict()
    for key, value in sample.items():
        console.print(f"  [cyan]{key}:[/cyan] {value}")
    
    console.print("\n[bold green]✓ Data ready for analysis![/bold green]")
    console.print("Next: Run [cyan]python -m src.scripts.analyze[/cyan] to analyze the data.\n")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

