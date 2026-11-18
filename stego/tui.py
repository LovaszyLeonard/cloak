"""Interactive Terminal User Interface (TUI) for Cloak with inline validation and robust UX."""

import sys
from collections.abc import Callable
from pathlib import Path

import questionary
from pyfiglet import Figlet
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress
from rich.table import Table

from .carriers import (
    decode_carrier_raw,
    encode_carrier,
    inspect_carrier,
)
from .envelope import FLAG_BINARY
from .exceptions import CloakError, PasswordRequiredError

console = Console()


def _format_bytes(num_bytes: int) -> str:
    if num_bytes < 1024:
        return f"{num_bytes} B"
    elif num_bytes < 1024 * 1024:
        return f"{num_bytes / 1024:.2f} KB ({num_bytes:,} bytes)"
    else:
        return f"{num_bytes / (1024 * 1024):.2f} MB ({num_bytes:,} bytes)"


# ----------------------------------------------------------------------
# Real-Time Inline Input Validators for Questionary Prompts
# ----------------------------------------------------------------------


def _make_existing_file_validator(
    file_label: str = "File",
    allowed_extensions: list[str] | None = None,
) -> Callable[[str], bool | str]:
    """Generate an inline validator ensuring the path points to an existing regular file."""

    def validator(text: str) -> bool | str:
        stripped = text.strip()
        if not stripped:
            return f"{file_label} path cannot be empty."

        path = Path(stripped).expanduser()
        if not path.exists():
            return f"{file_label} not found: '{stripped}'. Please check the path."
        if not path.is_file():
            return f"'{stripped}' is a directory, not a file."

        if allowed_extensions:
            ext = path.suffix.lower()
            if ext not in [e.lower() for e in allowed_extensions]:
                return f"{file_label} must have a valid extension: {', '.join(allowed_extensions)}"

        return True

    return validator


def _make_output_path_validator(default_ext: str | None = None) -> Callable[[str], bool | str]:
    """Validate destination file path and ensure parent directory exists."""

    def validator(text: str) -> bool | str:
        stripped = text.strip()
        if not stripped:
            return "Output path cannot be empty."

        path = Path(stripped).expanduser()
        if path.is_dir():
            return f"'{stripped}' is an existing directory. Please provide a file name."

        parent = path.parent
        if not parent.exists():
            return f"Parent directory does not exist: '{parent}'"

        if default_ext and path.suffix.lower() != default_ext.lower():
            # Allow user to proceed with warning or require extension
            pass

        return True

    return validator


def _validate_non_empty(text: str) -> bool | str:
    if not text.strip():
        return "Secret message cannot be empty."
    return True


# ----------------------------------------------------------------------
# TUI Visuals & Sub-Flows
# ----------------------------------------------------------------------


def show_banner():
    f = Figlet(font="slant")
    banner = f.renderText("Cloak")
    console.print(Panel(banner, style="bold cyan"))
    console.print("Multi-Format LSB Steganography Toolkit (PNG & WAV)\n", style="italic yellow")


def _get_payload_flow() -> tuple[str | bytes | None, bool, bool]:
    """Helper that returns (payload, is_binary, cancelled)."""
    source_choice = questionary.select(
        "Payload source:", choices=["Type text message directly", "Embed file (text or binary)"]
    ).ask()
    if source_choice is None:
        return None, False, True

    if source_choice == "Type text message directly":
        message = questionary.text(
            "Enter secret message:",
            validate=_validate_non_empty,
        ).ask()
        if message is None:
            return None, False, True
        return message, False, False
    else:
        file_path = questionary.path(
            "Select file to embed:",
            validate=_make_existing_file_validator("Payload file"),
        ).ask()
        if file_path is None:
            return None, False, True

        path = Path(file_path).expanduser()
        try:
            raw_bytes = path.read_bytes()
            if len(raw_bytes) == 0:
                console.print("[yellow]Warning: The selected file is 0 bytes (empty).[/yellow]")
            return raw_bytes, True, False
        except PermissionError:
            console.print(f"[red]Error: Permission denied reading '{file_path}'.[/red]")
            return None, False, True
        except Exception as e:
            console.print(f"[red]Could not read file: {e}[/red]")
            return None, False, True


