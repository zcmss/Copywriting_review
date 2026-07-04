# tests/conftest.py - shared fixtures
import os
import sys
import tempfile
import pytest

# ensure project root is in path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def temp_dir():
    """create a temporary directory for file-based tests."""
    with tempfile.TemporaryDirectory() as td:
        yield td


@pytest.fixture
def test_inputs_dir(temp_dir):
    """a temp directory with sample audit files."""
    os.makedirs(os.path.join(temp_dir, "inputs"), exist_ok=True)
    clean = os.path.join(temp_dir, "inputs", "clean.txt")
    violation = os.path.join(temp_dir, "inputs", "violation.txt")
    with open(clean, "w", encoding="utf-8") as f:
        f.write("normal document content\nnothing suspicious here.\n")
    with open(violation, "w", encoding="utf-8") as f:
        f.write("this document contains forbidden keyword 绝绝子 and more.\n")
    yield os.path.join(temp_dir, "inputs")
