"""Envelope framing, compression, and zero-copy bitwise steganography engine for Cloak."""

import hashlib
import zlib
from typing import Dict, List, Optional, Tuple, Union
from .exceptions import (
    CapacityError,
    PayloadNotFoundError,
    CorruptedPayloadError,
)

# 4-byte magic signature: 'C', 'L', 'K', version 0x01
MAGIC = b"CLK\x01"
FLAG_RAW = 0x00
FLAG_ENCRYPTED = 0x01
FLAG_BINARY = 0x02
FLAG_COMPRESSED = 0x04
FLAG_SCATTERED = 0x08

HEADER_SIZE = 9  # 4 bytes magic + 1 byte flags + 4 bytes length (big-endian)


def derive_scatter_seed(password: Optional[str] = None) -> bytes:
    """Derive a deterministic 32-byte seed for pseudo-random bit scattering."""
    if password:
        return hashlib.sha256(b"cloak_scatter:" + password.encode('utf-8')).digest()
    return hashlib.sha256(b"cloak_scatter:default_unencrypted").digest()


def _get_feistel_params(key_bytes: bytes, M: int) -> Tuple[List[int], int, int]:
    """Precompute Feistel round keys, half-width, and bitmask for M elements."""
    if M <= 1:
        return [], 0, 0
    k = (M - 1).bit_length()
    if k % 2 != 0:
        k += 1
    w = k // 2
    mask = (1 << w) - 1
    round_keys = [
        int.from_bytes(hashlib.sha256(key_bytes + bytes([r])).digest()[:4], "big")
        for r in range(4)
    ]
    return round_keys, w, mask


def _feistel_permute_fast(val: int, round_keys: List[int], w: int, mask: int, M: int) -> int:
    """Perform Feistel permutation in O(1) time using precomputed keys and bitmask."""
    if M <= 1:
        return 0
    curr = val
    while True:
        L = curr >> w
        R = curr & mask
        for r in range(4):
            f = ((R * 2654435761) ^ round_keys[r]) & mask
            L, R = R, L ^ f
        curr = (L << w) | R
        if curr < M:
            return curr


def feistel_permute(val: int, key_bytes: bytes, M: int) -> int:
    """Permute integer val in [0, M-1] using a 4-round Feistel cipher with cycle walking."""
    round_keys, w, mask = _get_feistel_params(key_bytes, M)
    return _feistel_permute_fast(val, round_keys, w, mask, M)


def pack_envelope(
    payload: bytes,
    is_encrypted: bool = False,
    is_binary: bool = False,
    is_compressed: bool = False,
    is_scattered: bool = False,
) -> bytes:
    """Create a formatted Cloak envelope containing magic header, flags, and payload."""
    flags = 0
    if is_encrypted:
        flags |= FLAG_ENCRYPTED
    if is_binary:
        flags |= FLAG_BINARY
    if is_compressed:
        flags |= FLAG_COMPRESSED
    if is_scattered:
        flags |= FLAG_SCATTERED

    length_bytes = len(payload).to_bytes(4, byteorder='big')
    return MAGIC + bytes([flags]) + length_bytes + payload


def embed_bits(carrier: bytearray, data: bytes, stride: int = 1) -> None:
    """
    Embed bits sequentially into the least significant bit (LSB) of carrier elements.
    Runs in-place with zero string allocations using unrolled bitwise operations.
    """
    required_elements = len(data) * 8 * stride
    if len(carrier) < required_elements:
        raise CapacityError(
            f"Carrier buffer too small: requires {required_elements} bytes, but carrier has {len(carrier)}."
        )

    carrier_idx = 0
    for byte in data:
        carrier[carrier_idx] = (carrier[carrier_idx] & 0xFE) | ((byte >> 7) & 1)
        carrier[carrier_idx + stride] = (carrier[carrier_idx + stride] & 0xFE) | ((byte >> 6) & 1)
        carrier[carrier_idx + 2 * stride] = (carrier[carrier_idx + 2 * stride] & 0xFE) | ((byte >> 5) & 1)
        carrier[carrier_idx + 3 * stride] = (carrier[carrier_idx + 3 * stride] & 0xFE) | ((byte >> 4) & 1)
        carrier[carrier_idx + 4 * stride] = (carrier[carrier_idx + 4 * stride] & 0xFE) | ((byte >> 3) & 1)
        carrier[carrier_idx + 5 * stride] = (carrier[carrier_idx + 5 * stride] & 0xFE) | ((byte >> 2) & 1)
        carrier[carrier_idx + 6 * stride] = (carrier[carrier_idx + 6 * stride] & 0xFE) | ((byte >> 1) & 1)
        carrier[carrier_idx + 7 * stride] = (carrier[carrier_idx + 7 * stride] & 0xFE) | (byte & 1)
        carrier_idx += 8 * stride


