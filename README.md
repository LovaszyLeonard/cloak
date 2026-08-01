# 🔐 Cloak – Steganography Tool

Hide encrypted messages inside PNG images. The output looks visually identical to the original image while carrying AES-256-GCM encrypted payload data embedded directly into the least significant bits (LSB).

## Features

- LSB Steganography: Embeds data seamlessly into lossless PNG images.
- Strong Encryption: Robust AES-256-GCM authenticated encryption (optional).
- Interactive TUI: User-friendly terminal interface featuring arrow-key navigation.
- Scriptable CLI: Full command-line interface support for automated workflows.
- Lightweight Dependencies: Built using Python standard libraries and lightweight trusted packages.


## Installation

### From Source

git clone https://github.com/LovaszyLeonard/cloak.git
cd stego-tool

python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

pip install -r requirements.txt
pip install -e .

### Standalone Executable (Optional)

Build a single executable that runs without requiring a local Python environment:

pip install pyinstaller
pyinstaller --onefile --name cloak stego/__main__.py

The compiled binary will be located in the dist/ directory.

## Usage

### Interactive Mode

Simply launch the tool to open the interactive TUI:

cloak

### Command-Line Mode

Hide a plain text message:
cloak encode -i input.png -m "secret message" -o hidden.png
cloak decode -i hidden.png

Hide an encrypted message:
cloak encode -i input.png -m "top secret" -o secret.png -p mypassword
cloak decode -i secret.png -p mypassword

Embed content from a file:
cloak encode -i input.png -f message.txt -o hidden.png

## How It Works

1. Encryption: Payload data is optionally encrypted using AES-256-GCM, with secret key derivation handled via PBKDF2.
2. Embedding: The encrypted binary stream is inserted into the least significant bits (LSB) of the image's RGB color channels.
3. Lossless Preservation: The image is saved strictly in lossless PNG format to guarantee data integrity.
4. Extraction: The decoding process reverses these steps. Without the correct decryption key, embedded payloads remain indistinguishable from statistical image noise.

## Security Considerations

- Implements 600,000 PBKDF2 iterations for key derivation combined with AES-256-GCM.
- The GCM authentication tag guarantees detection of payload tampering or corruption.
- Note: Steganography hides data presence but is not a substitute for standard security practices under high-threat environments, as advanced statistical analysis (chi-square tests) may reveal LSB anomalies.

## Testing

Run the test suite via Pytest:

pytest

## License

Distributed under the MIT License.