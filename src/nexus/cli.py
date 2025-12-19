"""
MoMo-Nexus CLI.

Typer-based command line interface.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import typer
from rich import print as rprint
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from nexus._version import __version__
from nexus.config import NexusConfig, load_config

app = typer.Typer(
    name="nexus",
    help="MoMo-Nexus - Central Communication Hub",
    add_completion=False,
)
console = Console()


# =============================================================================
# Version Callback
# =============================================================================


def version_callback(value: bool) -> None:
    """Show version and exit."""
    if value:
        rprint(f"[bold blue]MoMo-Nexus[/bold blue] v{__version__}")
        raise typer.Exit()


# =============================================================================
# Main Commands
# =============================================================================


@app.callback()
def main(
    version: bool = typer.Option(
        None,
        "--version",
        "-V",
        callback=version_callback,
        is_eager=True,
        help="Show version",
    ),
) -> None:
    """MoMo-Nexus - Central Communication Hub for MoMo Ecosystem."""
    pass


@app.command()
def run(
    config: Path | None = typer.Option(
        None,
        "--config",
        "-c",
        help="Config file path",
    ),
    debug: bool = typer.Option(
        False,
        "--debug",
        "-d",
        help="Enable debug mode",
    ),
    api: bool = typer.Option(
        True,
        "--api/--no-api",
        help="Enable API server",
    ),
) -> None:
    """Start the Nexus hub."""
    import logging

    from nexus.app import NexusApp

    # Setup logging
    log_level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    rprint(Panel.fit(
        f"[bold blue]MoMo-Nexus[/bold blue] v{__version__}\n"
        "[dim]Central Communication Hub[/dim]",
        border_style="blue",
    ))

    # Load config
    cfg = load_config(config)
    rprint(f"[dim]Device ID:[/dim] {cfg.device_id}")
    rprint(f"[dim]Enabled channels:[/dim] {', '.join(c.value for c in cfg.get_enabled_channels())}")

    if debug:
        rprint("[yellow]Debug mode enabled[/yellow]")

    async def run_app() -> None:
        nexus = NexusApp(cfg)

        try:
            await nexus.start()
            rprint("[green]✓ Nexus started[/green]")

            if api and cfg.server.enabled:
                rprint(f"[dim]API Server:[/dim] http://{cfg.server.host}:{cfg.server.port}")

                # Start API server
                import uvicorn

                from nexus.api.app import NexusAPI

                api_app = NexusAPI(
                    config=cfg,
                    router=nexus.router,
                    channel_manager=nexus.channel_manager,
                    fleet_manager=nexus.fleet_manager,
                )

                rprint(f"[dim]API Key:[/dim] {api_app.api_key[:8]}...")

                config_uvicorn = uvicorn.Config(
                    app=api_app.app,
                    host=cfg.server.host,
                    port=cfg.server.port,
                    log_level="warning",
                )
                server = uvicorn.Server(config_uvicorn)
                await server.serve()
            else:
                # Run without API
                await nexus._shutdown_event.wait()

        except KeyboardInterrupt:
            rprint("\n[yellow]Shutting down...[/yellow]")
        finally:
            await nexus.stop()
            rprint("[green]✓ Nexus stopped[/green]")

    asyncio.run(run_app())


@app.command()
def status(
    config: Path | None = typer.Option(None, "--config", "-c"),
) -> None:
    """Show Nexus status."""
    cfg = load_config(config)

    table = Table(title="Nexus Status", show_header=True)
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Device ID", cfg.device_id)
    table.add_row("Name", cfg.name)
    table.add_row("Version", cfg.version)
    table.add_row("Server", f"{cfg.server.host}:{cfg.server.port}")
    table.add_row("Database", cfg.database.path)

    console.print(table)

    # Channels
    channels_table = Table(title="Channels", show_header=True)
    channels_table.add_column("Channel", style="cyan")
    channels_table.add_column("Enabled", style="green")
    channels_table.add_column("Status", style="yellow")

    channels_table.add_row(
        "LoRa",
        "✓" if cfg.channels.lora.enabled else "✗",
        "Not connected",
    )
    channels_table.add_row(
        "Cellular",
        "✓" if cfg.channels.cellular.enabled else "✗",
        "Not connected",
    )
    channels_table.add_row(
        "WiFi",
        "✓" if cfg.channels.wifi.enabled else "✗",
        "Not connected",
    )
    channels_table.add_row(
        "BLE",
        "✓" if cfg.channels.ble.enabled else "✗",
        "Not connected",
    )

    console.print(channels_table)


@app.command()
def config(
    show: bool = typer.Option(False, "--show", "-s", help="Show current config"),
    generate: bool = typer.Option(False, "--generate", "-g", help="Generate default config"),
    output: Path | None = typer.Option(None, "--output", "-o", help="Output path"),
) -> None:
    """Manage configuration."""
    if generate:
        cfg = NexusConfig()
        output_path = output or Path("nexus.yml")
        cfg.to_yaml(output_path)
        rprint(f"[green]Generated config:[/green] {output_path}")
        return

    if show:
        cfg = load_config()
        import yaml
        rprint(yaml.dump(cfg.model_dump(), default_flow_style=False))
        return

    rprint("Use --show to view config or --generate to create default config")


@app.command()
def devices(
    config: Path | None = typer.Option(None, "--config", "-c"),
) -> None:
    """List registered devices."""
    from nexus.infrastructure.database import DeviceStore

    async def list_devices() -> None:
        cfg = load_config(config)
        store = DeviceStore(cfg.database.path)

        try:
            await store.connect()
            all_devices = await store.get_all()

            if not all_devices:
                rprint("[yellow]No devices registered[/yellow]")
                return

            table = Table(title="Registered Devices", show_header=True)
            table.add_column("ID", style="cyan")
            table.add_column("Type", style="blue")
            table.add_column("Name")
            table.add_column("Status", style="green")
            table.add_column("Last Seen")

            for device in all_devices:
                status_color = {
                    "online": "green",
                    "sleeping": "yellow",
                    "offline": "red",
                    "lost": "red dim",
                }.get(device.status, "white")

                table.add_row(
                    device.id,
                    str(device.type),
                    device.name or "-",
                    f"[{status_color}]{device.status}[/{status_color}]",
                    device.last_seen.strftime("%Y-%m-%d %H:%M") if device.last_seen else "-",
                )

            console.print(table)

        finally:
            await store.disconnect()

    asyncio.run(list_devices())


@app.command()
def messages(
    count: int = typer.Option(20, "--count", "-n", help="Number of messages"),
    config: Path | None = typer.Option(None, "--config", "-c"),
) -> None:
    """List recent messages."""
    from nexus.infrastructure.database import MessageStore

    async def list_messages() -> None:
        cfg = load_config(config)
        store = MessageStore(cfg.database.path)

        try:
            await store.connect()
            recent = await store.get_recent(limit=count)

            if not recent:
                rprint("[yellow]No messages found[/yellow]")
                return

            table = Table(title=f"Recent Messages (last {count})", show_header=True)
            table.add_column("ID", style="dim")
            table.add_column("Type", style="cyan")
            table.add_column("Src", style="blue")
            table.add_column("Dst", style="green")
            table.add_column("Priority")
            table.add_column("Time")

            for msg in recent:
                priority_color = {
                    "critical": "red bold",
                    "high": "yellow",
                    "normal": "white",
                    "low": "dim",
                }.get(str(msg.pri), "white")

                table.add_row(
                    msg.id[:8],
                    str(msg.type),
                    msg.src,
                    msg.dst or "*",
                    f"[{priority_color}]{msg.pri}[/{priority_color}]",
                    msg.created_at.strftime("%H:%M:%S"),
                )

            console.print(table)

        finally:
            await store.disconnect()

    asyncio.run(list_messages())


@app.command()
def test(
    channel: str = typer.Option("mock", "--channel", "-c", help="Channel to test"),
) -> None:
    """Test channel connectivity."""
    from nexus.channels.mock import MockChannel
    from nexus.domain.enums import MessageType
    from nexus.domain.models import Message

    async def run_test() -> None:
        rprint(f"[blue]Testing channel:[/blue] {channel}")

        if channel == "mock":
            ch = MockChannel(latency_ms=50)
            await ch.connect()

            msg = Message(
                src="nexus",
                dst="test-device",
                type=MessageType.PING,
            )

            rprint("[dim]Sending test message...[/dim]")
            success = await ch.send(msg)

            if success:
                rprint("[green]✓ Message sent successfully[/green]")
                rprint(f"[dim]  Latency: {ch.metrics.latency_ms:.1f}ms[/dim]")
            else:
                rprint("[red]✗ Message send failed[/red]")

            await ch.disconnect()
        else:
            rprint(f"[yellow]Channel '{channel}' not implemented yet[/yellow]")

    asyncio.run(run_test())


# =============================================================================
# Entry Point
# =============================================================================

if __name__ == "__main__":
    app()

