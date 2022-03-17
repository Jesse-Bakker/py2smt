from py2smt import __return__, assumes, ensures, param


@assumes(param.a < param.b)
@ensures(__return__ >= param.a, __return__ <= param.b)
@ensures((__return__ == param.c or __return__ == param.a) or __return__ == param.b)
def clamp(a: int, b: int, c: int) -> int:
    if c < a:
        ret = a
    elif c > b:
        ret = b
    else:
        ret = c
    return ret


# We cannot assert the correct answer here without inserting the function body,
# as the postconditions are not strong enough
assert clamp(0, 4, 6) != 6
assert clamp(0, 4, -2) >= 0 and clamp(0, 4, -1) <= 4

res = clamp(0, 4, clamp(-2, 3, 18))
assert res >= 0 and res <= 3
