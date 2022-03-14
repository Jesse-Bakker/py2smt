from typing import List

import z3  # type: ignore

from py2smt import get_smt


def normalize_whitespace(smt: str):
    n = 0

    def ws_filter(c):
        nonlocal n
        if c == "(":
            n += 1
        elif c == ")":
            n -= 1
        elif c == "\n":
            if n == 0:
                return True
            return False
        return True

    return "".join(filter(ws_filter, smt))


def check_smt(text: str, smt: List[str], sat: bool = True):
    actual = [s for smt in get_smt(text) for s in smt.splitlines()]
    expected = smt
    assert actual == expected
    z3_inp = z3.parse_smt2_string("\n".join(actual))
    solver = z3.SimpleSolver()
    solver.add(z3_inp)
    if sat:
        assert solver.check() == z3.sat
    else:
        assert solver.check() == z3.unsat


def test_simple_assign():
    check_smt("a = 1", ["(declare-fun a$0$0 () Int)", "(assert (= a$0$0 1))"])


def test_multiple_assign_constant():
    program = """
a = 1
a = 2
    """
    smt = [
        "(declare-fun a$0$0 () Int)",
        "(declare-fun a$0$1 () Int)",
        "(assert (= a$0$0 1))",
        "(assert (= a$0$1 2))",
    ]

    check_smt(program, smt)


def test_assign_variable():
    program = """
a = 1
b = a
    """
    smt = [
        "(declare-fun a$0$0 () Int)",
        "(declare-fun b$0$0 () Int)",
        "(assert (= a$0$0 1))",
        "(assert (= b$0$0 a$0$0))",
    ]

    check_smt(program, smt)


def test_assign_variable_multiple():
    program = """
a = 1
b = a
a = 2
a = b
    """
    smt = [
        "(declare-fun a$0$0 () Int)",
        "(declare-fun a$0$1 () Int)",
        "(declare-fun a$0$2 () Int)",
        "(declare-fun b$0$0 () Int)",
        "(assert (= a$0$0 1))",
        "(assert (= b$0$0 a$0$0))",
        "(assert (= a$0$1 2))",
        "(assert (= a$0$2 b$0$0))",
    ]

    check_smt(program, smt)


def test_assert():
    program = """
a = 1
assert a
"""
    smt = [
        "(declare-fun a$0$0 () Int)",
        "(assert (= a$0$0 1))",
        "(push 1)",
        "(assert (not (not (= a$0$0 0))))",
        "(check-sat)",
        "(pop 1)",
    ]
    check_smt(program, smt)


def test_if():
    program = """
a = 0
if a:
    b = 1
else:
    b = 2
"""
    smt = [
        "(declare-fun a$0$0 () Int)",
        "(declare-fun b$0_0$0 () Int)",
        "(declare-fun b$0_1$0 () Int)",
        "(declare-fun b$0$0 () Int)",
        "(assert (= a$0$0 0))",
        "(assert (=> (not (= a$0$0 0)) (= b$0_0$0 1)))",
        "(assert (=> (not (not (= a$0$0 0))) (= b$0_1$0 2)))",
        "(assert (=> (not (= a$0$0 0)) (= b$0$0 b$0_0$0)))",
        "(assert (=> (not (not (= a$0$0 0))) (= b$0$0 b$0_1$0)))",
    ]
    check_smt(program, smt)
