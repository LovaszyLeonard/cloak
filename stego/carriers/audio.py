import wave
from ..crypto import encrypt_message, decrypt_message


def encode_audio(audio_path: str, message: str, output_path: str, password: str = None) -> None:
    with wave.open(audio_path, 'rb') as wav_in:
        params = wav_in.getparams()
        frames = wav_in.readframes(wav_in.getnframes())

    raw_samples = bytearray(frames)

    if password:
        payload_bytes = encrypt_message(message, password)
    else:
        payload_bytes = message.encode('utf-8')


    length = len(payload_bytes)
    length_bytes = length.to_bytes(4, byteorder='little')
    all_bytes = length_bytes + payload_bytes



    bit_str = ''.join(format(byte, '08b') for byte in all_bytes)
    total_bits = len(bit_str)


    num_samples = len(raw_samples) // params.sampwidth  # sampwidth == 2 for 16‑bit
    if total_bits > num_samples:
        raise ValueError(f"Message too large! Need {total_bits} bits, audio has {num_samples} samples.")



    bit_index = 0
    sample_width = params.sampwidth
    for i in range(0, len(raw_samples), sample_width):
        if bit_index >= total_bits:
            break
        raw_samples[i] = (raw_samples[i] & 0xFE) | int(bit_str[bit_index])
        bit_index += 1

    with wave.open(output_path, 'wb') as wav_out:
        wav_out.setparams(params)
        wav_out.writeframes(raw_samples)


def decode_audio(audio_path: str, password: str = None) -> str:
    with wave.open(audio_path, 'rb') as wav_in:
        params = wav_in.getparams()
        frames = wav_in.readframes(wav_in.getnframes())

    raw_samples = bytearray(frames)
    sample_width = params.sampwidth



    bit_str = ''
    for i in range(0, len(raw_samples), sample_width):
        bit_str += str(raw_samples[i] & 1)



    length_bytes = bytes(int(bit_str[j:j+8], 2) for j in range(0, 32, 8))
    payload_length = int.from_bytes(length_bytes, byteorder='little')



    payload_bits = bit_str[32 : 32 + payload_length * 8]
    payload_bytes = bytearray()
    for i in range(0, len(payload_bits), 8):
        byte = int(payload_bits[i:i+8], 2)
        payload_bytes.append(byte)
    payload_bytes = bytes(payload_bytes)

    if password:
        return decrypt_message(payload_bytes, password)
    else:
        return payload_bytes.decode('utf-8')