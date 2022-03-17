import ast
from copy import copy
from typing import Iterable, List, Set

from py2smt.exceptions import IllegalOperationException

from . import types as hir


class AstVisitor(ast.NodeVisitor):
    def __init__(self):
        super().__init__()
        self.names = {"loop_invariant": bool}
        self.lookup_stack: List[Set[str]] = [set()]

    def add_ast(self, node, ast_node):
        if isinstance(node, list) or isinstance(node, tuple):
            for n in node:
                self.add_ast(n, ast_node)
        elif node:
            node.ast_node = ast_node

    def visit(self, node):
        result = super().visit(node)
        self.add_ast(result, node)
        return result

    def generic_visit(self, node):
        raise hir.UnsupportedException(
            f"The syntactic construct {type(node).__name__} is not supported"
        )

    def visit_Compare(self, node: ast.Compare):
        if len(node.comparators) > 1:
            raise hir.UnsupportedException(
                "Chained comparisons are not supported. Please split them into multiple comparisons"
            )
        lhs = self.visit(node.left)
        rhs = self.visit(node.comparators[0])
        op = node.ops[0]

        if isinstance(op, ast.NotEq):
            return hir.UnaryExpr(
                type_=bool,
                op=hir.UnaryOperator.NOT,
                operand=hir.BinExpr(
                    lhs=lhs, rhs=rhs, op=hir.BinOperator.EQ, type_=bool
                ),
            )

        BO = hir.BinOperator
        operator_map = {
            ast.Eq: BO.EQ,
            ast.Lt: BO.LT,
            ast.LtE: BO.LTE,
            ast.Gt: BO.GT,
            ast.GtE: BO.GTE,
        }
        return hir.BinExpr(type_=bool, lhs=lhs, rhs=rhs, op=operator_map[type(op)])

    def visit_BinOp(self, node):
        BO = hir.BinOperator
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

        lhs: hir.Expr = self.visit(node.left)
        rhs: hir.Expr = self.visit(node.right)

        type_: type
        if issubclass(lhs.type_, int) and issubclass(rhs.type_, int):
            type_ = int
        elif issubclass(rhs.type_, float) or issubclass(lhs.type_, float):
            type_ = float
        else:
            raise hir.UnsupportedException(
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
        return hir.BinExpr(lhs=lhs, rhs=rhs, op=op, type_=type_)

    def visit_BoolOp(self, node: ast.BoolOp):
        if len(node.values) > 2:
            raise hir.UnsupportedException(
                "Chained boolean operators are not supported. Please use parentheses to split them up"
            )
        lhs = self.visit(node.values[0])
        rhs = self.visit(node.values[1])

        # bool is a subclass of int
        if not issubclass(lhs.type_, (int, float)) or not issubclass(
            rhs.type_, (int, float)
        ):
            raise hir.UnsupportedException(
                "Boolean operators are only supported on bools, ints and floats"
            )

        if isinstance(node.op, ast.And):
            op = hir.BinOperator.AND
        elif isinstance(node.op, ast.Or):
            op = hir.BinOperator.OR
        else:
            assert False, "Unexpected boolean operator"

        if lhs.type_ is not rhs.type_:
            raise hir.UnsupportedException(
                "Boolean operators are only supported on operands of the same type"
            )
        return hir.BinExpr(lhs=lhs, rhs=rhs, type_=lhs.type_, op=op)

    def visit_Constant(self, node: ast.Constant):
        return hir.Constant(type_=type(node.value), value=node.value)

    def visit_Expr(self, node: ast.Expr):
        return hir.ExprStmt(expr=self.visit(node.value))

    def visit_Module(self, node: ast.Module):
        # Stmts can be split into multiple statements, for example with multiple
        # assignment: `a = b = 2 -> a = 2; b = 2`, so we unpack here
        stmts = self.flatten_stmts([self.visit(stmt) for stmt in node.body])
        return hir.Module(body=stmts)

    def visit_UnaryOp(self, node: ast.UnaryOp):
        op = node.op
        operand = self.visit(node.operand)

        if isinstance(op, ast.UAdd):
            return operand
        elif isinstance(op, ast.Not):
            return hir.UnaryExpr(
                type_=bool, op=hir.UnaryOperator.NOT, operand=self.expr_to_bool(operand)
            )
        elif isinstance(op, ast.USub):
            if operand.type_ not in (int, float):
                raise IllegalOperationException(
                    "The Invert operator `~` is only allowed on numeric types"
                )
            return hir.UnaryExpr(type_=int, op=hir.UnaryOperator.SUB, operand=operand)
        elif isinstance(op, ast.Invert):
            if operand.type_ is not int:
                raise IllegalOperationException(
                    "The Invert operator `~` is only allowed on integers"
                )
            return hir.UnaryExpr(
                type_=int, op=hir.UnaryOperator.INVERT, operand=operand
            )
        assert False, "Unexpected unary operator {op}"

    def expr_to_bool(self, expr: hir.Expr):
        if expr.type_ is bool:
            return expr

        def make_expr(type_, value):
            return hir.UnaryExpr(
                type_=bool,
                op=hir.UnaryOperator.NOT,
                operand=hir.BinExpr(
                    type_=bool,
                    lhs=expr,
                    rhs=hir.Constant(type_=type_, value=value),
                    op=hir.BinOperator.EQ,
                ),
            )

        if expr.type_ is int:
            return make_expr(int, 0)
        elif expr.type_ is float:
            return make_expr(float, 0.0)
        else:
            raise hir.UnsupportedException(
                "Only `int`s and `float`s can be converted to boolean expressions"
            )

    def flatten_stmts(
        self, stmts: Iterable[hir.Stmt | Iterable[hir.Stmt]]
    ) -> List[hir.Stmt]:
        ret = []
        for stmt in stmts:
            if isinstance(stmt, Iterable):
                ret.extend(self.flatten_stmts(stmt))
            elif stmt is not None:
                ret.append(stmt)
        return ret

    def visit_Assert(self, node: ast.Assert):
        test: hir.Expr = self.visit(node.test)
        test = self.expr_to_bool(test)
        return hir.Assert(test=test)

    def assign(self, name: ast.AST, to: hir.Expr):
        if not isinstance(name, ast.Name):
            raise hir.UnsupportedException("Only assignments to names are supported")
        type_ = to.type_
        self.names[name.id] = type_
        self.lookup_stack[-1].add(name.id)
        lhs = hir.Name(type_=type_, ident=name.id, ctx=hir.ExprContext.STORE)
        lhs.ast_node = name
        return hir.Assign(lhs=lhs, rhs=to)

    def visit_Assign(self, node: ast.Assign) -> List[hir.Assign]:
        targets = node.targets
        rhs: hir.Expr = self.visit(node.value)
        stmts = []
        for name in targets:
            if not isinstance(name, ast.Name):
                raise hir.UnsupportedException(
                    "Only assignments to names are supported"
                )
            stmts.append(self.assign(name, rhs))
        return stmts

    def visit_Name(self, node: ast.Name) -> hir.Name:
        # We only care about loads here, as we handle stores in `visit_Assign`
        if isinstance(node.ctx, ast.Del):
            raise hir.UnsupportedException("Del'ing names is not supported")

        assert isinstance(node.ctx, ast.Load), "Unexpected Store in visit_Name"

        self.lookup_stack[-1].add(node.id)
        return hir.Name(
            type_=self.names[node.id], ident=node.id, ctx=hir.ExprContext.LOAD
        )

    def visit_If(self, node: ast.If) -> hir.If:
        test = self.expr_to_bool(self.visit(node.test))
        body = self.flatten_stmts([self.visit(stmt) for stmt in node.body])

        orelse = self.flatten_stmts([self.visit(stmt) for stmt in node.orelse])
        return hir.If(test=test, body=body, orelse=orelse)

    def visit_Attribute(self, attr: ast.Attribute) -> hir.Name:
        error = hir.UnsupportedException("Attribute access is not supported")

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
        return hir.Name(type_=self.names[name], ident=name, ctx=hir.ExprContext.LOAD)

    def visit_FunctionDef(self, node: ast.FunctionDef):
        name = node.name

        def type_from_annotation(annotation: ast.expr):
            if isinstance(annotation, ast.Name):
                t = eval(annotation.id)
            else:
                raise hir.UnsupportedException(
                    "Only `type` return type expressions are supported"
                )
            if t not in (int, bool, float):
                raise hir.UnsupportedException(
                    f"Unsupported return type for function `{name}`"
                )
            return t

        return_type = type_from_annotation(node.returns) if node.returns else None
        # Only regular arguments are supported for now
        if node.args.posonlyargs or node.args.kwonlyargs or node.args.defaults:
            raise hir.UnsupportedException(
                "Only regular, non-defaulted, type-annotated arguments are supported. "
                f"Violating function: {name}"
            )

        args = {}
        for arg in node.args.args:
            if not arg.annotation:
                raise hir.UnsupportedException(
                    "Only type-annotated arguments are supported"
                )
            type_ = type_from_annotation(arg.annotation)
            args[arg.arg] = hir.Name(
                ident=arg.arg, type_=type_, ctx=hir.ExprContext.LOAD
            )
            args[arg.arg].ast_node = arg

        # We use a subvisitor here so only the function arguments are in scope.
        # This prevents name clashes when resolving pre- and post-conditions
        # and the function body.
        subvisitor = AstVisitor()
        subvisitor.names.update({name: arg.type_ for name, arg in args.items()})
        subvisitor.names["__return__"] = return_type

        def resolve_condition(condition: ast.Call):
            for expr in condition.args:
                return [subvisitor.visit(expr) for expr in condition.args]

        preconditions = []
        postconditions = []
        pre_astnode = None
        post_astnode = None
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Call):
                if not isinstance(decorator.func, ast.Name):
                    raise hir.UnsupportedException(
                        "Higher level functions are not supported"
                    )
                if decorator.func.id == "assumes":
                    preconditions.extend(resolve_condition(decorator))
                    pre_astnode = decorator
                elif decorator.func.id == "ensures":
                    postconditions.extend(resolve_condition(decorator))
                    post_astnode = decorator
                else:
                    raise hir.UnsupportedException(
                        "Only pre- and post-condition decorators are supported"
                    )
            else:
                raise hir.UnsupportedException(
                    "Only pre- and post-condition decorators are supported"
                )

        body = self.flatten_stmts([subvisitor.visit(stmt) for stmt in node.body])
        self.names[name] = return_type
        return hir.FuncDef(
            name=name,
            preconditions=preconditions,
            postconditions=postconditions,
            ret_type=return_type,
            arguments=list(args.values()),
            body=body,
            pre_astnode=pre_astnode,
            post_astnode=post_astnode,
        )

    def visit_Return(self, node: ast.Return):
        if not node.value:
            raise hir.UnsupportedException(
                "Functions must always return a value; this returns None"
            )

        # A return is an assignment to the special return value __return__
        name = hir.Name(
            type_=self.names["__return__"],
            ident="__return__",
            ctx=hir.ExprContext.STORE,
        )
        name.ast_node = node.value
        return hir.Assign(lhs=name, rhs=self.visit(node.value))

    def visit_Pass(self, node: ast.Pass) -> hir.Pass:
        return hir.Pass()

    def visit_Import(self, node: ast.Import):
        if any(name != "py2smt" for name in node.names):
            raise hir.UnsupportedException("Imports are not supported")

    def visit_ImportFrom(self, node: ast.ImportFrom):
        # Very crude. Maybe resolve the import?
        if node.module != "py2smt":
            raise hir.UnsupportedException("Imports are not supported")

    def visit_Call(self, node: ast.Call):
        if not isinstance(node.func, ast.Name):
            raise hir.UnsupportedException("Higher level functions are not supported")
        ident = node.func.id
        args = [self.visit(arg) for arg in node.args]
        return hir.Call(type_=self.names[ident], args=args, func=ident)

    def visit_While(self, node: ast.While):
        self.lookup_stack.append(set())
        test = self.visit(node.test)
        body = self.flatten_stmts([self.visit(stmt) for stmt in node.body])
        error = hir.UnsupportedException(
            "Loops without loop invariants are not supported"
        )

        try:
            invariant_stmt, body = body[0], body[1:] if len(body) > 1 else []
            if not isinstance(invariant_stmt, hir.ExprStmt) or not isinstance(
                call := invariant_stmt.expr, hir.Call
            ):
                raise error
            if not call.func == "loop_invariant":
                raise error
            invariants = call.args
        except IndexError:
            raise error
        variables = list(self.lookup_stack.pop())
        return hir.Loop(
            test=test, body=body, invariants=invariants, variables=variables
        )

    def visit_AugAssign(self, node: ast.AugAssign):
        BO = hir.BinOperator
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
        target = node.target
        if not isinstance(target, ast.Name):
            raise hir.UnsupportedException("Assigning is only supported for names")
        # Copy here, because we mutate the ast node, just in case
        target = copy(target)
        target.ctx = ast.Load()
        load = self.visit(target)
        rhs = self.visit(node.value)
        binop = hir.BinExpr(
            lhs=load, rhs=rhs, op=operator_map[type(node.op)], type_=load.type_
        )
        return self.assign(node.target, binop)

    def visit_NamedExpr(self, node: ast.NamedExpr):
        rhs = self.visit(node.value)
        assign = self.assign(node.target, rhs)
        return hir.NamedExpr(assignment=assign, rhs=rhs, type_=rhs.type_)


def lower_ast_to_hir(ast: ast.AST):
    visitor = AstVisitor()
    return visitor.visit(ast)
