from py2smt import __return__, assumes, ensures, param


@assumes(param.a > 0, param.b > 0)
@ensures(__return__ == param.a + param.b)
def plus(a: int, b: int) -> int:
    return a + b


assert plus(1, 2) == 3
