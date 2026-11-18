import argparse
import sys
from pathlib import Path

from rich.console import Console
from rich.table import Table

from .carriers import (
    decode_carrier,
    decode_carrier_to_file,
    encode_carrier,
    inspect_carrier,
)
from .exceptions import CloakError
from .tui import run_tui


def _format_bytes(num_bytes: int) -> str:
    if num_bytes < 1024:
        return f"{num_bytes} B"
    elif num_bytes < 1024 * 1024:
        return f"{num_bytes / 1024:.2f} KB ({num_bytes:,} bytes)"
    else:
        return f"{num_bytes / (1024 * 1024):.2f} MB ({num_bytes:,} bytes)"


def main():
    if len(sys.argv) == 1:
        run_tui()
        return

    parser = argparse.ArgumentParser(
        prog="cloak",
        description="Hide and extract secret messages and binary files inside PNG images and WAV audio files.",
        epilog="Run without arguments to launch interactive mode.",
    )

    subparsers = parser.add_subparsers(dest="command", required=True, help="Available commands")

    # Unified encode command
    enc_parser = subparsers.add_parser("encode", help="Hide a message or file in an image (PNG) or audio file (WAV)")
    enc_parser.add_argument("-i", "--input", "--image", dest="input", required=True, help="Path to input carrier file")
    enc_parser.add_argument("-o", "--output", required=True, help="Path for output carrier file")
    msg_group = enc_parser.add_mutually_exclusive_group(required=True)
    msg_group.add_argument("-m", "--message", help="Text message to hide")
    msg_group.add_argument("-f", "--file", help="Read message or binary payload from a file")
    enc_parser.add_argument("-p", "--password", help="Password for encryption (optional)")
    enc_parser.add_argument(
        "-s",
        "--scatter",
        action="store_true",
        help="Scatter payload bits pseudo-randomly across carrier (anti-steganalysis)",
    )
    enc_parser.add_argument(
        "--no-compress",
        dest="compress",
        action="store_false",
        default=True,
        help="Disable automatic payload compression",
    )

    # Unified decode command
    dec_parser = subparsers.add_parser("decode", help="Extract a message or file from a PNG image or WAV audio file")
    dec_parser.add_argument(
        "-i", "--input", "--image", dest="input", required=True, help="Path to carrier file with hidden data"
    )
    dec_parser.add_argument("-p", "--password", help="Password for decryption (optional)")
    dec_parser.add_argument(
        "-O", "--output-file", "-o", dest="output_file", help="Save extracted payload directly to a file"
    )

    # Info / inspection command
    info_parser = subparsers.add_parser("info", help="Inspect carrier metadata, capacity, and detect hidden payloads")
    info_parser.add_argument(
        "-i", "--input", "--image", dest="input", required=True, help="Path to carrier file to inspect"
    )

    # Backward compatibility subcommands
    aud_enc = subparsers.add_parser("audio-encode", help="Hide a message in a WAV audio file (alias)")
    aud_enc.add_argument("-i", "--input", required=True, help="Path to input WAV file")
    aud_enc.add_argument("-o", "--output", required=True, help="Path for output WAV file")
    msg_aud = aud_enc.add_mutually_exclusive_group(required=True)
    msg_aud.add_argument("-m", "--message", help="Text message to hide")
    msg_aud.add_argument("-f", "--file", help="Read message or binary payload from a file")
    aud_enc.add_argument("-p", "--password", help="Password for encryption (optional)")
    aud_enc.add_argument(
        "-s",
        "--scatter",
        action="store_true",
        help="Scatter payload bits pseudo-randomly across carrier (anti-steganalysis)",
    )
    aud_enc.add_argument(
        "--no-compress",
        dest="compress",
        action="store_false",
        default=True,
        help="Disable automatic payload compression",
    )

    aud_dec = subparsers.add_parser("audio-decode", help="Extract a message from a WAV audio file (alias)")
    aud_dec.add_argument("-i", "--input", required=True, help="Path to WAV file with hidden data")
    aud_dec.add_argument("-p", "--password", help="Password for decryption (optional)")
    aud_dec.add_argument(
        "-O", "--output-file", "-o", dest="output_file", help="Save extracted payload directly to a file"
    )

    args = parser.parse_args()

    if args.command in ("encode", "audio-encode"):
        handle_encode(args)
    elif args.command in ("decode", "audio-decode"):
        handle_decode(args)
    elif args.command == "info":
        handle_info(args)


