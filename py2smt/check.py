import ast

import z3  # type: ignore

from py2smt import hir, lir, mir


class CheckFailed(Exception):
    def __init__(self, model, context):
        self.model = model
        self.context = context


def check_inner(text: str):
    syntax = ast.parse(text)
    hir_ = hir.lower_ast_to_hir(syntax)
    mir_ = mir.lower_hir_to_mir(hir_)
    lir_ = lir.lower_mir_to_lir(mir_)

    smt_strs = []
    decls = {}
    decls_orig = {}
    for decl in lir_.function_defs:
        ident = decl.ident.ident
        decls[ident] = z3.Function(ident, *decl.args, decl.sort)
        decls_orig[ident] = decl
        smt_strs.append(decl.to_smt())

    solver = z3.SimpleSolver()
    error = None

    for stmt in lir_.body:
        smt_strs.append(stmt.to_smt())
        if isinstance(stmt, lir.ValidityScope):  # or isinstance(stmt, lir.Scope):
            solver.push()
            if isinstance(stmt, lir.ValidityScope):
                assumptions = z3.parse_smt2_string(
                    "".join(a.to_smt() for a in stmt.assumptions), decls=decls
                )
                test_str = f"(assert (not {stmt.test.to_smt()}))"
                test = z3.parse_smt2_string(test_str, decls=decls)
                solver.add(test)
            else:
                assumptions = z3.parse_smt2_string(
                    "".join(a.to_smt() for a in stmt.stmts if a)
                )
            if solver.check(*assumptions) != z3.unsat:
                model = solver.model()
                print(model)
                tuples = [
                    (model.get_interp(decl), decls_orig[decl.name()])
                    for decl in model.decls()
                ]
                error = CheckFailed(tuples, stmt)
            solver.pop()
        else:
            parsed = z3.parse_smt2_string(stmt.to_smt(), decls=decls)
            solver.add(*parsed)
    return (solver, smt_strs, error)


def get_smt(text: str):
    _, smt_strs, _ = check_inner(text)
    return smt_strs


def check(text: str):
    _, _, error = check_inner(text)
    if error:
        raise error
