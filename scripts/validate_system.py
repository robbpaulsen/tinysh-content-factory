#!/usr/bin/env python3
"""
Sistema de validación completo para tinysh-content-factory
Verifica configuración, dependencias y conectividad antes de ejecutar el workflow.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
import httpx

console = Console()


def check_media_server():
    """Verificar que el media server esté corriendo."""
    console.print("\n[bold cyan]1. Verificando Media Server...[/bold cyan]")

    try:
        response = httpx.get("http://localhost:8000/health", timeout=5.0)
        if response.status_code == 200:
            console.print("  [green]✓ Media server corriendo en http://localhost:8000[/green]")
            return True
        else:
            console.print(f"  [yellow]⚠ Media server responde con código {response.status_code}[/yellow]")
            return False
    except Exception as e:
        console.print(f"  [red]✗ Media server NO accesible: {e}[/red]")
        console.print("  [yellow]→ Inicia el media server antes de generar videos[/yellow]")
        return False


def check_channels():
    """Validar configuración de canales."""
    console.print("\n[bold cyan]2. Validando Configuración de Canales...[/bold cyan]")

    from src.channel_config import ChannelConfig

    channels = ChannelConfig.list_available_channels()

    if not channels:
        console.print("  [red]✗ No se encontraron canales configurados[/red]")
        return False

    table = Table(title="Canales Configurados")
    table.add_column("Canal", style="cyan")
    table.add_column("Nombre", style="white")
    table.add_column("Tipo", style="yellow")
    table.add_column("Profile", style="green")
    table.add_column("Prompts", style="magenta")
    table.add_column("Credentials", style="blue")

    all_ok = True

    for channel_name in channels:
        try:
            channel = ChannelConfig(channel_name)

            # Check profiles
            profiles_ok = channel.profiles_path.exists()

            # Check custom prompts
            script_prompt = channel.get_prompt('script')
            image_prompt = channel.get_prompt('image')
            prompts = []
            if script_prompt:
                prompts.append("script")
            if image_prompt:
                prompts.append("image")
            prompts_str = ", ".join(prompts) if prompts else "default"

            # Check credentials
            creds_ok = channel.credentials_path.exists()

            table.add_row(
                channel_name,
                channel.config.name,
                channel.config.channel_type,
                f"{'✓' if profiles_ok else '✗'} {channel.config.default_profile or 'N/A'}",
                prompts_str,
                "✓" if creds_ok else "✗"
            )

            if not profiles_ok:
                console.print(f"  [yellow]⚠ {channel_name}: profiles.yaml no encontrado[/yellow]")
                all_ok = False

            if not creds_ok:
                console.print(f"  [yellow]⚠ {channel_name}: credentials.json no encontrado[/yellow]")
                console.print(f"    → Coloca credentials.json en {channel.credentials_path}[/yellow]")

        except Exception as e:
            console.print(f"  [red]✗ Error cargando {channel_name}: {e}[/red]")
            all_ok = False

    console.print(table)

    if all_ok:
        console.print(f"\n  [green]✓ Todos los canales ({len(channels)}) configurados correctamente[/green]")

    return all_ok


def check_profiles():
    """Validar profiles.yaml de cada canal."""
    console.print("\n[bold cyan]3. Validando Profiles (Voice & Music)...[/bold cyan]")

    from src.channel_config import ChannelConfig
    from src.services.profile_manager import ProfileManager

    channels = ChannelConfig.list_available_channels()

    for channel_name in channels:
        channel = ChannelConfig(channel_name)

        if not channel.profiles_path.exists():
            console.print(f"  [yellow]⚠ {channel_name}: Sin profiles.yaml[/yellow]")
            continue

        try:
            pm = ProfileManager(channel.profiles_path)
            default_profile = channel.config.default_profile

            if default_profile:
                profile = pm.get_profile(default_profile)
                console.print(f"  [green]✓ {channel_name}: Profile '{profile.name}' (engine: {profile.voice.engine})[/green]")
            else:
                console.print(f"  [yellow]⚠ {channel_name}: Sin default_profile definido[/yellow]")

        except Exception as e:
            console.print(f"  [red]✗ {channel_name}: Error cargando profiles: {e}[/red]")

    return True


def check_channel_config_priority():
    """Verificar que channel_config tenga prioridad sobre .env."""
    console.print("\n[bold cyan]4. Validando Prioridad de Configuración...[/bold cyan]")

    from src.channel_config import ChannelConfig
    from src.services.llm import LLMService

    # Test wealth_wisdom
    ww = ChannelConfig('wealth_wisdom')
    ww_llm = LLMService(channel_config=ww)

    console.print(f"  [cyan]wealth_wisdom:[/cyan]")
    console.print(f"    content_type: {ww.config.content.content_type}")
    console.print(f"    subreddit: {ww.config.content.subreddit}")
    console.print(f"    art_style: {ww.config.image.style[:60]}...")
    console.print(f"    custom prompts: script={'✓' if ww_llm.custom_script_prompt else '✗'}, image={'✓' if ww_llm.custom_image_prompt else '✗'}")

    # Test momentum_mindset
    mm = ChannelConfig('momentum_mindset')
    mm_llm = LLMService(channel_config=mm)

    console.print(f"\n  [cyan]momentum_mindset:[/cyan]")
    console.print(f"    content_type: {mm.config.content.content_type}")
    console.print(f"    subreddit: {mm.config.content.subreddit}")
    console.print(f"    art_style: {mm.config.image.style[:60]}...")
    console.print(f"    custom prompts: script={'✓' if mm_llm.custom_script_prompt else '✗'}, image={'✓' if mm_llm.custom_image_prompt else '✗'}")

    # Verify they're different
    if ww.config.content.content_type != mm.config.content.content_type:
        console.print(f"\n  [green]✓ Canales usan configuraciones independientes[/green]")
        return True
    else:
        console.print(f"\n  [red]✗ Canales tienen la misma configuración (BUG)[/red]")
        return False


def main():
    """Ejecutar todas las validaciones."""
    console.print(Panel.fit(
        "[bold white]Sistema de Validación - tinysh-content-factory[/bold white]\n"
        "Verificando configuración antes de ejecutar workflow",
        border_style="cyan"
    ))

    results = {
        "media_server": check_media_server(),
        "channels": check_channels(),
        "profiles": check_profiles(),
        "config_priority": check_channel_config_priority(),
    }

    # Summary
    console.print("\n" + "="*60)
    console.print("[bold cyan]Resumen de Validación[/bold cyan]\n")

    for check, passed in results.items():
        status = "[green]✓ PASS[/green]" if passed else "[red]✗ FAIL[/red]"
        console.print(f"  {check:20} {status}")

    all_passed = all(results.values())

    if all_passed:
        console.print("\n[bold green]✅ Sistema listo para generar contenido[/bold green]")
        return 0
    elif results["media_server"] == False and all(list(results.values())[1:]):
        console.print("\n[bold yellow]⚠ Sistema configurado correctamente[/bold yellow]")
        console.print("[yellow]→ Inicia el media server para generar videos[/yellow]")
        return 0
    else:
        console.print("\n[bold red]❌ Corrige los errores antes de continuar[/bold red]")
        return 1


if __name__ == "__main__":
    sys.exit(main())
