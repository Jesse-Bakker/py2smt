from py2smt import __return__, assumes, ensures, loop_invariant, param


@assumes(param.n > 0)
@ensures(__return__ == (param.n * (param.n - 1)) // 2)
def sum(n: int) -> int:
    i = 0
    sum = 0
    while i < n:
        loop_invariant(sum == (i * (i - 1)) // 2, i <= n)
        sum = sum + i
        i = i + 1
    return sum
