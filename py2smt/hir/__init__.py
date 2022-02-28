"""
    The HIR (High-level Intermediate Representation) layer is an IR, which
    adds typing information and generalized a bit over the AST during lowering
"""
from .lower import lower_ast_to_hir

__ALL__ = [
    lower_ast_to_hir,
]
