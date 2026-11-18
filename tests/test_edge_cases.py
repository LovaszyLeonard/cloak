"""Comprehensive test suite for edge cases, boundary conditions, and error recovery."""

import wave

import pytest
from PIL import Image

from stego.carriers import (
    decode_carrier,
    decode_carrier_raw,
    detect_carrier_type,
    encode_carrier,
    get_capacity,
    inspect_carrier,
)
from stego.exceptions import (
    CapacityError,
    CorruptedPayloadError,
    DecryptionError,
    PayloadNotFoundError,
    UnsupportedCarrierError,
)


def _create_image(path, width=80, height=80, color="blue"):
    Image.new("RGB", (width, height), color=color).save(path)


def _create_wav(path, n_samples=20000, sampwidth=2, framerate=22050):
    with wave.open(str(path), "w") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(sampwidth)
        wav.setframerate(framerate)
        wav.writeframes(b"\x00" * (n_samples * sampwidth))


# ----------------------------------------------------------------------
# 1. Zero-byte / Empty Payload Tests
# ----------------------------------------------------------------------


def test_zero_byte_empty_string_image(tmp_path):
    img = tmp_path / "img.png"
    out = tmp_path / "out.png"
    _create_image(img)

    encode_carrier(img, "", out)
    assert decode_carrier(out) == ""


def test_zero_byte_empty_string_encrypted_image(tmp_path):
    img = tmp_path / "img.png"
    out = tmp_path / "out.png"
    _create_image(img)

    encode_carrier(img, "", out, password="pass")
    assert decode_carrier(out, password="pass") == ""


def test_zero_byte_binary_payload(tmp_path):
    img = tmp_path / "img.png"
    out = tmp_path / "out.png"
    _create_image(img)

    encode_carrier(img, b"", out, is_binary=True)
    flags, raw = decode_carrier_raw(out)
    assert raw == b""


def test_zero_byte_audio(tmp_path):
    wav = tmp_path / "audio.wav"
    out = tmp_path / "out.wav"
    _create_wav(wav)

    encode_carrier(wav, "", out)
    assert decode_carrier(out) == ""


# ----------------------------------------------------------------------
# 2. Non-ASCII & Multilingual Unicode Tests
# ----------------------------------------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        "Hello 🥷 Stego 🚀!",
        "你好世界，这是一个隐藏的信息。",
        "مرحبا بالعالم - رسالة سرية مشفرة",
        "Привет, мир! Секретное сообщение.",
        "こんにちは世界！暗号化された秘密のメッセージ。",
        "Γειά σου κόσμε! Μυστικό μήνυμα.",
        "Grüße aus München: Ä, Ö, Ü, ß!",
    ],
)
def test_unicode_multilingual_roundtrip(tmp_path, text):
    img = tmp_path / f"img_{hash(text)}.png"
    out = tmp_path / f"out_{hash(text)}.png"
    _create_image(img, width=100, height=100)

    encode_carrier(img, text, out, password="unicode_pass")
    extracted = decode_carrier(out, password="unicode_pass")
    assert extracted == text


# ----------------------------------------------------------------------
# 3. Exact Capacity Boundaries
# ----------------------------------------------------------------------


def test_exact_capacity_boundary(tmp_path):
    """Test filling the carrier to 100% capacity and exceeding by exactly 1 byte."""
    img = tmp_path / "boundary.png"
    out = tmp_path / "boundary_out.png"
    _create_image(img, width=20, height=20)  # 400 pixels * 3 = 1200 bytes => 150 bytes capacity => 141 payload max

    cap = get_capacity(img)
    assert cap > 0

    # 1. Exact maximum payload should succeed (without compression)
    exact_payload = "X" * cap
    encode_carrier(img, exact_payload, out, compress=False)
    assert decode_carrier(out) == exact_payload

    # 2. Exactly 1 byte over capacity should raise CapacityError (when uncompressed)
    overflow_payload = "X" * (cap + 1)
    with pytest.raises(CapacityError):
        encode_carrier(img, overflow_payload, out, compress=False)


# ----------------------------------------------------------------------
# 4. Header & Payload Tampering / Corruption
# ----------------------------------------------------------------------


def test_tampered_magic_signature_raises_payload_not_found(tmp_path):
    img = tmp_path / "carrier.png"
    out = tmp_path / "tampered.png"
    _create_image(img)

    encode_carrier(img, "Secret payload", out)

    # Corrupt the first pixel's red LSB (which contains bit 7 of the 'C' in 'CLK')
    with Image.open(out) as im:
        raw = bytearray(im.convert("RGB").tobytes())
    raw[0] ^= 1  # flip the first bit of the magic signature
    tampered_im = Image.frombytes("RGB", (80, 80), bytes(raw))
    tampered_im.save(out)

    with pytest.raises(PayloadNotFoundError):
        decode_carrier(out)


def test_corrupted_length_exceeding_carrier_raises_corrupted_payload(tmp_path):
    img = tmp_path / "carrier.png"
    out = tmp_path / "bad_len.png"
    _create_image(img, width=30, height=30)

    encode_carrier(img, "test", out)

    # Infiltrate the length field: bytes 5..8 of envelope correspond to carrier bytes 40..71
    with Image.open(out) as im:
        raw = bytearray(im.convert("RGB").tobytes())
    # Set the MSB of the length header to 1 (claiming 2GB payload)
    raw[40] = (raw[40] & 0xFE) | 1

    tampered_im = Image.frombytes("RGB", (30, 30), bytes(raw))
    tampered_im.save(out)

    with pytest.raises(CorruptedPayloadError):
        decode_carrier(out)


