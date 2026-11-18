"""WAV audio carrier implementation using zero-copy bitwise LSB steganography."""

import wave
import zlib
from pathlib import Path
from typing import Dict, Optional, Tuple, Union

from ..crypto import encrypt_bytes, decrypt_bytes
from ..envelope import (
    pack_envelope,
    unpack_envelope,
    peek_envelope,
    embed_bits,
    embed_bits_scattered,
    derive_scatter_seed,
    FLAG_ENCRYPTED,
    FLAG_BINARY,
    FLAG_COMPRESSED,
    FLAG_SCATTERED,
    HEADER_SIZE,
)
from ..exceptions import (
    CapacityError,
    PasswordRequiredError,
    CorruptedPayloadError,
    UnsupportedCarrierError,
)

LOSSY_AUDIO_EXTENSIONS = {'.mp3', '.ogg', '.aac', '.flac', '.m4a', '.wma', '.opus'}


def _open_audio_safely(audio_path: Union[str, Path], mode: str = 'rb') -> wave.Wave_read:
    """Open WAV audio file with descriptive error handling for corrupted or unreadable audio."""
    path = Path(audio_path).expanduser()
    try:
        wav_in = wave.open(str(path), mode)
        if mode == 'rb':
            if wav_in.getcomptype() != 'NONE':
                comp_name = wav_in.getcompname()
                wav_in.close()
                raise UnsupportedCarrierError(
                    f"'{path.name}' uses unsupported compression ({comp_name}). "
                    "Only uncompressed PCM WAV files are supported."
                )
        return wav_in
    except (wave.Error, EOFError, OSError) as e:
        if isinstance(e, UnsupportedCarrierError):
            raise
        raise UnsupportedCarrierError(
            f"'{path.name}' is not a valid or readable WAV file: {e}"
        ) from e


