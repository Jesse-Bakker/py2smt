import typing
from collections import ChainMap
from dataclasses import dataclass, field

import z3  # type: ignore

from py2smt import mir
from py2smt.visitor import Visitor


@dataclass
class Expr:
    def to_smt(self):
        raise NotImplementedError


@dataclass
class Constant:
    value: typing.Any

    def to_smt(self):
        return str(self.value).lower()


@dataclass
class Ident(Expr):
    ident: str

    def to_smt(self):
        return self.ident


@dataclass
class FunctionDef:
    sort: z3.SortRef
    args: typing.List[z3.SortRef]
    ident: Ident

    def to_smt(self):
        return (
            f"(declare-fun {self.ident.to_smt()} ({' '.join(self.args)}) {self.sort})"
        )


@dataclass
class Assume:
    expr: Expr

    def to_smt(self):
        return f"(assert {self.expr.to_smt()})"


@dataclass
class Scope:
    stmts: typing.Any

    def to_smt(self):
        body = "\n".join(stmt.to_smt() for stmt in self.stmts if stmt)
        return f"""(push 1)
{body}
(pop 1)"""


@dataclass
class ValidityScope:
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
class Model:
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
        self.stmts.append(Assume(call))

    def visit_Module(self, module: mir.Module):
        for var in module.vars:
            self.add_const(self.visit(var), var.type_)

        self.func_map.maps.append(module.funcs)
        for stmt in module.body:
            self.visit(stmt)

        return Model(function_defs=self.decls, body=self.stmts)

    def visit_Call(self, call: mir.Call):
        func = self.func_map[call.func]
        return Call(func=func.ident, args=[self.visit(arg) for arg in call.args])

    def visit_Assert(self, assertion: mir.Assert):
        self.stmts.append(
            ValidityScope(test=self.visit(assertion.test), assumptions=[])
        )

    def visit_FuncDef(self, funcdef: mir.FuncDef):
        prefix = self.prefix
        self.prefix = f"{prefix}{funcdef.name}!"
        self.in_funcdef = True
        variables = []
        for variable in funcdef.variables:
            variables.append(
                FunctionDef(
                    sort=self.SORT_MAP[variable.type_](),
                    args=[],
                    ident=self.visit(variable),
                )
            )
        self.decls.extend(variables)
        ret = Scope([self.visit(a) for a in funcdef.body])
        self.prefix = prefix
        self.stmts.append(ret)
        self.in_funcdef = False

    def visit_Assumption(self, assumption: mir.Assumption):
        self.stmts.append(Assume(self.visit(assumption.expr)))

    def and_exprs(self, exprs: typing.List[Expr]):
        return Call(func="and", args=exprs)

    def add_const(self, ident: Ident, type_: type):
        def_ = FunctionDef(sort=self.SORT_MAP[type_](), ident=ident, args=[])
        self.decls.append(def_)

    def visit_FuncCall(self, funccall: mir.FuncCall):

        preconditions = [self.visit(condition) for condition in funccall.preconditions]
        if preconditions:
            pre = self.and_exprs(preconditions)
            self.stmts.append(ValidityScope(test=pre, assumptions=[]))

        self.call_ctr += 1
        return_value = self.visit(funccall.return_value)
        self.add_const(return_value, funccall.type_)
        postconditions = [
            self.visit(condition) for condition in funccall.postconditions
        ]
        post = self.and_exprs(postconditions)
        # Assign temp var
        self.stmts.append(Assume(post))
        return return_value


def lower_mir_to_lir(mir: mir.Module) -> Model:
    visitor = MirVisitor()
    return visitor.visit(mir)