def embed_bits_scattered(
    carrier: bytearray,
    data: bytes,
    seed: bytes,
    total_elements: int,
    stride: int = 1,
) -> None:
    """
    Embed data bits pseudo-randomly scattered across available carrier elements.
    Preserves fixed header at indices 0..71, scattering the payload across the remaining space.
    """
    header_elements = HEADER_SIZE * 8
    pool_size = total_elements - header_elements
    total_bits = len(data) * 8
    if pool_size <= 0 or pool_size < total_bits:
        raise CapacityError(
            f"Carrier pool too small for scattered payload: {max(0, pool_size)} bits available, {total_bits} needed."
        )

    round_keys, w, mask = _get_feistel_params(seed, pool_size)

    for bit_idx in range(total_bits):
        byte_val = data[bit_idx // 8]
        bit = (byte_val >> (7 - (bit_idx % 8))) & 1
        pos = _feistel_permute_fast(bit_idx, round_keys, w, mask, pool_size)
        carrier_idx = (header_elements + pos) * stride
        carrier[carrier_idx] = (carrier[carrier_idx] & 0xFE) | bit


def extract_bytes(carrier: Union[bytes, bytearray], num_bytes: int, start_idx: int = 0, stride: int = 1) -> bytes:
    """Extract num_bytes sequentially from the LSBs of carrier using bitwise accumulation."""
    if num_bytes == 0:
        return b""
    required_len = start_idx + (num_bytes * 8 - 1) * stride + 1
    if len(carrier) < required_len:
        raise CorruptedPayloadError(
            f"Carrier buffer truncated: requires {required_len} elements, but carrier has only {len(carrier)}."
        )
    out = bytearray(num_bytes)
    carrier_idx = start_idx
    for i in range(num_bytes):
        val = 0
        for _ in range(8):
            val = (val << 1) | (carrier[carrier_idx] & 1)
            carrier_idx += stride
        out[i] = val
    return bytes(out)


def extract_bytes_scattered(
    carrier: Union[bytes, bytearray],
    num_bytes: int,
    seed: bytes,
    total_elements: int,
    stride: int = 1,
) -> bytes:
    """Extract num_bytes scattered across carrier elements using Feistel permutation."""
    header_elements = HEADER_SIZE * 8
    pool_size = total_elements - header_elements
    total_bits = num_bytes * 8
    if pool_size <= 0 or pool_size < total_bits:
        raise CorruptedPayloadError(
            f"Carrier pool too small for scattered payload: {max(0, pool_size)} bits available, {total_bits} claimed."
        )

    round_keys, w, mask = _get_feistel_params(seed, pool_size)
    out = bytearray(num_bytes)

    for bit_idx in range(total_bits):
        pos = _feistel_permute_fast(bit_idx, round_keys, w, mask, pool_size)
        carrier_idx = (header_elements + pos) * stride
        if carrier_idx >= len(carrier):
            raise CorruptedPayloadError(
                f"Carrier buffer truncated: index {carrier_idx} out of range (buffer size {len(carrier)})."
            )
        bit = carrier[carrier_idx] & 1
        byte_pos = bit_idx // 8
        out[byte_pos] = (out[byte_pos] << 1) | bit

    return bytes(out)


def peek_envelope(carrier: Union[bytes, bytearray], total_capacity_bytes: int, stride: int = 1) -> Dict:
    """
    Inspect whether carrier contains a valid Cloak envelope header without reading the full payload.
    Returns a dict with detection status and payload metadata.
    """
    required_bytes = (HEADER_SIZE * 8 - 1) * stride + 1
    if total_capacity_bytes < HEADER_SIZE or len(carrier) < required_bytes:
        return {"detected": False, "reason": "Carrier buffer is too small"}

    try:
        header = extract_bytes(carrier, HEADER_SIZE, start_idx=0, stride=stride)
    except CorruptedPayloadError:
        return {"detected": False, "reason": "Carrier buffer truncated"}

    if not header.startswith(MAGIC):
        return {"detected": False, "reason": "No magic signature"}

    flags = header[4]
    payload_len = int.from_bytes(header[5:9], byteorder='big')
    is_valid_len = (HEADER_SIZE + payload_len) <= total_capacity_bytes

    return {
        "detected": True,
        "version": header[3],
        "is_encrypted": bool(flags & FLAG_ENCRYPTED),
        "is_binary": bool(flags & FLAG_BINARY),
        "is_compressed": bool(flags & FLAG_COMPRESSED),
        "is_scattered": bool(flags & FLAG_SCATTERED),
        "payload_length": payload_len,
        "is_corrupted": not is_valid_len,
    }


def unpack_envelope(
    carrier: Union[bytes, bytearray],
    total_capacity_bytes: int,
    stride: int = 1,
    password: Optional[str] = None,
) -> Tuple[int, bytes]:
    """
    Validate and unpack the Cloak envelope from carrier elements.
    Supports both sequential and pseudo-random scattered embedding modes.
    Returns (flags, payload_bytes).
    """
    if total_capacity_bytes < HEADER_SIZE:
        raise PayloadNotFoundError("Carrier file is too small to contain a Cloak payload.")

    # Read exactly the 9-byte header first
    header = extract_bytes(carrier, HEADER_SIZE, start_idx=0, stride=stride)

    if not header.startswith(MAGIC):
        raise PayloadNotFoundError("No Cloak payload found in carrier (missing magic signature).")

    flags = header[4]
    payload_len = int.from_bytes(header[5:9], byteorder='big')

    required_capacity = HEADER_SIZE + payload_len
    if required_capacity > total_capacity_bytes:
        raise CorruptedPayloadError(
            f"Corrupted payload header: claims {payload_len} bytes, but carrier capacity is {total_capacity_bytes - HEADER_SIZE} bytes."
        )

    total_elements = total_capacity_bytes * 8
    if flags & FLAG_SCATTERED:
        seed = derive_scatter_seed(password)
        payload_bytes = extract_bytes_scattered(
            carrier,
            num_bytes=payload_len,
            seed=seed,
            total_elements=total_elements,
            stride=stride,
        )
    else:
        payload_bytes = extract_bytes(
            carrier,
            num_bytes=payload_len,
            start_idx=HEADER_SIZE * 8 * stride,
            stride=stride,
        )

    return flags, payload_bytes
