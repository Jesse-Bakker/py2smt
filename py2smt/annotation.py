import functools
from unittest import mock

_param = mock.MagicMock()
_param.__gt__ = mock.Mock()
_param.__lt__ = mock.Mock()
_param.__le__ = mock.Mock()
_param.__ge__ = mock.Mock()


class _ParamImpl:
    def __getattr__(self, name):
        return _param


param = _ParamImpl()

__return__ = _param


def __old__(*args, **kwargs):
    pass


def assumes(*args):
    @functools.wraps
    def inner(function):
        return function

    return inner


def ensures(*args):
    @functools.wraps
    def inner(function):
        return function

    return inner


def loop_invariant(*args):
    pass