def test_ciphertext_tampering_fails_gcm_auth_tag(tmp_path):
    img = tmp_path / "carrier.png"
    out = tmp_path / "tampered_cipher.png"
    _create_image(img)

    encode_carrier(img, "Original authentic message", out, password="mypassword")

    # Flip 1 bit in the ciphertext region (after 9 envelope bytes * 8 = 72 bits)
    with Image.open(out) as im:
        raw = bytearray(im.convert("RGB").tobytes())
    raw[120] ^= 1  # flip a bit in ciphertext

    tampered_im = Image.frombytes("RGB", (80, 80), bytes(raw))
    tampered_im.save(out)

    with pytest.raises(DecryptionError):
        decode_carrier(out, password="mypassword")


# ----------------------------------------------------------------------
# 5. Unsupported Formats & Non-existent Files
# ----------------------------------------------------------------------


def test_detect_carrier_type_non_existent():
    with pytest.raises(FileNotFoundError):
        detect_carrier_type("non_existent_file_12345.png")


def test_unsupported_carrier_format(tmp_path):
    text_file = tmp_path / "test.txt"
    text_file.write_text("Hello world")

    with pytest.raises(UnsupportedCarrierError):
        detect_carrier_type(text_file)

    with pytest.raises(UnsupportedCarrierError):
        inspect_carrier(text_file)


# ----------------------------------------------------------------------
# 6. Carrier Inspection Diagnostics
# ----------------------------------------------------------------------


def test_inspect_carrier_diagnostics(tmp_path):
    wav = tmp_path / "test.wav"
    out_wav = tmp_path / "stego.wav"
    _create_wav(wav, n_samples=16000)

    # Pristine audio
    info_clean = inspect_carrier(wav)
    assert info_clean["carrier_type"] == "audio"
    assert info_clean["format"] == "WAV"
    assert info_clean["envelope"]["detected"] is False

    # Audio with payload
    encode_carrier(wav, "Audio secret", out_wav, password="wavpwd")
    info_stego = inspect_carrier(out_wav)
    assert info_stego["envelope"]["detected"] is True
    assert info_stego["envelope"]["is_encrypted"] is True
    assert info_stego["envelope"]["is_corrupted"] is False


# ----------------------------------------------------------------------
# 7. Transparent Compression & Pseudo-Random Scattering Tests
# ----------------------------------------------------------------------


def test_transparent_compression_roundtrip(tmp_path):
    img = tmp_path / "comp_carrier.png"
    out = tmp_path / "comp_out.png"
    _create_image(img, width=120, height=120)

    # Repetitive payload that compresses significantly
    long_text = "Highly compressible secret message block! " * 30
    encode_carrier(img, long_text, out, compress=True)

    info = inspect_carrier(out)
    assert info["envelope"]["is_compressed"] is True

    extracted = decode_carrier(out)
    assert extracted == long_text


def test_scattered_embedding_image_roundtrip(tmp_path):
    img = tmp_path / "scatter_carrier.png"
    out = tmp_path / "scatter_out.png"
    _create_image(img, width=100, height=100)

    message = "Secret scattered across pixels pseudo-randomly!"
    password = "scatter_pass_123"

    encode_carrier(img, message, out, password=password, scatter=True)

    info = inspect_carrier(out)
    assert info["envelope"]["is_scattered"] is True
    assert info["envelope"]["is_encrypted"] is True

    # Correct password succeeds
    extracted = decode_carrier(out, password=password)
    assert extracted == message

    # Wrong password fails GCM verification
    with pytest.raises(DecryptionError):
        decode_carrier(out, password="wrong_password")


def test_scattered_embedding_audio_roundtrip(tmp_path):
    wav = tmp_path / "scatter_audio.wav"
    out = tmp_path / "scatter_out.wav"
    _create_wav(wav, n_samples=25000)

    message = "Audio scattered secret payload!"
    password = "audio_scatter_pwd"

    encode_carrier(wav, message, out, password=password, scatter=True)

    info = inspect_carrier(out)
    assert info["envelope"]["is_scattered"] is True

    extracted = decode_carrier(out, password=password)
    assert extracted == message


def test_combined_compression_and_scattering(tmp_path):
    img = tmp_path / "both_carrier.png"
    out = tmp_path / "both_out.png"
    _create_image(img, width=100, height=100)

    message = "Steganography stealth + compression: " + ("Repeat " * 25)
    password = "both_pwd"

    encode_carrier(img, message, out, password=password, scatter=True, compress=True)

    info = inspect_carrier(out)
    assert info["envelope"]["is_scattered"] is True
    assert info["envelope"]["is_compressed"] is True

    extracted = decode_carrier(out, password=password)
    assert extracted == message


def test_decode_to_file_rejects_directory_destination(tmp_path):
    from stego.carriers import decode_carrier_to_file

    img = tmp_path / "carrier.png"
    out = tmp_path / "stego.png"
    _create_image(img)
    encode_carrier(img, b"binary secret data", out, is_binary=True)

    dest_dir = tmp_path / "somedir"
    dest_dir.mkdir()

    with pytest.raises(ValueError, match="is an existing directory"):
        decode_carrier_to_file(out, dest_dir)


def test_extract_bytes_truncated_buffer_raises_cleanly():
    from stego.envelope import extract_bytes

    # 5 bytes needed = 40 elements, but only provide 10
    short_buffer = bytearray(10)
    with pytest.raises(CorruptedPayloadError, match="Carrier buffer truncated"):
        extract_bytes(short_buffer, num_bytes=5)


def test_peek_envelope_on_tiny_buffer_does_not_crash():
    from stego.envelope import peek_envelope

    tiny_buffer = bytearray([0] * 5)
    info = peek_envelope(tiny_buffer, total_capacity_bytes=10)
    assert info["detected"] is False
    assert "too small" in info["reason"]
