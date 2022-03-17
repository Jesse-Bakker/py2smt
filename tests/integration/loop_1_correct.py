from py2smt import loop_invariant

x = 10
while x > 0:
    loop_invariant(x >= 0)
    x = x - 1

assert x == 0
