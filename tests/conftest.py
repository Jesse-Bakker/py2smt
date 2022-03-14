import os


def pytest_generate_tests(metafunc):
    if "testfile_name" in metafunc.fixturenames:
        filenames = (
            os.path.join(dp, fn)
            for (dp, _, fns) in os.walk("tests/integration/")
            for fn in fns
        )
        metafunc.parametrize("testfile_name", filenames)
