import os
from pathlib import Path
import pytest

@pytest.fixture(autouse=True)
def ensure_repo_root():
    if not Path("dataset").exists() and Path("../dataset").exists():
        repo_root = Path(__file__).resolve().parent.parent.parent
        old_cwd = os.getcwd()
        os.chdir(repo_root)
        yield
        os.chdir(old_cwd)
    else:
        yield
