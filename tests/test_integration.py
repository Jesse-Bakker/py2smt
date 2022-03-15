from pathlib import Path

import pytest

from py2smt.check import CheckFailed, check


def test_integration(testfile_name):
    correct = not testfile_name.endswith("incorrect.py")
    data = Path(testfile_name).read_text()
    if correct:
        check(data)
    else:
        with pytest.raises(CheckFailed):
            check(data)
