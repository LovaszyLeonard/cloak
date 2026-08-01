import os
import wave
from stego.carriers.audio import encode_audio, decode_audio

def test_audio_roundtrip():
    # Generate a short silent WAV (mono, 44100 Hz, 16-bit)
    with wave.open('silence.wav', 'w') as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)      # 16-bit
        wav.setframerate(44100)
        wav.writeframes(b'\x00\x00' * 44100)   # 1 second

    message = "Hello WAV!"
    encode_audio('silence.wav', message, 'hidden.wav')
    extracted = decode_audio('hidden.wav')
    assert extracted == message

    os.remove('silence.wav')
    os.remove('hidden.wav')

def test_audio_encryption():
    with wave.open('enc_silence.wav', 'w') as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(22050)
        wav.writeframes(b'\x00\x00' * 11025)   # 0.5 sec

    msg = "Top secret!"
    pwd = "strong"
    encode_audio('enc_silence.wav', msg, 'enc_hidden.wav', password=pwd)
    extracted = decode_audio('enc_hidden.wav', password=pwd)
    assert extracted == msg

    os.remove('enc_silence.wav')
    os.remove('enc_hidden.wav')