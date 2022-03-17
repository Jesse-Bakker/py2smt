from py2smt.visitor import Visitor


class A:
    pass


class B:
    ast_node = None


def test_visitor():
    class TestVisitor(Visitor):
        def visit_A(self, node):
            ret = B()
            ret.b = 4
            return ret

    a = A()
    a.ast_node = 2
    vtor = TestVisitor()
    res = vtor.visit(a)
    assert res.b == 4
    assert res.ast_node == 2