def get_audio_capacity(audio_path: Union[str, Path]) -> int:
    """Return maximum payload capacity in bytes for the given WAV audio file."""
    with _open_audio_safely(audio_path, 'rb') as wav_in:
        n_frames = wav_in.getnframes()
        n_channels = wav_in.getnchannels()
    total_samples = n_frames * n_channels
    available_payload_bytes = (total_samples // 8) - HEADER_SIZE
    return max(0, available_payload_bytes)


def inspect_audio(audio_path: Union[str, Path]) -> Dict:
    """Inspect audio properties, steganographic capacity, and detect Cloak payloads."""
    path = Path(audio_path).expanduser()
    with _open_audio_safely(path, 'rb') as wav_in:
        params = wav_in.getparams()
        n_frames = wav_in.getnframes()
        framerate = wav_in.getframerate()
        n_channels = wav_in.getnchannels()
        sampwidth = wav_in.getsampwidth()

        header_samples = HEADER_SIZE * 8 * sampwidth
        peek_frames = wav_in.readframes(min(n_frames, header_samples))

    file_size = path.stat().st_size
    total_samples = n_frames * n_channels
    total_capacity_bytes = total_samples // 8
    max_payload_bytes = max(0, total_capacity_bytes - HEADER_SIZE)
    duration_seconds = n_frames / framerate if framerate > 0 else 0.0

    raw_sample = bytearray(peek_frames)
    envelope_info = peek_envelope(raw_sample, total_capacity_bytes=total_capacity_bytes, stride=sampwidth)

    return {
        "carrier_type": "audio",
        "format": "WAV",
        "channels": n_channels,
        "sample_rate": framerate,
        "sample_width_bits": sampwidth * 8,
        "duration_seconds": duration_seconds,
        "file_size": file_size,
        "capacity_bytes": max_payload_bytes,
        "envelope": envelope_info,
    }


def encode_audio(
    audio_path: Union[str, Path],
    message: Union[str, bytes],
    output_path: Union[str, Path],
    password: Optional[str] = None,
    is_binary: bool = False,
    scatter: bool = False,
    compress: bool = True,
) -> None:
    """Embed payload into the LSBs of audio samples in a WAV file."""
    out_p = Path(output_path).expanduser()
    if out_p.suffix.lower() in LOSSY_AUDIO_EXTENSIONS:
        raise ValueError(
            f"Cannot save steganographic carrier as lossy format '{out_p.suffix}'. "
            "Lossy compression destroys embedded payloads. Please use .wav."
        )
    out_p.parent.mkdir(parents=True, exist_ok=True)

    with _open_audio_safely(audio_path, 'rb') as wav_in:
        params = wav_in.getparams()
        frames = wav_in.readframes(wav_in.getnframes())

    raw_samples = bytearray(frames)
    sampwidth = params.sampwidth
    total_samples = len(raw_samples) // sampwidth
    max_payload = (total_samples // 8) - HEADER_SIZE

    if isinstance(message, str):
        payload_bytes = message.encode('utf-8')
    else:
        payload_bytes = bytes(message)
        is_binary = True

    # Transparent compression before encryption
    is_compressed = False
    if compress and len(payload_bytes) > 0:
        compressed_candidate = zlib.compress(payload_bytes, level=6)
        if len(compressed_candidate) < len(payload_bytes):
            payload_bytes = compressed_candidate
            is_compressed = True

    is_encrypted = bool(password)
    if is_encrypted:
        payload_bytes = encrypt_bytes(payload_bytes, password)

    if len(payload_bytes) > max_payload:
        raise CapacityError(
            f"Message too large! Need {len(payload_bytes)} bytes (+{HEADER_SIZE}b envelope), "
            f"but audio can only hold {max_payload} bytes."
        )

    envelope = pack_envelope(
        payload_bytes,
        is_encrypted=is_encrypted,
        is_binary=is_binary,
        is_compressed=is_compressed,
        is_scattered=scatter,
    )

    if scatter:
        # Embed fixed 9-byte header at indices 0..71
        embed_bits(raw_samples, envelope[:HEADER_SIZE], stride=sampwidth)
        # Embed payload bits scattered across the remaining audio samples
        seed = derive_scatter_seed(password)
        embed_bits_scattered(
            raw_samples,
            envelope[HEADER_SIZE:],
            seed=seed,
            total_elements=total_samples,
            stride=sampwidth,
        )
    else:
        embed_bits(raw_samples, envelope, stride=sampwidth)

    try:
        with wave.open(str(out_p), 'wb') as wav_out:
            wav_out.setparams(params)
            wav_out.writeframes(raw_samples)
    except (wave.Error, OSError) as e:
        raise UnsupportedCarrierError(f"Could not save output WAV file '{out_p.name}': {e}") from e


def decode_audio_raw(
    audio_path: Union[str, Path],
    password: Optional[str] = None,
) -> Tuple[int, bytes]:
    """Extract and decrypt raw payload bytes from a WAV audio file."""
    with _open_audio_safely(audio_path, 'rb') as wav_in:
        params = wav_in.getparams()
        frames = wav_in.readframes(wav_in.getnframes())

    raw_samples = bytearray(frames)
    sampwidth = params.sampwidth
    total_capacity_bytes = (len(raw_samples) // sampwidth) // 8

    flags, payload_bytes = unpack_envelope(
        raw_samples,
        total_capacity_bytes=total_capacity_bytes,
        stride=sampwidth,
        password=password,
    )

    if flags & FLAG_ENCRYPTED:
        if not password:
            raise PasswordRequiredError("Carrier contains an encrypted payload. A password is required.")
        payload_bytes = decrypt_bytes(payload_bytes, password)

    if flags & FLAG_COMPRESSED:
        try:
            payload_bytes = zlib.decompress(payload_bytes)
        except Exception as e:
            raise CorruptedPayloadError("Failed to decompress payload data.") from e

    return flags, payload_bytes


def decode_audio(
    audio_path: Union[str, Path],
    password: Optional[str] = None,
) -> str:
    """Extract and decrypt text message from a WAV audio file."""
    flags, payload_bytes = decode_audio_raw(audio_path, password)
    try:
        return payload_bytes.decode('utf-8')
    except UnicodeDecodeError as e:
        if flags & FLAG_BINARY:
            raise ValueError("Payload contains binary data. Use -O / --output-file to save to disk.") from e
        raise ValueError("Decoded payload is not valid UTF-8 text.") from e
