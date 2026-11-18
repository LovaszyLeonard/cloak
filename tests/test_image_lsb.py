import pytest
from PIL import Image

from stego.exceptions import (
    CapacityError,
    DecryptionError,
    PasswordRequiredError,
    PayloadNotFoundError,
)
from stego.image_lsb import decode, encode, get_image_capacity


def test_plain_image_roundtrip(tmp_path):
    sample = tmp_path / "plain_sample.png"
    output = tmp_path / "plain_hidden.png"
    Image.new("RGB", (60, 60), color="green").save(sample)

    message = "Simple plain text secret message"
    encode(str(sample), message, str(output))
    extracted = decode(str(output))
    assert extracted == message


def test_encryption_roundtrip(tmp_path):
    sample = tmp_path / "enc_sample.png"
    output = tmp_path / "enc_hidden.png"
    Image.new("RGB", (80, 80), color="blue").save(sample)

    message = "Encrypted test!"
    password = "strongpassword"
    encode(str(sample), message, str(output), password)
    extracted = decode(str(output), password)
    assert extracted == message


def test_wrong_password_fails(tmp_path):
    sample = tmp_path / "fail_sample.png"
    output = tmp_path / "fail_hidden.png"
    Image.new("RGB", (50, 50), color="red").save(sample)

    encode(str(sample), "test", str(output), "correct_pass")
    with pytest.raises(DecryptionError):
        decode(str(output), "wrong_pass")


def test_encrypted_without_password_fails(tmp_path):
    sample = tmp_path / "enc_nopass_sample.png"
    output = tmp_path / "enc_nopass_hidden.png"
    Image.new("RGB", (50, 50), color="purple").save(sample)

    encode(str(sample), "sensitive", str(output), "some_pass")
    with pytest.raises(PasswordRequiredError):
        decode(str(output), password=None)


def test_unencoded_image_fails_cleanly(tmp_path):
    sample = tmp_path / "unencoded.png"
    Image.new("RGB", (40, 40), color="white").save(sample)

    with pytest.raises(PayloadNotFoundError):
        decode(str(sample))


def test_capacity_exceeded_raises_error(tmp_path):
    sample = tmp_path / "tiny.png"
    output = tmp_path / "tiny_out.png"
    Image.new("RGB", (5, 5), color="black").save(
        sample
    )  # 25 pixels * 3 bytes = 75 bytes capacity (max ~0 bytes payload)

    capacity = get_image_capacity(str(sample))
    huge_message = "A" * (capacity + 50)
    with pytest.raises(CapacityError):
        encode(str(sample), huge_message, str(output))
