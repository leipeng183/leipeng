import os
import shutil
import tempfile
from contextlib import contextmanager

from . import CliRunner

__all__ = ["CliRunner", "isolated_filesystem"]


@contextmanager
def isolated_filesystem():
    previous = os.getcwd()
    directory = tempfile.mkdtemp()
    try:
        os.chdir(directory)
        yield directory
    finally:
        os.chdir(previous)
        shutil.rmtree(directory)
