from pathlib import Path
import pytest

from budgetdev.config import Settings
from budgetdev.ledger import Ledger
from budgetdev.tools.base import ToolRegistry


@pytest.fixture
def workspace(tmp_path):
    (tmp_path / "app.py").write_text("def add(a, b):\n    return a - b\n")
    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "test_app.py").write_text("from app import add\n\ndef test_add():\n    assert add(2, 3) == 5\n")
    return tmp_path


@pytest.fixture
def ledger(tmp_path):
    return Ledger(tmp_path / "ledger.sqlite3")


@pytest.fixture
def settings(tmp_path):
    return Settings(bifrost_base_url="https://example.test/v1", bifrost_api_key="key",
                    cheap_model="cheap", coder_model="coder", ledger_path=tmp_path / "ledger.sqlite3")


@pytest.fixture
def registry():
    return ToolRegistry()
