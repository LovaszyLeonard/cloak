def test_encryption_roundtrip():
    from PIL import Image
    Image.new('RGB', (100,100), color='blue').save('enc_sample.png')
    message = "Encrypted test!"
    password = "strongpassword"
    encode('enc_sample.png', message, 'enc_hidden.png', password)
    extracted = decode('enc_hidden.png', password)
    assert extracted == message


    import os
    os.remove('enc_sample.png')
    os.remove('enc_hidden.png')


def test_wrong_password_fails():
    from PIL import Image
    Image.new('RGB', (50,50), color='red').save('fail_sample.png')
    encode('fail_sample.png', 'test', 'fail_hidden.png', 'pass')
    try:
        decode('fail_hidden.png', 'wrong')
        assert False, "Should have raised"
    except Exception:
        pass
    os.remove('fail_sample.png')
    os.remove('fail_hidden.png')