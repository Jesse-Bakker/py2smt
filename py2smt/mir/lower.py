import typing
from collections import defaultdict
from dataclasses import dataclass, field

from py2smt import hir, mir
from py2smt.exceptions import IllegalOperationException
from py2smt.hir import BinOperator as BO
from py2smt.hir import UnaryOperator as UO
from py2smt.visitor import Visitor

PREDEFINED_FUNCTIONS = {
    -1: mir.Func(id=mir.FuncId(-1), ident=mir.Ident("+")),
    -2: mir.Func(id=mir.FuncId(-2), ident=mir.Ident("-")),
    -3: mir.Func(id=mir.FuncId(-3), ident=mir.Ident("*")),
    -4: mir.Func(id=mir.FuncId(-4), ident=mir.Ident("*")),
    -5: mir.Func(id=mir.FuncId(-5), ident=mir.Ident("/")),
    -6: mir.Func(id=mir.FuncId(-6), ident=mir.Ident("mod")),
    -7: mir.Func(id=mir.FuncId(-7), ident=mir.Ident("=")),
    -8: mir.Func(id=mir.FuncId(-8), ident=mir.Ident("<")),
    -9: mir.Func(id=mir.FuncId(-9), ident=mir.Ident("<=")),
    -10: mir.Func(id=mir.FuncId(-10), ident=mir.Ident(">")),
    -11: mir.Func(id=mir.FuncId(-11), ident=mir.Ident(">=")),
    -12: mir.Func(id=mir.FuncId(-12), ident=mir.Ident("and")),
    -13: mir.Func(id=mir.FuncId(-13), ident=mir.Ident("or")),
    -14: mir.Func(id=mir.FuncId(-14), ident=mir.Ident("not")),
    -15: mir.Func(id=mir.FuncId(-15), ident=mir.Ident("-")),
}
PREDEFINED_FUNCTION_MAP = {
    BO.ADD: -1,
    BO.SUB: -2,
    BO.MUL: -3,
    BO.MUL: -4,
    BO.DIV: -5,
    BO.MOD: -6,
    BO.EQ: -7,
    BO.LT: -8,
    BO.LTE: -9,
    BO.GT: -10,
    BO.GTE: -11,
    BO.AND: -12,
    BO.OR: -13,
    UO.NOT: -14,
    UO.SUB: -15,
}


@dataclass
class Scope:
    parent: typing.Optional["Scope"] = None
    idx: int = 0

    # Monotonically growing index. When merging subscopes, this does not reset to avoid conflicts with future subscopes
    subscope_idx: int = -1
    subscopes: typing.List["Scope"] = field(default_factory=list)
    variables: typing.Dict[mir.Ident, typing.List[mir.Var]] = field(
        default_factory=dict
    )
    _condition: typing.Optional[mir.Expr] = None

    @property
    def condition(self):
        return [
            parent._condition
            for parent in self.iter_parents()
            if parent._condition is not None
        ]

    def iter_parents(self):
        it = self
        while it is not None:
            yield it
            it = it.parent

    def subscope(self, condition=None) -> "Scope":
        self.subscope_idx += 1
        new = Scope(
            parent=self, idx=self.subscope_idx, subscopes=[], _condition=condition
        )
        self.subscopes.append(new)
        return new

    def canonical_idx(self) -> typing.List[int]:
        return list(reversed([scope.idx for scope in self.iter_parents()]))

    def resolve_var(self, ident: mir.Ident) -> mir.Var:
        """Resolve variable by identifier from this subscope upwards"""
        for scope in self.iter_parents():
            try:
                return scope.variables[ident][-1]
            except KeyError:
                pass
        else:
            raise IllegalOperationException("Cannot LOAD undefined variable")

    def reconcile_subscopes(self) -> (typing.List[mir.Assign]):
        """Pop direct subscopes and emit the proper assignments for reconciling them"""
        new_vars: typing.Dict[mir.Ident, mir.Var] = dict()
        assignments = []
        for scope in self.subscopes:
            for ident, versions in scope.variables.items():
                # Create new var in this scope
                new_var = self._make_var(ident, versions[-1].type_)
                var = new_vars.setdefault(ident, new_var)

        for var in new_vars.values():
            # Emit assignment of the new variable to the last version in this scope, under its path condition
            for scope in self.subscopes:
                assignments.append(
                    mir.Assign(
                        path_condition=scope.condition,
                        lhs=var,
                        rhs=scope.resolve_var(var.ident),
                    )
                )
                # Then add all versions of the variable to this scope's versions.
                # This is sound, because we later add the new version for this specific
                # scope as well, to which the ident will then resolve in this scope
                # and future subscopes.
                self.variables.setdefault(var.ident, []).extend(
                    scope.variables.get(var.ident, [])
                )

            self.variables.setdefault(var.ident, []).append(var)

        return assignments

    def _make_var(self, ident: mir.Ident, type_: type) -> mir.Var:
        versions = self.variables.get(ident, [])
        new = mir.Var(
            type_=type_, version=len(versions), scope=self.canonical_idx(), ident=ident
        )
        return new

    def store_var(self, ident: mir.Ident, type_: type) -> mir.Var:
        new = self._make_var(ident, type_)
        self.variables.setdefault(ident, []).append(new)
        return new


