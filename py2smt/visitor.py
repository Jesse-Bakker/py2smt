class Visitor:
    def visit(self, node):
        return getattr(self, f"visit_{type(node).__name__}")(node)
