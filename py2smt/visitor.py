class Visitor:
    def add_ast(self, node, ast_node):
        if isinstance(node, list):
            for n in node:
                self.add_ast(n, ast_node)
        elif node and not node.ast_node:
            node.ast_node = ast_node

    def visit(self, node):
        ast_node = node.ast_node
        result = getattr(self, f"visit_{type(node).__name__}")(node)
        self.add_ast(result, ast_node)
        return result
