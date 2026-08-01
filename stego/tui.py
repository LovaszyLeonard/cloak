import sys
from pathlib import Path
import questionary
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress
from pyfiglet import Figlet
from .image_lsb import encode, decode
from .carriers.audio import encode_audio, decode_audio

console = Console()

def show_banner():
    f = Figlet(font='slant')
    banner = f.renderText('Cloak')
    console.print(Panel(banner, style="bold cyan"))
    console.print("Hide secret messages inside images or WAV audio files\n", style="italic yellow")


def _get_message_flow():
    """Helper that returns (message, cancelled?)"""
    source_choice = questionary.select(
        "Message source:",
        choices=["Type directly", "Read from file"]
    ).ask()
    if source_choice is None:
        return None, True

    if source_choice == "Type directly":
        message = questionary.text("Enter secret message:").ask()
        if message is None:
            return None, True
        return message, False
    else:
        file_path = questionary.path("Select text file:").ask()
        if file_path is None:
            return None, True
        try:
            message = Path(file_path).read_text(encoding='utf-8')
            return message, False
        except Exception as e:
            console.print(f"[red]Could not read file: {e}[/red]")
            return None, True


def _get_password_flow():
    """Returns (password, cancelled?)"""
    use_encryption = questionary.confirm("Encrypt with password?").ask()
    if use_encryption is None:
        return None, True
    if not use_encryption:
        return None, False

    password = questionary.password("Enter password:").ask()
    if password is None:
        return None, True
    confirm = questionary.password("Confirm password:").ask()
    if confirm != password:
        console.print("[red]Passwords do not match.[/red]")
        return None, True
    return password, False


def _check_file(path_str, file_type="file"):
    if not Path(path_str).is_file():
        console.print(f"[red]{file_type} not found: {path_str}[/red]")
        return False
    return True


def image_hide_flow():
    console.print("\n[bold]HIDE IN IMAGE[/bold]\n")
    image_path = questionary.path("Select input image (PNG):").ask()
    if image_path is None or not _check_file(image_path, "Image"):
        return

    message, cancelled = _get_message_flow()
    if cancelled:
        return

    password, cancelled = _get_password_flow()
    if cancelled:
        return

    output_path = questionary.path("Output image path (PNG):").ask()
    if output_path is None:
        return

    try:
        with Progress() as progress:
            task = progress.add_task("[cyan]Embedding...", total=None)
            encode(str(image_path), message, str(output_path), password)
            progress.update(task, completed=True)
        console.print(Panel(f"Message hidden in [green]{output_path}[/green]", style="bold green"))
    except Exception as e:
        console.print(f"[red]Encoding failed: {e}[/red]")


def image_reveal_flow():
    console.print("\n[bold]REVEAL FROM IMAGE[/bold]\n")
    image_path = questionary.path("Select image with hidden data (PNG):").ask()
    if image_path is None or not _check_file(image_path, "Image"):
        return

    password, cancelled = _get_password_flow()
    if cancelled:
        return

    try:
        with Progress() as progress:
            task = progress.add_task("[cyan]Extracting...", total=None)
            message = decode(str(image_path), password)
            progress.update(task, completed=True)
        console.print(Panel(f"[bold]Hidden message:[/bold]\n\n{message}", style="bold green"))
    except Exception as e:
        console.print(f"[red]Decoding failed: {e}[/red]")


def audio_hide_flow():
    console.print("\n[bold]HIDE IN AUDIO[/bold]\n")
    audio_path = questionary.path("Select input WAV file:").ask()
    if audio_path is None or not _check_file(audio_path, "Audio file"):
        return

    message, cancelled = _get_message_flow()
    if cancelled:
        return

    password, cancelled = _get_password_flow()
    if cancelled:
        return

    output_path = questionary.path("Output WAV path:").ask()
    if output_path is None:
        return

    try:
        with Progress() as progress:
            task = progress.add_task("[cyan]Embedding...", total=None)
            encode_audio(str(audio_path), message, str(output_path), password)
            progress.update(task, completed=True)
        console.print(Panel(f"Message hidden in [green]{output_path}[/green]", style="bold green"))
    except Exception as e:
        console.print(f"[red]Encoding failed: {e}[/red]")


def audio_reveal_flow():
    console.print("\n[bold]REVEAL FROM AUDIO[/bold]\n")
    audio_path = questionary.path("Select WAV file with hidden data:").ask()
    if audio_path is None or not _check_file(audio_path, "Audio file"):
        return

    password, cancelled = _get_password_flow()
    if cancelled:
        return

    try:
        with Progress() as progress:
            task = progress.add_task("[cyan]Extracting...", total=None)
            message = decode_audio(str(audio_path), password)
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
            choices=[
                "Hide a message in an image",
                "Reveal a message from an image",
                "Hide a message in audio",
                "Reveal a message from audio",
                "Exit"
            ]
        ).ask()

        if action == "Hide a message in an image":
            image_hide_flow()
        elif action == "Reveal a message from an image":
            image_reveal_flow()
        elif action == "Hide a message in audio":
            audio_hide_flow()
        elif action == "Reveal a message from audio":
            audio_reveal_flow()
        else:
            console.print("[yellow]Goodbye![/yellow]")
            sys.exit(0)