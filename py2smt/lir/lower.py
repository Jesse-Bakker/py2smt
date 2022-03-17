import ast
import typing
from collections import ChainMap
from dataclasses import dataclass, field

import z3  # type: ignore

from py2smt import mir
from py2smt.visitor import Visitor


@dataclass
class Node:
    ast_node: typing.Optional[ast.AST] = field(compare=False, init=False)

    def __post_init__(self):
        self.ast_node = None


@dataclass
class Expr(Node):
    def to_smt(self):
        raise NotImplementedError


@dataclass
class Constant(Node):
    value: typing.Any

    def to_smt(self):
        return str(self.value).lower()


@dataclass
class Ident(Expr):
    ident: str

    def to_smt(self):
        return self.ident


@dataclass
class FunctionDef(Node):
    sort: z3.SortRef
    args: typing.List[z3.SortRef]
    ident: Ident

    def to_smt(self):
        return (
            f"(declare-fun {self.ident.to_smt()} ({' '.join(self.args)}) {self.sort})"
        )


@dataclass
class Assume(Node):
    expr: Expr

    def to_smt(self):
        return f"(assert {self.expr.to_smt()})"


@dataclass
class Scope(Node):
    stmts: typing.Any

    def to_smt(self):
        body = "\n".join(stmt.to_smt() for stmt in self.stmts if stmt)
        return f"""(push 1)
{body}
(pop 1)"""


@dataclass
class ValidityScope(Node):
    ctx_name: str
    test: Expr
    assumptions: typing.List[Assume]
    post: typing.List[Assume] = field(default_factory=list)

    def to_smt(self):
        assumptions = (
            ("\n" + "\n".join(ass.to_smt() for ass in self.assumptions))
            if self.assumptions
            else ""
        )
        post = (
            ("\n" + "\n".join(ass.to_smt() for ass in self.post)) if self.post else ""
        )
        return f"""(push 1){assumptions}
(assert (not {self.test.to_smt()}))
(check-sat)
(pop 1){post}"""


@dataclass
class Call(Expr):
    func: str
    args: typing.List[Expr]

    def to_smt(self):
        args = " ".join(arg.to_smt() for arg in self.args)
        return f"({self.func} {args})"


@dataclass
class Model(Node):
    function_defs: typing.List[FunctionDef]
    body: typing.List[Assume | ValidityScope]


class MirVisitor(Visitor):
    SORT_MAP = {
        int: z3.IntSort,
        bool: z3.BoolSort,
    }

    def __init__(self):
        self.func_map = ChainMap(mir.lower.PREDEFINED_FUNCTIONS)
        self.prefix = ""
        self.stmts = []
        self.decls = []
        self.call_ctr = 0
        self.in_funcdef = False
        self.ctx_name = "__main__"

    def visit_Var(self, var: mir.Var):
        scope = "_".join(str(idx) for idx in var.scope)
        prefix = self.prefix
        if var.ident == "__return__" and not self.in_funcdef:
            prefix = f"!call_{self.call_ctr}!" + prefix
        return Ident(ident=f"{prefix}{var.ident}${scope}${var.version}")

    def visit_Constant(self, constant: mir.Constant):
        return Constant(constant.value)

    def visit_Assign(self, assign: mir.Assign):
        call = Call(func="=", args=[self.visit(assign.lhs), self.visit(assign.rhs)])
        if pc := assign.path_condition:
            if len(pc) > 1:
                condition = Call(func="and", args=[self.visit(cond) for cond in pc])
            else:
                condition = self.visit(pc[0])
            call = Call(func="=>", args=[condition, call])
        call.ast_node = assign.ast_node
        self.add_stmt(Assume(call), assign)

    def visit_Module(self, module: mir.Module):
        for var in module.vars:
            self.add_const(self.visit(var), var.type_, var)

        self.func_map.maps.append(module.funcs)
        for stmt in module.body:
            self.visit(stmt)

        return Model(function_defs=self.decls, body=self.stmts)

    def visit_Call(self, call: mir.Call):
        func = self.func_map[call.func]
        return Call(func=func.ident, args=[self.visit(arg) for arg in call.args])

    def visit_Assert(self, assertion: mir.Assert):
        self.add_stmt(
            ValidityScope(
                test=self.visit(assertion.test), assumptions=[], ctx_name=self.ctx_name
            ),
            assertion,
        )

    def visit_FuncDef(self, funcdef: mir.FuncDef):
        old_ctx, self.ctx_name = funcdef.name, self.ctx_name
        prefix = self.prefix
        self.prefix = f"{prefix}{funcdef.name}!"
        self.in_funcdef = True
        for variable in funcdef.variables:
            self.add_const(self.visit(variable), variable.type_, variable)
        for a in funcdef.body:
            self.visit(a)
        self.prefix = prefix
        self.in_funcdef = False
        self.ctx_name = old_ctx

    def visit_Assumption(self, assumption: mir.Assumption):
        self.add_stmt(Assume(self.visit(assumption.expr)), assumption)

    def and_exprs(self, exprs: typing.List[Expr]):
        return Call(func="and", args=exprs)

    def add_const(self, ident: Ident, type_: type, from_: mir.Node):
        def_ = FunctionDef(sort=self.SORT_MAP[type_](), ident=ident, args=[])
        def_.ast_node = from_.ast_node
        self.decls.append(def_)

    def add_stmt(self, stmt: Node, from_: mir.Node):
        stmt.ast_node = from_.ast_node
        self.stmts.append(stmt)

    def visit_FuncCall(self, funccall: mir.FuncCall):

        preconditions = [self.visit(condition) for condition in funccall.preconditions]
        if preconditions:
            pre = self.and_exprs(preconditions)
            self.add_stmt(
                ValidityScope(test=pre, assumptions=[], ctx_name=self.ctx_name),
                funccall,
            )

        self.call_ctr += 1
        return_value = self.visit(funccall.return_value)
        self.add_const(return_value, funccall.type_, funccall)
        postconditions = [
            self.visit(condition) for condition in funccall.postconditions
        ]
        if postconditions:
            post = self.and_exprs(postconditions)
            # Assign temp var
            self.add_stmt(Assume(post), funccall)
        return return_value

    def visit_NamedExpr(self, expr: mir.NamedExpr):
        rhs = self.visit(expr.rhs)
        self.visit(expr.assignment)
        return rhs


def lower_mir_to_lir(mir: mir.Module) -> Model:
    visitor = MirVisitor()
    return visitor.visit(mir)
