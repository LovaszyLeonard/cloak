import subprocess
import sys
import wave
from PIL import Image


def _create_test_wav(path, n_samples=20000):
    with wave.open(str(path), 'w') as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(22050)
        wav.writeframes(b'\x00' * (n_samples * 2))


def test_cli_image_roundtrip(tmp_path):
    sample = tmp_path / "sample.png"
    output = tmp_path / "hidden.png"
    Image.new('RGB', (100, 100), 'blue').save(sample)

    message = "CLI test message!"

    result = subprocess.run(
        [sys.executable, "-m", "stego", "encode",
         "-i", str(sample), "-m", message, "-o", str(output)],
        capture_output=True, text=True
    )
    assert result.returncode == 0
    assert "Message hidden successfully" in result.stdout

    result = subprocess.run(
        [sys.executable, "-m", "stego", "decode",
         "-i", str(output)],
        capture_output=True, text=True
    )
    assert result.returncode == 0
    assert message in result.stdout


def test_cli_unified_audio_encode_decode(tmp_path):
    """Test that cloak encode and decode work automatically on WAV files without needing audio-encode."""
    sample = tmp_path / "input.wav"
    output = tmp_path / "hidden.wav"
    _create_test_wav(sample)

    message = "Unified audio secret!"
    password = "clipassword"

    result = subprocess.run(
        [sys.executable, "-m", "stego", "encode",
         "-i", str(sample), "-m", message, "-o", str(output), "-p", password],
        capture_output=True, text=True
    )
    assert result.returncode == 0
    assert "Message hidden successfully" in result.stdout

    result = subprocess.run(
        [sys.executable, "-m", "stego", "decode",
         "-i", str(output), "-p", password],
        capture_output=True, text=True
    )
    assert result.returncode == 0
    assert message in result.stdout


def test_cli_audio_alias_subcommands(tmp_path):
    """Test backward compatibility with audio-encode and audio-decode subcommands."""
    sample = tmp_path / "input_alias.wav"
    output = tmp_path / "hidden_alias.wav"
    _create_test_wav(sample)

    message = "Alias command test!"

    result = subprocess.run(
        [sys.executable, "-m", "stego", "audio-encode",
         "-i", str(sample), "-m", message, "-o", str(output)],
        capture_output=True, text=True
    )
    assert result.returncode == 0

    result = subprocess.run(
        [sys.executable, "-m", "stego", "audio-decode",
         "-i", str(output)],
        capture_output=True, text=True
    )
    assert result.returncode == 0
    assert message in result.stdout


def test_cli_file_payload(tmp_path):
    sample = tmp_path / "carrier.png"
    output = tmp_path / "carrier_out.png"
    payload_file = tmp_path / "msg.txt"

    Image.new('RGB', (100, 100), 'cyan').save(sample)
    content = "Secret content from a text file!\nWith newlines."
    payload_file.write_text(content, encoding='utf-8')

    result = subprocess.run(
        [sys.executable, "-m", "stego", "encode",
         "-i", str(sample), "-f", str(payload_file), "-o", str(output)],
        capture_output=True, text=True
    )
    assert result.returncode == 0

    result = subprocess.run(
        [sys.executable, "-m", "stego", "decode",
         "-i", str(output)],
        capture_output=True, text=True
    )
    assert result.returncode == 0
    assert content in result.stdout


def test_cli_binary_payload_to_output_file(tmp_path):
    """Test embedding arbitrary binary file and extracting it directly with -O."""
    carrier = tmp_path / "image.png"
    stego_out = tmp_path / "stego_img.png"
    binary_input = tmp_path / "payload.bin"
    extracted_output = tmp_path / "extracted.bin"

    Image.new('RGB', (120, 120), 'green').save(carrier)
    # Binary bytes that would break simple UTF-8 decode
    raw_binary = bytes([0x00, 0xFF, 0xFE, 0xCA, 0xFE, 0xBA, 0xBE, 0x12, 0x34, 0x56]) * 20
    binary_input.write_bytes(raw_binary)

    # Encode with password
    res = subprocess.run(
        [sys.executable, "-m", "stego", "encode",
         "-i", str(carrier), "-f", str(binary_input), "-p", "bin_pass", "-o", str(stego_out)],
        capture_output=True, text=True
    )
    assert res.returncode == 0

    # Extract directly to file with -O
    res_dec = subprocess.run(
        [sys.executable, "-m", "stego", "decode",
         "-i", str(stego_out), "-p", "bin_pass", "-O", str(extracted_output)],
        capture_output=True, text=True
    )
    assert res_dec.returncode == 0
    assert "Extracted payload saved to" in res_dec.stdout
    assert extracted_output.read_bytes() == raw_binary


def test_cli_info_command(tmp_path):
    """Test cloak info output for image and audio carriers."""
    img = tmp_path / "inspect.png"
    Image.new('RGB', (100, 100), 'yellow').save(img)

    # 1. Info on pristine carrier
    res = subprocess.run(
        [sys.executable, "-m", "stego", "info", "-i", str(img)],
        capture_output=True, text=True
    )
    assert res.returncode == 0
    assert "IMAGE" in res.stdout
    assert "100 x 100 px" in res.stdout
    assert "None detected" in res.stdout

    # 2. Embed payload and inspect again
    stego = tmp_path / "inspect_stego.png"
    subprocess.run(
        [sys.executable, "-m", "stego", "encode",
         "-i", str(img), "-m", "Info payload", "-p", "pwd", "-o", str(stego)],
        check=True
    )

    res_stego = subprocess.run(
        [sys.executable, "-m", "stego", "info", "-i", str(stego)],
        capture_output=True, text=True
    )
    assert res_stego.returncode == 0
    assert "DETECTED" in res_stego.stdout
    assert "AES-256-GCM" in res_stego.stdout


def test_cli_scatter_flag(tmp_path):
    """Test CLI --scatter flag with encode, info and decode."""
    img = tmp_path / "scatter_in.png"
    out = tmp_path / "scatter_out.png"
    Image.new('RGB', (100, 100), 'purple').save(img)

    message = "CLI scattered message with compression!"
    password = "cli_scatter_pass"

    res_enc = subprocess.run(
        [sys.executable, "-m", "stego", "encode",
         "-i", str(img), "-m", message, "-p", password, "--scatter", "-o", str(out)],
        capture_output=True, text=True
    )
    assert res_enc.returncode == 0
    assert "Message hidden successfully" in res_enc.stdout

    # Info should report scattering and compression
    res_info = subprocess.run(
        [sys.executable, "-m", "stego", "info", "-i", str(out)],
        capture_output=True, text=True
    )
    assert res_info.returncode == 0
    assert "Pseudo-Random Scattering" in res_info.stdout

    # Decode without needing to specify --scatter (auto-detected)
    res_dec = subprocess.run(
        [sys.executable, "-m", "stego", "decode",
         "-i", str(out), "-p", password],
        capture_output=True, text=True
    )
    assert res_dec.returncode == 0
    assert message in res_dec.stdout
