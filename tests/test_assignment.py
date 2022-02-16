from py2smt import compile


def test_simple_assign():
    assert compile("a = 1") == ["(declare-fun a0 () Int)", "(assert (= a0 1))"]


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

    assert compile(program) == smt


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

    assert compile(program) == smt


def test_assign_variable_multiple():
    program = """
a = 1
b = a
a = 2
a = b
    """
    smt = [
        "(declare-fun a0 () Int)",
        "(declare-fun b0 () Int)",
        "(declare-fun a1 () Int)",
        "(declare-fun a2 () Int)",
        "(assert (= a0 1))",
        "(assert (= b0 a0))",
        "(assert (= a1 2))",
        "(assert (= a2 b0))",
    ]

    assert compile(program) == smt
