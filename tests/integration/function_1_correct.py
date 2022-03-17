from py2smt import __return__, ensures, param


@ensures(__return__ == param.a + param.b)
def plus(a: int, b: int) -> int:
    return a + b


assert plus(1, 2) == 3
