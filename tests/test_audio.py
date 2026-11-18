import wave
import pytest
from stego.carriers.audio import encode_audio, decode_audio, get_audio_capacity
from stego.exceptions import (
    CapacityError,
    DecryptionError,
    PasswordRequiredError,
    PayloadNotFoundError,
    UnsupportedCarrierError,
)


def _create_wav(path, n_samples=22050, sampwidth=2, framerate=22050):
    with wave.open(str(path), 'w') as wav:
        wav.setnchannels(1)
        wav.setsampwidth(sampwidth)
        wav.setframerate(framerate)
        wav.writeframes(b'\x00' * (n_samples * sampwidth))


def test_audio_roundtrip(tmp_path):
    sample = tmp_path / "silence.wav"
    output = tmp_path / "hidden.wav"
    _create_wav(sample, n_samples=20000)

    message = "Hello WAV steganography!"
    encode_audio(str(sample), message, str(output))
    extracted = decode_audio(str(output))
    assert extracted == message


def test_audio_encryption(tmp_path):
    sample = tmp_path / "enc_silence.wav"
    output = tmp_path / "enc_hidden.wav"
    _create_wav(sample, n_samples=20000)

    msg = "Top secret audio payload!"
    pwd = "audio_strong_pass"
    encode_audio(str(sample), msg, str(output), password=pwd)
    extracted = decode_audio(str(output), password=pwd)
    assert extracted == msg


def test_audio_wrong_password_fails(tmp_path):
    sample = tmp_path / "fail_silence.wav"
    output = tmp_path / "fail_hidden.wav"
    _create_wav(sample, n_samples=10000)

    encode_audio(str(sample), "secret", str(output), password="correct")
    with pytest.raises(DecryptionError):
        decode_audio(str(output), password="incorrect")


def test_audio_missing_password_fails(tmp_path):
    sample = tmp_path / "nopass_silence.wav"
    output = tmp_path / "nopass_hidden.wav"
    _create_wav(sample, n_samples=10000)

    encode_audio(str(sample), "secret", str(output), password="somepass")
    with pytest.raises(PasswordRequiredError):
        decode_audio(str(output), password=None)


def test_audio_unencoded_fails_cleanly(tmp_path):
    sample = tmp_path / "unencoded.wav"
    _create_wav(sample, n_samples=5000)

    with pytest.raises(PayloadNotFoundError):
        decode_audio(str(sample))


def test_audio_capacity_exceeded_raises_error(tmp_path):
    sample = tmp_path / "tiny.wav"
    output = tmp_path / "tiny_out.wav"
    _create_wav(sample, n_samples=100)  # 100 samples -> ~3 bytes capacity

    capacity = get_audio_capacity(str(sample))
    message = "A" * (capacity + 50)
    with pytest.raises(CapacityError):
        encode_audio(str(sample), message, str(output))


def test_audio_corrupted_file_raises_unsupported_carrier(tmp_path):
    corrupt_wav = tmp_path / "corrupt.wav"
    corrupt_wav.write_bytes(b"RIFF\x00\x00\x00\x00WAVEfmt garbage broken data")

    with pytest.raises(UnsupportedCarrierError):
        get_audio_capacity(corrupt_wav)

    with pytest.raises(UnsupportedCarrierError):
        decode_audio(corrupt_wav)


def test_audio_lossy_output_format_rejected(tmp_path):
    sample = tmp_path / "carrier.wav"
    _create_wav(sample, n_samples=10000)

    with pytest.raises(ValueError, match="Cannot save steganographic carrier as lossy format"):
        encode_audio(sample, "secret", tmp_path / "output.mp3")


def test_audio_nested_directory_created_automatically(tmp_path):
    sample = tmp_path / "carrier.wav"
    _create_wav(sample, n_samples=10000)
    nested_out = tmp_path / "sub" / "deep" / "output.wav"

    encode_audio(sample, "nested audio secret", nested_out)
    assert nested_out.exists()
    assert decode_audio(nested_out) == "nested audio secret"
