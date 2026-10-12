import os
import shutil
import sys
import tempfile
from pathlib import Path


_TEST_DATABASE_DIRECTORY = Path(tempfile.mkdtemp(prefix="comp3613a1-tests-"))
_TEST_DATABASE_PATH = _TEST_DATABASE_DIRECTORY / "test.db"
_ORIGINAL_DATABASE_URI = os.environ.get("DATABASE_URI")

os.environ["DATABASE_URI"] = f"sqlite:///{_TEST_DATABASE_PATH.as_posix()}"


def pytest_sessionfinish(session, exitstatus):
    database_module = sys.modules.get("app.database")
    if database_module is not None:
        database_module.engine.dispose()

    if _ORIGINAL_DATABASE_URI is None:
        os.environ.pop("DATABASE_URI", None)
    else:
        os.environ["DATABASE_URI"] = _ORIGINAL_DATABASE_URI

    shutil.rmtree(_TEST_DATABASE_DIRECTORY, ignore_errors=True)