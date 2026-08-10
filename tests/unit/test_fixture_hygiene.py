"""Test-only protection against local interpreter output polluting golden fixtures."""

from pathlib import Path

from conftest import clean_instrument_fixture_bytecode


def test_fixture_hygiene_removes_only_generated_python_bytecode(tmp_path: Path):
    package = tmp_path / "instrument" / "game"
    cache = package / "__pycache__"
    cache.mkdir(parents=True)
    source = package / "game.py"
    bytecode = cache / "game.cpython-311.pyc"
    source.write_text("VALUE = 1\n", encoding="utf-8")
    bytecode.write_bytes(b"generated")

    clean_instrument_fixture_bytecode(tmp_path)

    assert source.read_text(encoding="utf-8") == "VALUE = 1\n"
    assert not cache.exists()
