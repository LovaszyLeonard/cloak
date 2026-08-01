import argparse
import sys
from pathlib import Path
from .image_lsb import encode, decode
from .carriers.audio import encode_audio, decode_audio
from .tui import run_tui


def main():
    if len(sys.argv) == 1:
        run_tui()
        return

    parser = argparse.ArgumentParser(
        prog='cloak',
        description='Hide and extract secret messages inside images and WAV audio files.',
        epilog='Run without arguments to launch interactive mode.'
    )

    subparsers = parser.add_subparsers(dest='command', required=True, help='Available commands')


    img_enc = subparsers.add_parser('encode', help='Hide a message in an image (PNG)')
    img_enc.add_argument('-i', '--image', required=True, help='Path to input PNG image')
    img_enc.add_argument('-o', '--output', required=True, help='Path for output PNG image')
    msg_group = img_enc.add_mutually_exclusive_group(required=True)
    msg_group.add_argument('-m', '--message', help='Text message to hide')
    msg_group.add_argument('-f', '--file', help='Read message from a text file')
    img_enc.add_argument('-p', '--password', help='Password for encryption (optional)')



    img_dec = subparsers.add_parser('decode', help='Extract a message from an image (PNG)')
    img_dec.add_argument('-i', '--image', required=True, help='Path to image with hidden data')
    img_dec.add_argument('-p', '--password', help='Password for decryption (optional)')



    aud_enc = subparsers.add_parser('audio-encode', help='Hide a message in a WAV audio file')
    aud_enc.add_argument('-i', '--input', required=True, help='Path to input WAV file')
    aud_enc.add_argument('-o', '--output', required=True, help='Path for output WAV file')
    msg_aud = aud_enc.add_mutually_exclusive_group(required=True)
    msg_aud.add_argument('-m', '--message', help='Text message to hide')
    msg_aud.add_argument('-f', '--file', help='Read message from a text file')
    aud_enc.add_argument('-p', '--password', help='Password for encryption (optional)')



    aud_dec = subparsers.add_parser('audio-decode', help='Extract a message from a WAV audio file')
    aud_dec.add_argument('-i', '--input', required=True, help='Path to WAV file with hidden data')
    aud_dec.add_argument('-p', '--password', help='Password for decryption (optional)')

    args = parser.parse_args()



    if args.command == 'encode':
        handle_encode(args)
    elif args.command == 'decode':
        handle_decode(args)
    elif args.command == 'audio-encode':
        handle_audio_encode(args)
    elif args.command == 'audio-decode':
        handle_audio_decode(args)


def _get_message(args):
    if args.message:
        return args.message
    else:
        filepath = Path(args.file)
        if not filepath.is_file():
            print(f"Error: File '{args.file}' not found.")
            sys.exit(1)
        return filepath.read_text(encoding='utf-8')


def handle_encode(args):
    password = args.password
    message = _get_message(args)

    image_path = Path(args.image)
    if not image_path.is_file():
        print(f"Error: Image '{args.image}' not found.")
        sys.exit(1)

    try:
        encode(str(image_path), message, str(args.output), password)
        print(f"Message hidden successfully in {args.output}")
    except Exception as e:
        print(f"Encoding failed: {e}")
        sys.exit(1)


def handle_decode(args):
    password = args.password
    image_path = Path(args.image)
    if not image_path.is_file():
        print(f"Error: Image '{args.image}' not found.")
        sys.exit(1)

    try:
        result = decode(str(image_path), password)
        print("Hidden message:")
        print(result)
    except Exception as e:
        print(f"Decoding failed: {e}")
        sys.exit(1)


def handle_audio_encode(args):
    password = args.password
    message = _get_message(args)

    input_path = Path(args.input)
    if not input_path.is_file():
        print(f"Error: Audio file '{args.input}' not found.")
        sys.exit(1)

    try:
        encode_audio(str(input_path), message, str(args.output), password)
        print(f"Message hidden successfully in {args.output}")
    except Exception as e:
        print(f"Encoding failed: {e}")
        sys.exit(1)


def handle_audio_decode(args):
    password = args.password
    input_path = Path(args.input)
    if not input_path.is_file():
        print(f"Error: Audio file '{args.input}' not found.")
        sys.exit(1)

    try:
        result = decode_audio(str(input_path), password)
        print("Hidden message:")
        print(result)
    except Exception as e:
        print(f"Decoding failed: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()