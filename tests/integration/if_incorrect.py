from py2smt import __return__, ensures, param


@ensures(
    __return__ >= param.a,
    __return__ >= param.b,
    __return__ >= param.c,
    (__return__ == param.a or __return__ == param.b) or __return__ == param.c,
)
def largest(a: int, b: int, c: int) -> int:
    if a > b:
        if a < c:
            ret = a
        else:
            ret = c
    elif b > c:
        ret = b
    else:
        ret = c
    return ret
