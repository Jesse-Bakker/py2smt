import ast

from py2smt import hir, lir, mir


def compile(text: str):
    syntax = ast.parse(text)
    hir_ = hir.lower_ast_to_hir(syntax)
    mir_ = mir.lower_hir_to_mir(hir_)
    lir_ = lir.lower_mir_to_lir(mir_)
    return "\n".join(x.to_smt() for x in lir_)
