import ast

import py2smt.hir.types as hir
from py2smt.hir import lower_ast_to_hir


def unwrap_stmt(hir: hir.Module):
    return hir.body[0]


def check_hir_stmt(syntax: ast.Module, hir_stmt):
    assert unwrap_stmt(lower_ast_to_hir(syntax)) == hir_stmt


def check_expr_type(syntax: ast.Module, type_: type):
    assert unwrap_stmt(lower_ast_to_hir(syntax)).expr.type_ == type_


def test_simple_add():
    syntax = ast.parse("6 + 7")
    check_hir_stmt(
        syntax,
        hir.ExprStmt(
            hir.BinExpr(
                type_=int,
                lhs=hir.Constant(type_=int, value=6),
                rhs=hir.Constant(type_=int, value=7),
                op=hir.BinOperator.ADD,
            )
        ),
    )


def test_nested_ops():
    syntax = ast.parse("6 + 7 + 8")
    check_hir_stmt(
        syntax,
        hir.ExprStmt(
            hir.BinExpr(
                lhs=hir.BinExpr(
                    type_=int,
                    lhs=hir.Constant(type_=int, value=6),
                    rhs=hir.Constant(type_=int, value=7),
                    op=hir.BinOperator.ADD,
                ),
                rhs=hir.Constant(type_=int, value=8),
                type_=int,
                op=hir.BinOperator.ADD,
            )
        ),
    )


def test_propagate_float_type():
    syntax = ast.parse("6 + (7.0 * 3)")
    check_expr_type(syntax, float)


def test_binary_op():
    syntax = ast.parse("True and False or False")
    check_hir_stmt(
        syntax,
        hir.ExprStmt(
            hir.BinExpr(
                type_=bool,
                lhs=hir.BinExpr(
                    type_=bool,
                    lhs=hir.Constant(type_=bool, value=True),
                    rhs=hir.Constant(type_=bool, value=False),
                    op=hir.BinOperator.AND,
                ),
                rhs=hir.Constant(type_=bool, value=False),
                op=hir.BinOperator.OR,
            )
        ),
    )


def test_assert():
    syntax = ast.parse("assert True")
    check_hir_stmt(syntax, hir.Assert(test=hir.Constant(type_=bool, value=True)))


def test_assign():
    syntax = ast.parse("a = 3")
    check_hir_stmt(
        syntax,
        hir.Assign(
            lhs=hir.Name(type_=int, ident="a", ctx=hir.ExprContext.STORE),
            rhs=hir.Constant(type_=int, value=3),
        ),
    )


def test_multiple_assign():
    syntax = ast.parse("a = b = 3")
    assert lower_ast_to_hir(syntax) == hir.Module(
        [
            hir.Assign(
                lhs=hir.Name(type_=int, ident="a", ctx=hir.ExprContext.STORE),
                rhs=hir.Constant(type_=int, value=3),
            ),
            hir.Assign(
                lhs=hir.Name(type_=int, ident="b", ctx=hir.ExprContext.STORE),
                rhs=hir.Constant(type_=int, value=3),
            ),
        ]
    )


def test_name_store_load():
    syntax = ast.parse(
        """
a = 3
b = a
b
a
    """
    )

    assert lower_ast_to_hir(syntax) == hir.Module(
        [
            hir.Assign(
                lhs=hir.Name(type_=int, ident="a", ctx=hir.ExprContext.STORE),
                rhs=hir.Constant(type_=int, value=3),
            ),
            hir.Assign(
                lhs=hir.Name(type_=int, ident="b", ctx=hir.ExprContext.STORE),
                rhs=hir.Name(type_=int, ident="a", ctx=hir.ExprContext.LOAD),
            ),
            hir.ExprStmt(
                hir.Name(type_=int, ident="b", ctx=hir.ExprContext.LOAD),
            ),
            hir.ExprStmt(
                hir.Name(type_=int, ident="a", ctx=hir.ExprContext.LOAD),
            ),
        ]
    )


def test_assert_conversion():
    syntax = ast.parse("assert 3")
    check_hir_stmt(
        syntax,
        hir.Assert(
            hir.UnaryExpr(
                type_=bool,
                op=hir.UnaryOperator.NOT,
                operand=hir.BinExpr(
                    type_=bool,
                    lhs=hir.Constant(type_=int, value=3),
                    rhs=hir.Constant(type_=int, value=0),
                    op=hir.BinOperator.EQ,
                ),
            )
        ),
    )


def test_assert_full():
    syntax = ast.parse("a=1;assert a")
    assert lower_ast_to_hir(syntax) == hir.Module(
        [
            hir.Assign(
                lhs=hir.Name(type_=int, ident="a", ctx=hir.ExprContext.STORE),
                rhs=hir.Constant(type_=int, value=1),
            ),
            hir.Assert(
                test=hir.UnaryExpr(
                    type_=bool,
                    op=hir.UnaryOperator.NOT,
                    operand=hir.BinExpr(
                        type_=bool,
                        lhs=hir.Name(type_=int, ident="a", ctx=hir.ExprContext.LOAD),
                        rhs=hir.Constant(type_=int, value=0),
                        op=hir.BinOperator.EQ,
                    ),
                )
            ),
        ]
    )


def test_if():
    syntax = ast.parse(
        """
if True:
    pass
elif False:
    pass
else:
    pass
"""
    )
    check_hir_stmt(
        syntax,
        hir.If(
            test=hir.Constant(type_=bool, value=True),
            body=[hir.Pass()],
            orelse=[
                hir.If(
                    test=hir.Constant(type_=bool, value=False),
                    body=[hir.Pass()],
                    orelse=[hir.Pass()],
                )
            ],
        ),
    )


def test_simple_func():
    syntax = ast.parse(
        """
def func(a: int, b: bool) -> int:
    pass
"""
    )
    check_hir_stmt(
        syntax,
        hir.FuncDef(
            name="func",
            preconditions=[],
            postconditions=[],
            ret_type=int,
            arguments=[
                hir.Name(type_=int, ident="a", ctx=hir.ExprContext.LOAD),
                hir.Name(type_=bool, ident="b", ctx=hir.ExprContext.LOAD),
            ],
            body=[hir.Pass()],
        ),
    )