class HirVisitor(Visitor):
    def __init__(self):
        self.variables = defaultdict(list)
        self.functions = []
        self.func_map = {}

        self.scope = Scope()

    def push_scope(self, condition=None) -> Scope:
        self.scope = self.scope.subscope(condition)
        return self.scope

    def pop_scope(self) -> Scope:
        assert self.scope.parent is not None
        scope = self.scope
        self.scope = self.scope.parent
        return scope

    def visit_Name(self, name: hir.Name) -> mir.Var:
        if name.ctx == hir.ExprContext.STORE:
            self.scope.store_var(
                type_=name.type_,
                ident=mir.Ident(name.ident),
            )
        return self.scope.resolve_var(name.ident)

    def visit_Assert(self, assertion: hir.Assert) -> mir.Assert:
        return mir.Assert(
            path_condition=self.scope.condition, test=self.visit(assertion.test)
        )

    def visit_Assign(self, assign: hir.Assign) -> mir.Assign:
        lhs = self.visit(assign.lhs)
        rhs = self.visit(assign.rhs)
        return mir.Assign(path_condition=self.scope.condition, lhs=lhs, rhs=rhs)

    def visit_BinExpr(self, expr: hir.BinExpr):
        lhs = self.visit(expr.lhs)
        rhs = self.visit(expr.rhs)

        func = PREDEFINED_FUNCTION_MAP[expr.op]
        return mir.Call(type_=expr.type_, func=mir.FuncId(func), args=[lhs, rhs])

    def visit_UnaryExpr(self, expr: hir.UnaryExpr):
        operand = self.visit(expr.operand)
        func = PREDEFINED_FUNCTION_MAP[expr.op]
        return mir.Call(type_=expr.type_, func=mir.FuncId(func), args=[operand])

    def visit_Constant(self, expr: hir.Constant):
        return mir.Constant(type_=expr.type_, value=expr.value)

    def visit_ExprStmt(self, stmt: hir.ExprStmt):
        return mir.ExprStmt(
            path_condition=self.scope.condition, expr=self.visit(stmt.expr)
        )

    def not_expr(self, expr: mir.Expr):
        assert expr.type_ == bool
        return mir.Call(
            type_=bool, func=mir.FuncId(PREDEFINED_FUNCTION_MAP[UO.NOT]), args=[expr]
        )

    def visit_stmts(self, stmts: typing.List[hir.Stmt]):
        ret = []
        for stmt in stmts:
            if isinstance(stmt, hir.Pass):
                continue
            visited = self.visit(stmt)
            if isinstance(visited, list):
                ret.extend(visited)
            else:
                ret.append(visited)
        return ret

    def visit_If(self, if_stmt: hir.If):
        condition = self.visit(if_stmt.test)
        self.push_scope(condition)
        body_stmts = self.visit_stmts(if_stmt.body)
        self.pop_scope()
        self.push_scope(self.not_expr(condition))
        else_stmts = self.visit_stmts(if_stmt.orelse)
        self.pop_scope()
        extra_assigns = self.scope.reconcile_subscopes()
        return [*body_stmts, *else_stmts, *extra_assigns]

    def visit_Module(self, module: hir.Module):
        stmts = self.visit_stmts(module.body)
        return mir.Module(
            vars=[var for ident in self.scope.variables.values() for var in ident],
            body=stmts,
            funcs={},
        )


def lower_hir_to_mir(hir: hir.Module):
    visitor = HirVisitor()
    return visitor.visit(hir)
