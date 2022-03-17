from py2smt import loop_invariant

x = 5
y = 3
k = 0
r = 0
while k < x:
    loop_invariant(k <= x and r == k * y)
    r = r + y
    k = k + 1

assert r == x * y
