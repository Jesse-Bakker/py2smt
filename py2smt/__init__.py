import ast
import enum
from collections import defaultdict, namedtuple


class Type(enum.Enum):
    BOOL = 1
    INT = 2


Variable = namedtuple("Variable", ["name", "type"])
Assignment = namedtuple("Assignment", ["variable", "expr"])

# Expressions
Expr = namedtuple("Expr", ["type", "resolution"])
Var = namedtuple("Var", ["id", "type"])
Const = namedtuple("Const", ["value", "type"])

Assertion = namedtuple("Assertion", ["type", "lhs", "rhs"])


class Visitor(ast.NodeVisitor):
    def __init__(self):
        super().__init__()

        self.variables = []

        self.var_map = defaultdict(list)
        self.assertions = []

    def visit_Assign(self, stmt):
        assert len(stmt.targets) == 1
        target = stmt.targets[0]
        assert isinstance(target, ast.Name)
        target: ast.Name
        name = target.id

        value = stmt.value
        match value:
            case ast.Constant(value):
                match value:
                    case int():
                        t = Type.INT
                    case bool():
                        t = Type.BOOL
                    case _:
                        raise NotImplementedError(
                            "Only int and bool types are supported"
                        )
                assignment = Assignment(
                    variable=Variable(name=name, type=t), expr=Const(value, t)
                )

            case ast.Name(value):
                var = self.var(value)
                assignment = Assignment(
                    variable=Variable(name=name, type=var.type), expr=var
                )
            case _:
                raise NotImplementedError()
        self.add_assignment(assignment)

    def add_assignment(self, assignment):
        var = assignment.variable
        self.variables.append(var)

        var_id = len(self.variables) - 1
        self.var_map[var.name].append(var_id)
        self.assertions.append(Assertion(type="=", lhs=var_id, rhs=assignment.expr))

    def var(self, name):
        # A var with a name refers to the last assigned version
        var_id = self.var_map[name][-1]
        return Var(id=var_id, type=self.variables[var_id].type)

    def to_smt(self):
        counter = defaultdict(int)
        names = []
        for var in self.variables:
            count = counter[var.name]
            names.append(f"{var.name}{count}")
            counter[var.name] += 1

        lines = []

        for i, var in enumerate(self.variables):
            match var.type:
                case Type.INT:
                    t = "Int"
                case Type.BOOL:
                    t = "Bool"
                case _:
                    print(var.type)
            lines.append(f"(declare-fun {names[i]} () {t})")

        for assertion in self.assertions:
            name = names[assertion.lhs]
            match assertion.rhs:
                case Var(id=i):
                    rhs = names[i]
                case Const(value=v):
                    rhs = str(v)
            lines.append(f"(assert ({assertion.type} {name} {rhs}))")
        return lines


class VariableType(enum.Enum):
    INT = 1
    BOOL = 2


def resolve_assign(ctx, stmt: ast.Assign):
    assert len(stmt.targets) == 1
    target = stmt.targets[0]
    assert isinstance(target, ast.Name)
    target: ast.Name
    name = target.id

    value = stmt.value
    match value:
        case ast.Constant(value):
            match value:
                case int():
                    t = Type.INT
                case bool():
                    t = Type.BOOL
                case _:
                    raise NotImplementedError("Only int and bool types are supported")
            assignment = Assignment(
                variable=Variable(name=name, type=t), expr=Const(value, t)
            )

        case ast.Name(value):
            var = ctx.var(value)
            assignment = Assignment(
                variable=Variable(name=name, type=var.type), expr=var
            )
        case _:
            raise NotImplementedError()
    ctx.add_assignment(assignment)


def compile(source: str):
    syntax = ast.parse(source)

    visitor = Visitor()
    visitor.visit(syntax)
    return visitor.to_smt()
