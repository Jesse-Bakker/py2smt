import ast

import z3

from py2smt import hir, lir, mir


class CheckFailed(Exception):
    pass


def check_inner(text: str):
    syntax = ast.parse(text)
    hir_ = hir.lower_ast_to_hir(syntax)
    mir_ = mir.lower_hir_to_mir(hir_)
    lir_ = lir.lower_mir_to_lir(mir_)

    smt_strs = []
    decls = {}
    for decl in lir_.function_defs:
        ident = decl.ident.ident
        decls[ident] = z3.Function(ident, *decl.args, decl.sort)
        smt_strs.append(decl.to_smt())

    solver = z3.SimpleSolver()
    error = None

    for stmt in lir_.body:
        smt_strs.append(stmt.to_smt())
        if isinstance(stmt, lir.ValidityScope):
            assumptions = z3.parse_smt2_string(
                "".join(a.to_smt() for a in stmt.assumptions), decls=decls
            )
            test_str = f"(assert (not {stmt.test.to_smt()}))"
            test = z3.parse_smt2_string(test_str, decls=decls)
            solver.push()
            solver.add(test)
            if solver.check(*assumptions) != z3.unsat:
                error = CheckFailed()
            solver.pop()
        else:
            parsed = z3.parse_smt2_string(stmt.to_smt(), decls=decls)
            solver.add(*parsed)
    if solver.check() != z3.sat:
        error = CheckFailed()
    return (solver, smt_strs, error)


def get_smt(text: str):
    _, smt_strs, _ = check_inner(text)
    return smt_strs


def check(text: str):
    _, _, error = check_inner(text)
    if error:
        raise error
