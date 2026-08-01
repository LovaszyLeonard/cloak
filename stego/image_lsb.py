from PIL import Image
from .crypto import encrypt_message, decrypt_message

def encode(image_path: str, message: str, output_path: str, password: str = None) -> None:
    img = Image.open(image_path).convert('RGB')
    raw_bytes = bytearray(img.tobytes())

    # If password is given, encrypt the message
    if password:
        payload_bytes = encrypt_message(message, password)
    else:
        payload_bytes = message.encode('utf-8')

    # Prefix the payload with its length
    length = len(payload_bytes)
    length_bytes = length.to_bytes(4, byteorder='little')
    all_bytes = length_bytes + payload_bytes

    bit_str = ''.join(format(byte, '08b') for byte in all_bytes)
    total_bits = len(bit_str)

    if total_bits > len(raw_bytes) * 8:
        raise ValueError(f"Payload too large! Need {total_bits} bits, image can hold {len(raw_bytes)*8}.")

    for i in range(total_bits):
        raw_bytes[i] = (raw_bytes[i] & 0xFE) | int(bit_str[i])

    new_img = Image.frombytes('RGB', img.size, bytes(raw_bytes))
    new_img.save(output_path, 'PNG')




def decode(image_path: str, password: str = None) -> str:
    img = Image.open(image_path).convert('RGB')
    raw_bytes = img.tobytes()

    bit_str = ''.join(str(byte & 1) for byte in raw_bytes)

    # Extract length
    length_bytes = bytes(int(bit_str[i:i+8], 2) for i in range(0, 32, 8))
    payload_length = int.from_bytes(length_bytes, byteorder='little')

    # Extract payload bits and convert to bytes
    payload_bits = bit_str[32 : 32 + payload_length * 8]
    payload_bytes = bytearray()
    for i in range(0, len(payload_bits), 8):
        byte = int(payload_bits[i:i+8], 2)
        payload_bytes.append(byte)
    payload_bytes = bytes(payload_bytes)

    if password:
        # Decrypt the payload
        return decrypt_message(payload_bytes, password)
    else:
        # Old behaviour: payload is the direct UTF-8 message
        return payload_bytes.decode('utf-8')