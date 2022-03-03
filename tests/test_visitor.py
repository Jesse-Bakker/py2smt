from py2smt.visitor import Visitor


def test_visitor():
    class TestVisitor(Visitor):
        def visit_int(self, node):
            return node + 1

    vtor = TestVisitor()
    assert vtor.visit(3) == 4
