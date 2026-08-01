import sys
from pathlib import Path
import questionary
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress
from pyfiglet import Figlet
from .image_lsb import encode, decode

console = Console()

def show_banner():
    f = Figlet(font='slant')
    banner = f.renderText('Cloak')
    console.print(Panel(banner, style="bold cyan"))
    console.print("Hide secret messages inside images\n", style="italic yellow")


def hide_flow():
    console.print("\n[bold]HIDE A MESSAGE[/bold]\n")

    image_path = questionary.path("Select input image (PNG):").ask()
    if image_path is None:
        return

    if not Path(image_path).is_file():
        console.print("[red]File not found.[/red]")
        return

    source_choice = questionary.select(
        "Message source:",
        choices=["Type directly", "Read from file"]
    ).ask()

    if source_choice is None:
        return

    if source_choice == "Type directly":
        message = questionary.text("Enter secret message:").ask()
        if message is None:
            return
    else:
        file_path = questionary.path("Select text file:").ask()
        if file_path is None:
            return
        try:
            message = Path(file_path).read_text(encoding='utf-8')
        except Exception as e:
            console.print(f"[red]Could not read file: {e}[/red]")
            return

    use_encryption = questionary.confirm("Encrypt with password?").ask()
    if use_encryption is None:
        return
    password = None
    if use_encryption:
        password = questionary.password("Enter password:").ask()
        if password is None:
            return
        confirm = questionary.password("Confirm password:").ask()
        if confirm != password:
            console.print("[red]Passwords do not match.[/red]")
            return

    output_path = questionary.path("Output image path (PNG):").ask()
    if output_path is None:
        return

    try:
        with Progress() as progress:
            task = progress.add_task("[cyan]Embedding...", total=None)
            encode(str(image_path), message, str(output_path), password)   # <-- password passed
            progress.update(task, completed=True)
        console.print(Panel(f"Message hidden in [green]{output_path}[/green]", style="bold green"))
    except Exception as e:
        console.print(f"[red]Encoding failed: {e}[/red]")


def reveal_flow():
    console.print("\n[bold]REVEAL A MESSAGE[/bold]\n")

    image_path = questionary.path("Select image with hidden data:").ask()
    if image_path is None:
        return

    if not Path(image_path).is_file():
        console.print("[red]File not found.[/red]")
        return

    has_encryption = questionary.confirm("Is the hidden data encrypted?").ask()
    if has_encryption is None:
        return
    password = None
    if has_encryption:
        password = questionary.password("Enter password:").ask()
        if password is None:
            return

    try:
        with Progress() as progress:
            task = progress.add_task("[cyan]Extracting...", total=None)
            message = decode(str(image_path), password)   # <-- password passed
            progress.update(task, completed=True)
        console.print(Panel(f"[bold]Hidden message:[/bold]\n\n{message}", style="bold green"))
    except Exception as e:
        console.print(f"[red]Decoding failed: {e}[/red]")



def run_tui():
    console.clear()
    show_banner()

    while True:
        action = questionary.select(
            "What would you like to do?",
            choices=["Hide a message", "Reveal a message", "Exit"]
        ).ask()

        if action == "Hide a message":
            hide_flow()
        elif action == "Reveal a message":
            reveal_flow()
        else:
            console.print("[yellow]Goodbye![/yellow]")
            sys.exit(0)