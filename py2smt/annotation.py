class _ParamImpl:
    def __getattr__(self, name):
        return Param()


class Param:
    def __eq__(self, o):
        pass

    def __lt__(self, o):
        pass

    def __gt__(self, o):
        pass

    def __gte__(self, o):
        pass

    def __lte__(self, o):
        pass


param = _ParamImpl()

__return__ = Param()


def __old__(*args, **kwargs):
    pass


def assumes(*args):
    def inner(function):
        return function

    return inner


def ensures(*args):
    def inner(function):
        return function

    return inner
