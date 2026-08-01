def test_tui_import():
    from stego.tui import run_tui
    assert callable(run_tui)