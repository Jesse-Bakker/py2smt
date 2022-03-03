from py2smt.mir.lower import Scope
from py2smt.mir.types import Assign, Constant, Ident, Var


def test_simple_reconcile():
    scope = Scope()
    sub1 = scope.subscope()
    sub1.condition = Constant(type_=bool, value=True)
    sub1.store_var(Ident("test"), int)

    assigns = scope.reconcile_subscopes()
    assert scope.variables["test"] == [
        Var(ident=Ident("test"), type_=int, version=0, scope=[0, 0]),
        Var(ident=Ident("test"), type_=int, version=0, scope=[0]),
    ]

    assert assigns == [
        Assign(
            path_condition=[sub1.condition],
            lhs=Var(ident=Ident("test"), type_=int, version=0, scope=[0]),
            rhs=Var(ident=Ident("test"), type_=int, version=0, scope=[0, 0]),
        ),
    ]


def test_full():
    scope = Scope()
    sub1 = scope.subscope()
    assert sub1.canonical_idx() == [0, 0]

    sub2 = scope.subscope()
    assert sub2.canonical_idx() == [0, 1]

    sub1.condition = Constant(type_=bool, value=False)
    sub2.condition = Constant(type_=bool, value=True)

    scope.store_var(Ident("b"), int)

    sub1.store_var(Ident("a"), int)
    sub2.store_var(Ident("a"), int)

    sub2.store_var(Ident("b"), int)

    assigns = scope.reconcile_subscopes()
    assert scope.variables == {
        Ident("a"): [
            Var(
                version=0,
                scope=[0, 0],
                type_=int,
                ident=Ident("a"),
            ),
            Var(
                version=0,
                scope=[0, 1],
                type_=int,
                ident=Ident("a"),
            ),
            Var(
                version=0,
                scope=[0],
                type_=int,
                ident=Ident("a"),
            ),
        ],
        Ident("b"): [
            Var(
                version=0,
                scope=[0],
                type_=int,
                ident=Ident("b"),
            ),
            Var(
                version=0,
                scope=[0, 1],
                type_=int,
                ident=Ident("b"),
            ),
            Var(
                version=1,
                scope=[0],
                type_=int,
                ident=Ident("b"),
            ),
        ],
    }

    assert assigns == [
        Assign(
            path_condition=[sub1.condition],
            lhs=Var(version=0, scope=[0], type_=int, ident=Ident("a")),
            rhs=Var(version=0, scope=[0, 0], type_=int, ident=Ident("a")),
        ),
        Assign(
            path_condition=[sub2.condition],
            lhs=Var(version=0, scope=[0], type_=int, ident=Ident("a")),
            rhs=Var(version=0, scope=[0, 1], type_=int, ident=Ident("a")),
        ),
        Assign(
            path_condition=[sub1.condition],
            lhs=Var(version=1, scope=[0], type_=int, ident=Ident("b")),
            rhs=Var(version=0, scope=[0], type_=int, ident=Ident("b")),
        ),
        Assign(
            path_condition=[sub2.condition],
            lhs=Var(version=1, scope=[0], type_=int, ident=Ident("b")),
            rhs=Var(version=0, scope=[0, 1], type_=int, ident=Ident("b")),
        ),
    ]