def _get_password_flow(is_encoding: bool = True) -> tuple[str | None, bool]:
    """Interactive password prompt with confirmation loop and cancellation support."""
    prompt_text = "Encrypt with password?" if is_encoding else "Is the payload password-protected?"
    use_encryption = questionary.confirm(prompt_text, default=True if is_encoding else False).ask()
    if use_encryption is None:
        return None, True
    if not use_encryption:
        return None, False

    prompt_label = "Enter encryption password:" if is_encoding else "Enter decryption password:"
    while True:
        password = questionary.password(prompt_label).ask()
        if password is None:
            return None, True
        if not password:
            console.print("[red]Password cannot be empty. Please enter a valid password.[/red]")
            continue

        if is_encoding:
            confirm = questionary.password("Confirm password:").ask()
            if confirm is None:
                return None, True

            if confirm != password:
                console.print("[red]Passwords do not match. Please try again.[/red]")
                continue

        return password, False


def carrier_hide_flow(carrier_type_label: str = "Image (PNG)", allowed_exts: list[str] | None = None):
    console.print(f"\n[bold]HIDE IN {carrier_type_label.upper()}[/bold]\n")
    carrier_path = questionary.path(
        f"Select input {carrier_type_label}:",
        validate=_make_existing_file_validator(f"Carrier {carrier_type_label}", allowed_exts),
    ).ask()
    if carrier_path is None:
        return

    payload, is_binary, cancelled = _get_payload_flow()
    if cancelled:
        return

    password, cancelled = _get_password_flow(is_encoding=True)
    if cancelled:
        return

    scatter = questionary.confirm(
        "Enable pseudo-random bit scattering? (Anti-steganalysis)",
        default=True,
    ).ask()
    if scatter is None:
        return

    output_path = questionary.path(
        "Output path for carrier:",
        validate=_make_output_path_validator(),
    ).ask()
    if output_path is None:
        return

    try:
        with Progress() as progress:
            task = progress.add_task("[cyan]Embedding payload...", total=None)
            encode_carrier(
                str(Path(carrier_path).expanduser()),
                payload,
                str(Path(output_path).expanduser()),
                password,
                is_binary=is_binary,
                scatter=scatter,
            )
            progress.update(task, completed=True)
        console.print(Panel(f"Payload hidden successfully in [green]{output_path}[/green]", style="bold green"))
    except (CloakError, ValueError) as e:
        console.print(f"[red]Encoding failed: {e}[/red]")
    except Exception as e:
        console.print(f"[red]Unexpected error during encoding: {e}[/red]")


def carrier_reveal_flow(carrier_type_label: str = "Image (PNG)", allowed_exts: list[str] | None = None):
    console.print(f"\n[bold]REVEAL FROM {carrier_type_label.upper()}[/bold]\n")
    carrier_path = questionary.path(
        f"Select {carrier_type_label} with hidden data:",
        validate=_make_existing_file_validator(f"Carrier {carrier_type_label}", allowed_exts),
    ).ask()
    if carrier_path is None:
        return

    password, cancelled = _get_password_flow(is_encoding=False)
    if cancelled:
        return

    try:
        try:
            with Progress() as progress:
                task = progress.add_task("[cyan]Extracting payload...", total=None)
                flags, payload_bytes = decode_carrier_raw(
                    str(Path(carrier_path).expanduser()),
                    password,
                )
                progress.update(task, completed=True)
        except PasswordRequiredError:
            console.print("[yellow]Carrier contains an encrypted payload, but no password was entered.[/yellow]")
            retry_pw = questionary.password("Enter decryption password:").ask()
            if not retry_pw:
                return
            with Progress() as progress:
                task = progress.add_task("[cyan]Extracting payload...", total=None)
                flags, payload_bytes = decode_carrier_raw(
                    str(Path(carrier_path).expanduser()),
                    retry_pw,
                )
                progress.update(task, completed=True)

        is_binary = bool(flags & FLAG_BINARY)
        action = None
        if is_binary:
            console.print(f"[yellow]Carrier contains binary data ({_format_bytes(len(payload_bytes))}).[/yellow]")
            action = "Save to file"
        else:
            action = questionary.select(
                "How would you like to view the payload?", choices=["Display text on screen", "Save to file"]
            ).ask()

        if action == "Save to file":
            save_path = questionary.path(
                "Enter destination file path:",
                validate=_make_output_path_validator(),
            ).ask()
            if save_path:
                out_p = Path(save_path).expanduser()
                out_p.parent.mkdir(parents=True, exist_ok=True)
                out_p.write_bytes(payload_bytes)
                console.print(
                    Panel(
                        f"Saved {_format_bytes(len(payload_bytes))} to [green]{save_path}[/green]", style="bold green"
                    )
                )
        elif action == "Display text on screen":
            try:
                text_msg = payload_bytes.decode("utf-8")
                console.print(Panel(f"[bold]Hidden message:[/bold]\n\n{text_msg}", style="bold green"))
            except UnicodeDecodeError:
                console.print(
                    "[red]Payload contains binary data and cannot be displayed as UTF-8 text. Please save to a file.[/red]"
                )
    except (CloakError, ValueError) as e:
        console.print(f"[red]Decoding failed: {e}[/red]")
    except Exception as e:
        console.print(f"[red]Unexpected error during decoding: {e}[/red]")


