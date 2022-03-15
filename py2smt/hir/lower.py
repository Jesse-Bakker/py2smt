import ast
from typing import Iterable, List

from py2smt.exceptions import IllegalOperationException
from py2smt.hir.types import (
    Assert,
    Assign,
    BinExpr,
    BinOperator,
    Constant,
    Expr,
    ExprContext,
    ExprStmt,
    FuncDef,
    If,
    Module,
    Name,
    Pass,
    Stmt,
    UnaryExpr,
    UnaryOperator,
    UnsupportedException,
)


class AstVisitor(ast.NodeVisitor):
    def __init__(self):
        super().__init__()
        self.names = {}

    def generic_visit(self, node):
        print(node)
        assert False, "Unreachable"

    def visit_Compare(self, node: ast.Compare):
        if len(node.comparators) > 1:
            raise UnsupportedException("Chained comparisons are not supported")
        lhs = self.visit(node.left)
        rhs = self.visit(node.comparators[0])
        op = node.ops[0]

        if isinstance(op, ast.NotEq):
            return UnaryExpr(
                type_=bool,
                op=UnaryOperator.NOT,
                operand=BinExpr(lhs=lhs, rhs=rhs, op=BinOperator.EQ, type_=bool),
            )

        BO = BinOperator
        operator_map = {
            ast.Eq: BO.EQ,
            ast.Lt: BO.MUL,
            ast.LtE: BO.DIV,
            ast.Gt: BO.GT,
            ast.GtE: BO.POW,
        }
        return BinExpr(type_=bool, lhs=lhs, rhs=rhs, op=operator_map[type(op)])

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
        stmts = self.flatten_stmts([self.visit(stmt) for stmt in node.body])
        return Module(body=stmts)

    def visit_UnaryOp(self, node: ast.UnaryOp):
        op = node.op
        operand = self.visit(node.operand)

        if isinstance(op, ast.UAdd):
            return operand
        elif isinstance(op, ast.Not):
            return UnaryExpr(
                type_=bool, op=UnaryOperator.NOT, operand=self.expr_to_bool(operand)
            )
        elif isinstance(op, ast.USub):
            if operand.type_ not in (int, float):
                raise IllegalOperationException(
                    "The Invert operator `~` is only allowed on numeric types"
                )
            return UnaryExpr(type_=int, op=UnaryOperator.SUB, operand=operand)
        elif isinstance(op, ast.Invert):
            if operand.type_ is not int:
                raise IllegalOperationException(
                    "The Invert operator `~` is only allowed on integers"
                )
            return UnaryExpr(type_=int, op=UnaryOperator.INVERT, operand=operand)
        assert False, "Unexpected unary operator {op}"

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
                "Only `int`s and `float`s can be converted to boolean expressions"
            )

    def flatten_stmts(self, stmts: Iterable[Stmt | Iterable[Stmt]]) -> List[Stmt]:
        ret = []
        for stmt in stmts:
            if isinstance(stmt, Iterable):
                ret.extend(self.flatten_stmts(stmt))
            elif stmt is not None:
                ret.append(stmt)
        return ret

    def visit_Assert(self, node: ast.Assert):
        test: Expr = self.visit(node.test)
        test = self.expr_to_bool(test)
        return Assert(test=test)

    def visit_Assign(self, node: ast.Assign) -> List[Assign]:
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

    def visit_Name(self, node: ast.Name) -> Name:
        # We only care about loads here, as we handle stores in `visit_Assign`
        if isinstance(node.ctx, ast.Del):
            raise UnsupportedException("Del'ing names is not supported")

        assert isinstance(node.ctx, ast.Load), "Unexpected Store in visit_Name"

        return Name(type_=self.names[node.id], ident=node.id, ctx=ExprContext.LOAD)

    def visit_If(self, node: ast.If) -> If:
        test = self.expr_to_bool(self.visit(node.test))
        body = self.flatten_stmts([self.visit(stmt) for stmt in node.body])

        orelse = self.flatten_stmts([self.visit(stmt) for stmt in node.orelse])
        return If(test=test, body=body, orelse=orelse)

    def visit_Attribute(self, attr: ast.Attribute) -> Name:
        error = UnsupportedException("Attribute access is not supported")

        if isinstance(attr.value, ast.Attribute):
            if not isinstance(attr.value.value, ast.Name) or not (
                attr.value.value.id == "py2smt" and attr.value.attr == "param"
            ):
                raise error
            else:
                name = attr.attr
        elif isinstance(attr.value, ast.Name) and attr.value.id == "param":
            name = attr.attr
        else:
            raise error
        return Name(type_=self.names[name], ident=name, ctx=ExprContext.LOAD)

    def visit_FunctionDef(self, node: ast.FunctionDef):
        name = node.name

        def type_from_annotation(annotation: ast.expr):
            if isinstance(annotation, ast.Name):
                t = eval(annotation.id)
            else:
                raise UnsupportedException(
                    "Only `type` return type expressions are supported"
                )
            if t not in (int, bool, float):
                raise UnsupportedException(
                    f"Unsupported return type for function `{name}`"
                )
            return t

        return_type = type_from_annotation(node.returns) if node.returns else None
        # Only regular arguments are supported for now
        if node.args.posonlyargs or node.args.kwonlyargs or node.args.defaults:
            raise UnsupportedException(
                "Only regular, non-defaulted, type-annotated arguments are supported. "
                f"Violating function: {name}"
            )

        args = {}
        for arg in node.args.args:
            if not arg.annotation:
                raise UnsupportedException(
                    "Only type-annotated arguments are supported"
                )
            type_ = type_from_annotation(arg.annotation)
            args[arg.arg] = Name(ident=arg.arg, type_=type_, ctx=ExprContext.LOAD)

        # We use a subvisitor here so only the function arguments are in scope.
        # This prevents name clashes when resolving pre- and post-conditions
        # and the function body.
        subvisitor = AstVisitor()
        subvisitor.names = {name: arg.type_ for name, arg in args.items()}

        def resolve_condition(condition: ast.Call):
            for expr in condition.args:
                return [subvisitor.visit(expr) for expr in condition.args]

        preconditions = []
        postconditions = []
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Call):
                if not isinstance(decorator.func, ast.Name):
                    raise UnsupportedException(
                        "Higher level functions are not supported"
                    )
                if decorator.func.id == "assumes":
                    preconditions.extend(resolve_condition(decorator))
                elif decorator.func.id == "ensures":
                    postconditions.extend(resolve_condition(decorator))
                else:
                    raise UnsupportedException(
                        "Only pre- and post-condition decorators are supported"
                    )
            else:
                raise UnsupportedException(
                    "Only pre- and post-condition decorators are supported"
                )

        body = self.flatten_stmts([subvisitor.visit(stmt) for stmt in node.body])
        return FuncDef(
            name=name,
            preconditions=preconditions,
            postconditions=postconditions,
            ret_type=return_type,
            arguments=list(args.values()),
            body=body,
        )

    def visit_Pass(self, node: ast.Pass) -> Pass:
        return Pass()

    def visit_Import(self, node: ast.Import):
        if any(name != "py2smt" for name in node.names):
            raise UnsupportedException("Imports are not supported")

    def visit_ImportFrom(self, node: ast.ImportFrom):
        # Very crude. Maybe resolve the import?
        if node.module != "py2smt":
            raise UnsupportedException("Imports are not supported")


def lower_ast_to_hir(ast: ast.AST):
    visitor = AstVisitor()
    return visitor.visit(ast)
