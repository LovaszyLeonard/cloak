import subprocess
import sys
import os
from PIL import Image


def test_cli_roundtrip(tmp_path):
    # Create a sample PNG
    sample = tmp_path / "sample.png"
    Image.new('RGB', (100, 100), 'blue').save(sample)

    output = tmp_path / "hidden.png"
    message = "CLI test message!"



    result = subprocess.run(
        [sys.executable, "-m", "stego", "encode",
         "-i", str(sample), "-m", message, "-o", str(output)],
        capture_output=True, text=True
    )
    assert result.returncode == 0



    result = subprocess.run(
        [sys.executable, "-m", "stego", "decode",
         "-i", str(output)],
        capture_output=True, text=True
    )
    assert result.returncode == 0
    assert message in result.stdout