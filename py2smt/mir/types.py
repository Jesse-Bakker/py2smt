import typing
from dataclasses import dataclass, field

Ident = typing.NewType("Ident", str)


@dataclass
class Expr:
    type_: type


@dataclass
class Var(Expr):
    ident: Ident
    version: int
    scope: typing.List[int]


FuncId = typing.NewType("FuncId", int)


@dataclass
class Func:
    id: FuncId
    ident: Ident
    args: typing.List[Var] = field(default_factory=list)


@dataclass
class Call(Expr):
    func: FuncId
    args: typing.List[Expr]


@dataclass
class Stmt:
    path_condition: typing.List[Expr]


@dataclass
class ExprStmt(Stmt):
    expr: Expr


@dataclass
class Assert(Stmt):
    test: Expr


@dataclass
class Assign(Stmt):
    lhs: Var
    rhs: Expr


@dataclass
class Constant(Expr):
    value: typing.Any
