import ast
import typing
from dataclasses import dataclass, field
from enum import Enum, auto


@dataclass
class Node:
    ast_node: typing.Optional[ast.AST] = field(compare=False, init=False)

    def __post_init__(self):
        self.ast_node = None


class UnsupportedException(Exception):
    pass


class ExprContext(Enum):
    LOAD = auto()
    STORE = auto()
    DEL = auto()


class BinOperator(Enum):
    # Boolean operators
    AND = auto()
    OR = auto()

    # Number operators
    ADD = auto()
    SUB = auto()
    MUL = auto()
    DIV = auto()
    FLOORDIV = auto()
    MOD = auto()
    POW = auto()
    LSHIFT = auto()
    RSHIFT = auto()
    BITOR = auto()
    BITXOR = auto()
    BITAND = auto()
    MATMULT = auto()

    EQ = auto()
    LT = auto()
    LTE = auto()
    GT = auto()
    GTE = auto()
    IS = auto()
    IN = auto()


class UnaryOperator(Enum):
    INVERT = auto()
    NOT = auto()
    SUB = auto()


@dataclass
class Expr(Node):
    type_: type


@dataclass
class BinExpr(Expr):
    op: BinOperator
    lhs: Expr
    rhs: Expr


@dataclass
class UnaryExpr(Expr):
    op: UnaryOperator
    operand: Expr


@dataclass
class Constant(Expr):
    value: typing.Any


@dataclass
class Stmt(Node):
    pass


@dataclass
class ExprStmt(Stmt):
    expr: Expr


@dataclass
class Assert(Stmt):
    test: Expr


@dataclass
class Name(Expr):
    ident: str
    ctx: ExprContext


@dataclass
class Assign(Stmt):
    lhs: Name
    rhs: Expr


@dataclass
class Module(Node):
    body: typing.List[Stmt]


@dataclass
class Pass(Stmt):
    pass


@dataclass
class If(Stmt):
    test: Expr
    body: typing.List[Stmt]
    orelse: typing.List[Stmt]


@dataclass
class FuncDef(Stmt):
    name: str
    preconditions: typing.List[Expr]
    postconditions: typing.List[Expr]

    ret_type: type
    arguments: typing.List[Name]
    body: typing.List[Stmt]
    pre_astnode: typing.Optional[ast.AST] = field(compare=False, default=None)
    post_astnode: typing.Optional[ast.AST] = field(compare=False, default=None)


@dataclass
class Call(Expr):
    func: str
    args: typing.List[Expr]


@dataclass
class Loop(Stmt):
    invariants: typing.List[Expr]
    test: Expr
    body: typing.List[Stmt]
    variables: typing.List[str]


@dataclass
class NamedExpr(Expr):
    assignment: Assign
    rhs: Expr
