import ast
import typing
from dataclasses import dataclass, field

Ident = typing.NewType("Ident", str)


@dataclass
class Node:
    ast_node: typing.Optional[ast.AST] = field(compare=False, init=False)

    def __post_init__(self):
        self.ast_node = None


@dataclass
class Expr(Node):
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
class Stmt(Node):
    path_condition: typing.List[Expr]


@dataclass
class Assumption(Stmt):
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


@dataclass
class Module(Node):
    vars: typing.List[Var]
    body: typing.List[Stmt]
    funcs: typing.Mapping[FuncId, Func]


@dataclass
class FuncDef(Stmt):
    name: Ident

    ret_type: type
    variables: typing.List[Var]
    body: typing.List[Stmt]


@dataclass
class FuncCall(Expr):
    func_name: Ident
    preconditions: typing.List[Expr]
    postconditions: typing.List[Expr]
    return_value: Var


@dataclass
class Loop(Stmt):
    invariants: typing.List[Expr]
    test: Expr
    body: typing.List[Stmt]


@dataclass
class NamedExpr(Expr):
    assignment: Assign
    rhs: Expr