def _get_payload(args) -> tuple[str | bytes, bool]:
    if args.message is not None:
        return args.message, False
    else:
        filepath = Path(args.file).expanduser()
        if not filepath.exists():
            print(f"Error: Payload file '{args.file}' not found.", file=sys.stderr)
            sys.exit(1)
        if not filepath.is_file():
            print(f"Error: Path '{args.file}' is a directory, not a regular file.", file=sys.stderr)
            sys.exit(1)
        try:
            raw = filepath.read_bytes()
            return raw, True
        except PermissionError:
            print(f"Error: Permission denied reading '{args.file}'.", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"Error reading file '{args.file}': {e}", file=sys.stderr)
            sys.exit(1)


def handle_encode(args):
    carrier_path = Path(args.input).expanduser()
    if not carrier_path.exists():
        print(f"Error: Carrier file '{args.input}' not found.", file=sys.stderr)
        sys.exit(1)
    if not carrier_path.is_file():
        print(f"Error: Carrier path '{args.input}' is a directory, not a regular file.", file=sys.stderr)
        sys.exit(1)

    payload, is_binary = _get_payload(args)
    password = args.password
    scatter = getattr(args, "scatter", False)
    compress = getattr(args, "compress", True)

    try:
        encode_carrier(
            str(carrier_path),
            payload,
            str(Path(args.output).expanduser()),
            password,
            is_binary=is_binary,
            scatter=scatter,
            compress=compress,
        )
        print(f"Message hidden successfully in {args.output}")
    except (CloakError, ValueError) as e:
        print(f"Encoding failed: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error during encoding: {e}", file=sys.stderr)
        sys.exit(1)


def handle_decode(args):
    carrier_path = Path(args.input).expanduser()
    if not carrier_path.exists():
        print(f"Error: Carrier file '{args.input}' not found.", file=sys.stderr)
        sys.exit(1)
    if not carrier_path.is_file():
        print(f"Error: Carrier path '{args.input}' is a directory, not a regular file.", file=sys.stderr)
        sys.exit(1)

    password = args.password

    if getattr(args, "output_file", None):
        try:
            bytes_written = decode_carrier_to_file(
                str(carrier_path),
                str(Path(args.output_file).expanduser()),
                password,
            )
            print(f"Extracted payload saved to {args.output_file} ({_format_bytes(bytes_written)})")
        except (CloakError, ValueError) as e:
            print(f"Decoding failed: {e}", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"Unexpected error during decoding: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        try:
            result = decode_carrier(str(carrier_path), password)
            print("Hidden message:")
            print(result)
        except (CloakError, ValueError) as e:
            print(f"Decoding failed: {e}", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"Unexpected error during decoding: {e}", file=sys.stderr)
            sys.exit(1)


def handle_info(args):
    carrier_path = Path(args.input).expanduser()
    if not carrier_path.exists():
        print(f"Error: Carrier file '{args.input}' not found.", file=sys.stderr)
        sys.exit(1)
    if not carrier_path.is_file():
        print(f"Error: Carrier path '{args.input}' is a directory, not a regular file.", file=sys.stderr)
        sys.exit(1)

    try:
        info = inspect_carrier(str(carrier_path))
    except (CloakError, ValueError) as e:
        print(f"Inspection failed: {e}", file=sys.stderr)
        sys.exit(1)

    console = Console()
    table = Table(title=f"Carrier Analysis: {carrier_path.name}", show_header=True, header_style="bold cyan")
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


if __name__ == "__main__":
    main()
