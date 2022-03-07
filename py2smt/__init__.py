import ast
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, List

from py2smt import hir, mir
from py2smt.visitor import Visitor


@dataclass
class Expr:
    pass


@dataclass
class Ident(Expr):
    id: str

    def to_smt(self):
        return self.id


@dataclass
class Constant(Expr):
    value: Any

    def to_smt(self):
        return str(self.value)


@dataclass
class Call(Expr):
    func: str
    args: List[str]

    def to_smt(self):
        return f"({self.func} {' '.join(arg.to_smt() for arg in self.args)})"


@dataclass
class Assertion:
    expr: Expr

    def to_smt(self):
        return f"(assert {self.expr.to_smt()})"


@dataclass
class Definition:
    ident: Ident
    args: List[str]
    sort: str

    def to_smt(self):
        return (
            f"(declare-fun {self.ident.to_smt()} ({' '.join(self.args)}) {self.sort})"
        )


@dataclass
class Module:
    definitions: List[Definition]
    body: List[Assertion]

    def to_smt(self):
        return (
            "\n".join(defn.to_smt() for defn in self.definitions)
            + "\n"
            + "\n".join(assertion.to_smt() for assertion in self.body)
        )


class HirVisitor(Visitor):
    def __init__(self):
        self.assertions = []
        self.var_map = defaultdict(list)
        self.variables = []

    def get_var_name(self, ident: str):
        return Ident(f"{ident}{len(self.var_map[ident]) - 1}")

    def visit_Module(self, module: hir.Module):
        for stmt in module.body:
            self.visit(stmt)

        defs = []
        for ident_name, versions in self.var_map.items():
            for version, var_id in enumerate(versions):
                var = self.variables[var_id]
                ident = Ident(f"{ident_name}{version}")
                if var.type_ is int:
                    sort = "Int"
                elif var.type_ is bool:
                    sort = "Bool"
                else:
                    raise NotImplementedError("Only ints and bools are implemented")
                defs.append(Definition(ident=ident, args=[], sort=sort))
        return Module(definitions=defs, body=self.assertions)

    def visit_Assign(self, assign: hir.Assign):
        rhs = self.visit(assign.rhs)
        lhs = self.visit(assign.lhs)
        self.assertions.append(Assertion(Call(func="=", args=[lhs, rhs])))

    def visit_Name(self, name: hir.Name):
        if name.ctx == hir.ExprContext.STORE:
            var_id = len(self.variables)
            self.variables.append(name)
            self.var_map[name.ident].append(var_id)
        return self.get_var_name(name.ident)

    def visit_BinExpr(self, expr: hir.BinExpr):
        lhs = self.visit(expr.lhs)
        rhs = self.visit(expr.rhs)
        from .hir.types import BinOperator as BO

        op_map = {
            BO.ADD: "+",
            BO.SUB: "-",
            BO.MUL: "*",
            BO.DIV: "/",
            BO.AND: "and",
            BO.OR: "or",
            BO.EQ: "=",
        }

        op = op_map[expr.op]
        return Call(args=[lhs, rhs], func=op)

    def visit_UnaryExpr(self, expr: hir.UnaryExpr):
        operand = self.visit(expr.operand)
        from .hir.types import UnaryOperator as UO

        op_map = {
            UO.SUB: "-",
            UO.NOT: "not",
        }

        return Call(func=op_map[expr.op], args=[operand])

    def visit_Constant(self, constant: hir.Constant):
        return Constant(value=constant.value)

    def visit_Assert(self, stmt: hir.Assert):
        self.assertions.append(Assertion(self.visit(stmt.test)))


def compile(text: str):
    syntax = ast.parse(text)
    hir_ = hir.lower_ast_to_hir(syntax)
    visitor = HirVisitor()
    return visitor.visit(hir_).to_smt()
