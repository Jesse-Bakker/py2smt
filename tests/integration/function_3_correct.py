from py2smt import __return__, assumes, ensures, param


@assumes(param.a > 0)
@ensures(__return__ == 2 * param.a)
def double(a: int) -> int:
    return a * 2


assert double(double(1)) == 4
