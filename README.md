# Cloak 🥷 – Modern Multi-Format Steganography

[![Run tests](https://github.com/LovaszyLeonard/cloak/actions/workflows/tests.yml/badge.svg)](https://github.com/LovaszyLeonard/cloak/actions/workflows/tests.yml)
[![Python Version](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13%20%7C%203.14-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code Style: Ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

**Cloak** is a high-performance steganography toolkit featuring both an interactive Terminal User Interface (TUI) and an automated CLI. It embeds arbitrary secret payloads (text messages or binary data) into lossless carrier media (**PNG** images and **WAV** audio) using Least Significant Bit (LSB) steganography, with optional military-grade **AES-256-GCM** authenticated encryption.

The resulting carrier files remain perceptual replicas of the originals, identical to the human eye and ear, while safely carrying encrypted payload streams.

---

## Table of Contents

- [Features](#features)
- [How It Works](#how-it-works)
- [Carrier Capacity Guide](#carrier-capacity-guide)
- [Installation](#installation)
  - [Prerequisites](#prerequisites)
  - [Setup](#setup)
  - [Building a Standalone Executable](#building-a-standalone-executable)
- [Usage](#usage)
  - [Interactive TUI Mode](#interactive-tui-mode)
  - [Command-Line Interface (CLI)](#command-line-interface-cli)
- [Security Architecture](#security-architecture)
- [Testing](#testing)
- [Troubleshooting](#troubleshooting)
- [Contributing & Roadmap](#contributing--roadmap)
- [License](#license)

---

## Features

- **Multi-Carrier LSB Engine**: Conceal data across RGB channels of lossless PNG images and PCM frame samples of uncompressed WAV audio.
- **Anti-Steganalysis Scattering**: Cryptographic pseudo-random bit scattering using a 4-round Feistel permutation with cycle walking. Modified bits are scattered across the entire carrier medium rather than clustered sequentially.
- **Transparent Compression**: Automatic Deflate compression reduces text and document footprints by up to 80% before encryption, multiplying effective carrier capacity.
- **Authenticated Encryption**: Robust **AES-256-GCM** encryption hardened with **PBKDF2-HMAC-SHA256** (600,000 iterations) to safeguard against brute-force attacks.
- **Tamper Detection**: Built-in GCM authentication tag verifies payload integrity and instantly flags any tampering or bit rot.
- **Dual Interfaces**:
  - **Interactive TUI**: Arrow-key menus, file-pickers, and real-time progress bars built with `questionary` and `rich`.
  - **Scriptable CLI**: Clean, exit-code-compliant interface designed for automation, scripts, and CI pipelines.
- **Zero Compression Artifacts**: Strict reliance on lossless formats ensures embedded payloads survive storage and playback intact.

---

## How It Works

```
                        [ Secret Message / File ]
                                    │
                        ┌───────────┴───────────┐
                        │   Password Provided?  │
                        └───────────┬───────────┘
                                    │
                    YES ┌───────────┴───────────┐ NO
                        ▼                       ▼
            [ AES-256-GCM Encryption ]     [ Raw UTF-8 Bytes ]
            (PBKDF2, Salt, Nonce, Tag)          │
                        │                       │
                        └───────────┬───────────┘
                                    │
                         [ 32-bit Length Header ]
                                    │
                                    ▼
                         [ Bitstream Serialization ]
                                    │
                ┌───────────────────┴───────────────────┐
                ▼                                       ▼
     PNG Image Carrier                       WAV Audio Carrier
  (LSB of R, G, B channels)              (LSB of 16-bit audio samples)
                │                                       │
                ▼                                       ▼
        [ Stego PNG File ]                      [ Stego WAV File ]
```

---

## Carrier Capacity Guide

Each byte/sample in the carrier stores **1 bit** of payload data in its least significant bit:

| Carrier Format | Carrier Element | Bits per Element | Capacity Formula | Example Capacity |
| :--- | :--- | :--- | :--- | :--- |
| **PNG (RGB)** | 1 pixel (3 bytes: R, G, B) | 3 bits | `(Width × Height × 3) / 8` bytes | 1920×1080 image $\approx$ **777 KB** payload |
| **WAV (16-bit)**| 1 audio sample (2 bytes) | 1 bit | `(Total Samples) / 8` bytes | 1 min CD audio (44.1kHz stereo) $\approx$ **661 KB** payload |

---

## Installation

### Prerequisites

- **Python 3.10+** installed on your system (`python3 --version` or `python --version`).

### Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/LovaszyLeonard/cloak.git
   cd cloak
   ```

2. **Create and activate a virtual environment**:
   * **Linux & macOS**:
     ```bash
     python3 -m venv venv
     source venv/bin/activate
     ```
     *(Note: If your Linux system does not have the `venv` module pre-installed, install it with your system package manager, e.g. `sudo apt install python3-venv` on Ubuntu/Debian).*
   * **Windows** (PowerShell / Command Prompt):
     ```powershell
     python -m venv venv
     venv\Scripts\activate
     ```

3. **Install dependencies and the `cloak` command**:
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   pip install -e .
   ```

> [!TIP]
> `pip install -e .` registers the `cloak` command directly into your terminal while the virtual environment is active. You can then run `cloak` from any directory.

### Building a Standalone Executable

To generate a standalone portable binary that runs without requiring Python:

```bash
pip install pyinstaller
pyinstaller --onefile --name cloak stego/__main__.py
```
The binary will be generated under the `dist/` directory (e.g. `dist/cloak`).

---

## Usage

### Interactive TUI Mode

Launch the interactive interface with rich visual styling and prompts by running `cloak` without arguments:

```bash
cloak
```

### Command-Line Interface (CLI)

#### Unified CLI Commands

`cloak` automatically detects carrier types (PNG vs WAV) so you can use `cloak encode` and `cloak decode` interchangeably for both media formats.

* **Inspect Carrier Media & Detect Hidden Payloads**:
  ```bash
  cloak info -i carrier.png
  # Or for audio:
  cloak info -i sample.wav
  ```

* **Hide a plain text message**:
  ```bash
  cloak encode -i input.png -m "Confidential project details" -o hidden.png
  cloak encode -i input.wav -m "Meeting coordinates" -o hidden.wav
  ```

* **Hide an encrypted message with AES-256-GCM & Pseudo-Random Scattering (`-s / --scatter`)**:
  ```bash
  cloak encode -i input.png -m "Top secret" -p "StrongPassword123" --scatter -o secret.png
  cloak encode -i input.wav -m "Top secret" -p "StrongPassword123" --scatter -o secret.wav
  ```

* **Embed an arbitrary file (Text, PDF, ZIP, Binary)**:
  ```bash
  cloak encode -i input.png -f document.pdf -p "StrongPassword123" --scatter -o secret.png
  ```

* **Decode / Reveal text message to console**:
  ```bash
  # Unencrypted:
  cloak decode -i hidden.png

  # Encrypted:
  cloak decode -i secret.png -p "StrongPassword123"
  ```

* **Extract payload directly to a file (`-O / --output-file`)**:
  ```bash
  cloak decode -i secret.png -p "StrongPassword123" -O extracted_document.pdf
  ```

---

## Security Architecture

- **Cipher**: AES-256 in Galois/Counter Mode (GCM).
- **Key Derivation Function**: PBKDF2-HMAC-SHA256 with **600,000 iterations**.
- **Cryptographic Randomness**: 16-byte cryptographically secure salt (`os.urandom(16)`) and 12-byte standard GCM nonce.
- **Integrity Verification**: AES-GCM includes an authentication tag in the ciphertext. Corrupted bits or incorrect passwords fail cleanly without leaking plaintext.
- **Steganographic Notice**: LSB steganography conceals the presence of data against visual and acoustic observation. High-assurance environments should account for statistical stegananalysis (e.g., sample pair analysis, Chi-square distribution tests).

---

## Testing

Run the automated test suite with `pytest`:

```bash
pytest -v
```

---

## Troubleshooting

### `Error: Unable to create directory '.../venv/bin/activate'`
This happens if `python -m venv` and `source` are typed on one line without separators:
```bash
# Incorrect:
python -m venv venv source venv/bin/activate

# Correct:
python3 -m venv venv
source venv/bin/activate
```

### `BuildBackendWarning: project.license as a TOML table is deprecated`
Ensure your `pyproject.toml` uses `license = "MIT"` (SPDX string) and `license-files = ["LICENSE"]` instead of the legacy `{text = "MIT"}` table.

---

## Contributing & Roadmap

See [cloak_production_roadmap.md](file:///home/leo/.gemini/antigravity/brain/41901155-7961-470a-9a91-909fa8c2c314/cloak_production_roadmap.md) for the detailed implementation roadmap:
- [x] Envelope framing with magic byte verification (`CLK1`).
- [x] Carrier auto-detection (unifying `encode` and `decode` across PNG and WAV).
- [x] Arbitrary binary file support (`.zip`, `.pdf`, `.bin`) and direct disk extraction (`-O`).
- [x] Carrier capacity inspection command (`cloak info`).
- [x] Fast zero-copy bitwise streaming engine.
- [x] Transparent Deflate payload compression.
- [x] Cryptographic pseudo-random bit scattering (Anti-Steganalysis).
- [ ] Visual difference map generator (`cloak diff`).
- [ ] Chi-square ($\chi^2$) statistical steganalysis detector (`cloak analyze`).

PRs and issues are welcome!

---

## License

Distributed under the [MIT License](file:///home/leo/Desktop/pr1/cloak/LICENSE). Copyright © 2026 Lovaszy Leonard.
