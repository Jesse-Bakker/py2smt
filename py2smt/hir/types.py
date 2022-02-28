import typing
from dataclasses import dataclass
from enum import Enum, auto


class UnsupportedException(Exception):
    pass


class IllegalOperationException(Exception):
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
class Expr:
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
class Stmt:
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
class Module:
    body: typing.List[Stmt]