def carrier_info_flow():
    console.print("\n[bold]INSPECT CARRIER MEDIA[/bold]\n")
    path_str = questionary.path(
        "Select image or audio file to inspect:",
        validate=_make_existing_file_validator("Carrier file", allowed_extensions=[".png", ".bmp", ".wav"]),
    ).ask()
    if path_str is None:
        return

    clean_path = str(Path(path_str).expanduser())
    try:
        info = inspect_carrier(clean_path)
    except Exception as e:
        console.print(f"[red]Could not inspect carrier: {e}[/red]")
        return

    table = Table(title=f"Carrier Analysis: {Path(clean_path).name}", show_header=True, header_style="bold cyan")
    table.add_column("Property", style="dim", width=24)
    table.add_column("Value", style="bold")

    table.add_row("Carrier Type", info["carrier_type"].upper())
    table.add_row("Format", info.get("format", "N/A"))
    table.add_row("File Size", _format_bytes(info["file_size"]))

    if info["carrier_type"] == "image":
        table.add_row("Dimensions", f"{info['width']} x {info['height']} px")
        table.add_row("Color Mode", info.get("mode", "RGB"))
    elif info["carrier_type"] == "audio":
        table.add_row("Channels", "Stereo" if info.get("channels") == 2 else "Mono")
        table.add_row("Sample Rate", f"{info.get('sample_rate')} Hz")
        table.add_row("Sample Width", f"{info.get('sample_width_bits')}-bit")
        mins = int(info.get("duration_seconds", 0) // 60)
        secs = info.get("duration_seconds", 0) % 60
        table.add_row("Duration", f"{mins:02d}:{secs:05.2f}")

    table.add_row("Maximum Capacity", _format_bytes(info["capacity_bytes"]))

    envelope = info.get("envelope", {})
    if envelope.get("detected"):
        table.add_row("Cloak Payload", "[green]DETECTED[/green]")
        table.add_row("Payload Version", f"v{envelope.get('version', 1)}")
        enc_str = "[yellow]AES-256-GCM[/yellow]" if envelope.get("is_encrypted") else "[cyan]Plaintext[/cyan]"
        table.add_row("Encryption", enc_str)
        comp_str = "[green]Zlib Deflate[/green]" if envelope.get("is_compressed") else "[dim]None[/dim]"
        table.add_row("Compression", comp_str)
        mode_str = "[magenta]Pseudo-Random Scattering[/magenta]" if envelope.get("is_scattered") else "Sequential LSB"
        table.add_row("Embedding Mode", mode_str)
        type_str = "Binary File" if envelope.get("is_binary") else "UTF-8 Text"
        table.add_row("Payload Type", type_str)
        p_len = envelope.get("payload_length", 0)
        cap = info["capacity_bytes"]
        pct = (p_len / cap * 100) if cap > 0 else 0
        table.add_row("Payload Size", f"{_format_bytes(p_len)} ({pct:.1f}% capacity used)")
        table.add_row("Integrity", "[red]CORRUPTED[/red]" if envelope.get("is_corrupted") else "[green]OK[/green]")
    else:
        table.add_row("Cloak Payload", "[dim]None detected[/dim]")

    console.print(table)


def run_tui():
    try:
        console.clear()
        show_banner()

        while True:
            action = questionary.select(
                "What would you like to do?",
                choices=[
                    "Hide payload in an image (PNG)",
                    "Reveal payload from an image (PNG)",
                    "Hide payload in audio (WAV)",
                    "Reveal payload from audio (WAV)",
                    "Inspect carrier media info & detect payloads",
                    "Exit",
                ],
            ).ask()

            if action == "Hide payload in an image (PNG)":
                carrier_hide_flow("Image (PNG)", allowed_exts=[".png", ".bmp"])
            elif action == "Reveal payload from an image (PNG)":
                carrier_reveal_flow("Image (PNG)", allowed_exts=[".png", ".bmp"])
            elif action == "Hide payload in audio (WAV)":
                carrier_hide_flow("Audio (WAV)", allowed_exts=[".wav"])
            elif action == "Reveal payload from audio (WAV)":
                carrier_reveal_flow("Audio (WAV)", allowed_exts=[".wav"])
            elif action == "Inspect carrier media info & detect payloads":
                carrier_info_flow()
            else:
                console.print("[yellow]Goodbye![/yellow]")
                sys.exit(0)
    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled. Goodbye![/yellow]")
        sys.exit(0)
