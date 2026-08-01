import argparse
import sys
from pathlib import Path
from getpass import getpass
from .image_lsb import encode, decode
from .tui import run_tui



def main():
    if len(sys.argv) == 1:
        run_tui()
        return

    parser = argparse.ArgumentParser(
        prog='stego',
        description='Hide and extract secret messages inside PNG images.',
        epilog='Run without arguments to launch interactive mode.'
    )
    subparsers = parser.add_subparsers(dest='command', required=True)

    encode_parser = subparsers.add_parser('encode', help='Hide a message in an image')
    encode_parser.add_argument('-i', '--image', required=True, help='Path to input PNG image')
    encode_parser.add_argument('-o', '--output', required=True, help='Path for output image (PNG)')
    msg_group = encode_parser.add_mutually_exclusive_group(required=True)
    msg_group.add_argument('-m', '--message', help='Text message to hide')
    msg_group.add_argument('-f', '--file', help='Read message from a text file')
    encode_parser.add_argument('-p', '--password', help='Password for encryption (optional)')

    decode_parser = subparsers.add_parser('decode', help='Extract a message from an image')
    decode_parser.add_argument('-i', '--image', required=True, help='Path to image with hidden data')
    decode_parser.add_argument('-p', '--password', help='Password for decryption (optional)')


    args = parser.parse_args()

    if args.command == 'encode':
        # Resolve password
        password = args.password
        if password is None:
            # Ask interactively if not supplied
            use_encrypt = input("Encrypt with password? (y/n): ").strip().lower()
            if use_encrypt == 'y':
                password = getpass("Password: ")
                confirm = getpass("Confirm password: ")
                if password != confirm:
                    print("Passwords do not match.")
                    sys.exit(1)
            else:
                password = None

        # Get message (as before)
        if args.message:
            message = args.message
        else:
            filepath = Path(args.file)
            if not filepath.is_file():
                print(f"Error: File '{args.file}' not found.")
                sys.exit(1)
            message = filepath.read_text(encoding='utf-8')

        image_path = Path(args.image)
        if not image_path.is_file():
            print(f"Error: Image '{args.image}' not found.")
            sys.exit(1)

        output_path = Path(args.output)

        try:
            encode(str(image_path), message, str(output_path), password)
            print(f"Message hidden successfully in {output_path}")
        except Exception as e:
            print(f"Encoding failed: {e}")
            sys.exit(1)


    elif args.command == 'decode':
        password = args.password
        if password is None:
            use_decrypt = input("Image was encrypted? (y/n): ").strip().lower()
            if use_decrypt == 'y':
                password = getpass("Password: ")
            else:
                password = None

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



if __name__ == '__main__':
    main()