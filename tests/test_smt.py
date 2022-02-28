from typing import List

import z3  # type: ignore

from py2smt import compile


def check_smt(text: str, smt: List[str], sat: bool = True):
    actual = compile(text)
    expected = "\n".join(smt)
    assert actual == expected
    z3_inp = z3.parse_smt2_string(actual)
    solver = z3.SimpleSolver()
    solver.add(z3_inp)
    if sat:
        assert solver.check() == z3.sat
    else:
        assert solver.check() == z3.unsat


def test_simple_assign():
    check_smt("a = 1", ["(declare-fun a0 () Int)", "(assert (= a0 1))"])


def test_multiple_assign_constant():
    program = """
a = 1
a = 2
    """
    smt = [
        "(declare-fun a0 () Int)",
        "(declare-fun a1 () Int)",
        "(assert (= a0 1))",
        "(assert (= a1 2))",
    ]

    check_smt(program, smt)


def test_assign_variable():
    program = """
a = 1
b = a
    """
    smt = [
        "(declare-fun a0 () Int)",
        "(declare-fun b0 () Int)",
        "(assert (= a0 1))",
        "(assert (= b0 a0))",
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
        "(declare-fun a0 () Int)",
        "(declare-fun a1 () Int)",
        "(declare-fun a2 () Int)",
        "(declare-fun b0 () Int)",
        "(assert (= a0 1))",
        "(assert (= b0 a0))",
        "(assert (= a1 2))",
        "(assert (= a2 b0))",
    ]

    check_smt(program, smt)


def test_assert():
    program = """
a = 1
assert a
"""
    smt = ["(declare-fun a0 () Int)", "(assert (= a0 1))", "(assert (not (= a0 0)))"]
    check_smt(program, smt)
