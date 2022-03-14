import typing
from collections import ChainMap
from dataclasses import dataclass

import z3

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
        return str(self.value)


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
class ValidityScope:
    test: Expr
    assumptions: typing.List[Assume]

    def to_smt(self):
        assumptions = (
            ("\n" + "\n".join(ass.to_smt() for ass in self.assumptions))
            if self.assumptions
            else ""
        )
        return f"""(push 1){assumptions}
(assert (not {self.test.to_smt()}))
(check-sat)
(pop 1)"""


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

    def visit_Var(self, var: mir.Var):
        scope = "_".join(str(idx) for idx in var.scope)
        return Ident(ident=f"{var.ident}${scope}${var.version}")

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
        return Assume(call)

    def visit_Module(self, module: mir.Module):
        decls = [
            FunctionDef(sort=self.SORT_MAP[var.type_](), args=[], ident=self.visit(var))
            for var in module.vars
        ]

        for func in module.funcs:
            # TODO: add function def
            break

        self.func_map.maps.append(module.funcs)
        body = []
        for stmt in module.body:
            if (visited := self.visit(stmt)) is not None:
                body.append(visited)

        return Model(function_defs=decls, body=body)

    def visit_Call(self, call: mir.Call):
        func = self.func_map[call.func]
        return Call(func=func.ident, args=[self.visit(arg) for arg in call.args])

    def visit_Assert(self, assertion: mir.Assert):
        return ValidityScope(test=self.visit(assertion.test), assumptions=[])


def lower_mir_to_lir(mir: mir.Module) -> Model:
    visitor = MirVisitor()
    return visitor.visit(mir)
