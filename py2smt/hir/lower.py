import ast

from .types import (
    Assert,
    Assign,
    BinExpr,
    BinOperator,
    Constant,
    Expr,
    ExprContext,
    ExprStmt,
    IllegalOperationException,
    Module,
    Name,
    UnaryExpr,
    UnaryOperator,
    UnsupportedException,
)


class AstVisitor(ast.NodeVisitor):
    def __init__(self):
        super().__init__()
        self.names = {}

    def visit_BinOp(self, node) -> BinExpr:
        BO = BinOperator
        operator_map = {
            ast.Add: BO.ADD,
            ast.Sub: BO.SUB,
            ast.Mult: BO.MUL,
            ast.Div: BO.DIV,
            ast.Mod: BO.MOD,
            ast.Pow: BO.POW,
            ast.LShift: BO.LSHIFT,
            ast.RShift: BO.RSHIFT,
            ast.BitOr: BO.BITOR,
            ast.BitXor: BO.BITXOR,
            ast.BitAnd: BO.BITAND,
            ast.FloorDiv: BO.FLOORDIV,
        }

        lhs: Expr = self.visit(node.left)
        rhs: Expr = self.visit(node.right)

        type_: type
        if issubclass(lhs.type_, int) and issubclass(rhs.type_, int):
            type_ = int
        elif issubclass(rhs.type_, float) or issubclass(lhs.type_, float):
            type_ = float
        else:
            raise UnsupportedException(
                "Only int, bool and float types are supported in binary expressions"
            )

        op = operator_map[type(node.op)]
        if (
            op in (BO.LSHIFT, BO.RSHIFT, BO.BITOR, BO.BITXOR, BO.BITAND)
            and type_ is float
        ):
            raise IllegalOperationException(
                "Bit operations are only allowed on integer types"
            )
        return BinExpr(lhs=lhs, rhs=rhs, op=op, type_=type_)

    def visit_BoolOp(self, node: ast.BoolOp):
        lhs = self.visit(node.values[0])
        rhs = self.visit(node.values[1])

        # bool is a subclass of int
        if not issubclass(lhs.type_, (int, float)) or not issubclass(
            rhs.type_, (int, float)
        ):
            raise UnsupportedException(
                "Boolean operators are only supported on bools, ints and floats"
            )

        if isinstance(node.op, ast.And):
            op = BinOperator.AND
        elif isinstance(node.op, ast.Or):
            op = BinOperator.OR
        else:
            assert False, "Unexpected boolean operator"

        if lhs.type_ is not rhs.type_:
            raise UnsupportedException(
                "Boolean operators are only supported on operands of the same type"
            )
        return BinExpr(lhs=lhs, rhs=rhs, type_=lhs.type_, op=op)

    def visit_Constant(self, node: ast.Constant):
        return Constant(type_=type(node.value), value=node.value)

    def visit_Expr(self, node: ast.Expr):
        return ExprStmt(expr=self.visit(node.value))

    def visit_Module(self, node: ast.Module):
        # Stmts can be split into multiple statements, for example with multiple
        # assignment: `a = b = 2 -> a = 2; b = 2`, so we unpack here
        stmts = []
        for ast_stmt in node.body:
            stmt = self.visit(ast_stmt)
            if isinstance(stmt, list):
                stmts.extend(stmt)
            else:
                stmts.append(stmt)
        return Module(body=stmts)

    def expr_to_bool(self, expr: Expr):
        if expr.type_ is bool:
            return expr

        def make_expr(type_, value):
            return UnaryExpr(
                type_=bool,
                op=UnaryOperator.NOT,
                operand=BinExpr(
                    type_=bool,
                    lhs=expr,
                    rhs=Constant(type_=type_, value=value),
                    op=BinOperator.EQ,
                ),
            )

        if expr.type_ is int:
            return make_expr(int, 0)
        elif expr.type_ is float:
            return make_expr(float, 0.0)
        else:
            raise UnsupportedException(
                "Only int's and floats can be converted to boolean expressions"
            )

    def visit_Assert(self, node: ast.Assert):
        test: Expr = self.visit(node.test)
        test = self.expr_to_bool(test)
        return Assert(test=test)

    def visit_Assign(self, node: ast.Assign):
        targets = node.targets
        rhs: Expr = self.visit(node.value)
        type_ = rhs.type_
        stmts = []
        for name in targets:
            if not isinstance(name, ast.Name):
                raise UnsupportedException("Only assignments to names are supported")
            self.names[name.id] = type_
            stmts.append(
                Assign(
                    lhs=Name(type_=type_, ident=name.id, ctx=ExprContext.STORE), rhs=rhs
                )
            )
        return stmts

    def visit_Name(self, node: ast.Name):
        # We only care about loads here, as we handle stores in `visit_Assign`
        if isinstance(node.ctx, ast.Del):
            raise UnsupportedException("Del'ing names is not supported")

        assert isinstance(node.ctx, ast.Load), "Unexpected Store in visit_Name"

        return Name(type_=self.names[node.id], ident=node.id, ctx=ExprContext.LOAD)


def lower_ast_to_hir(ast: ast.AST):
    visitor = AstVisitor()
    return visitor.visit(ast)