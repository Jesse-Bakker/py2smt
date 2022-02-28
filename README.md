# Python-to-smt converter

A python library to convert a subset of python to smtlib2

Python programs are converted to SMT using the following steps:

    - Parsing the source code using python's ast module
    - Lowering the AST into a High-level Intermediate Representation (HIR), which adds 
        type information, generalizes some forms of expressions and implements python's "truthiness" for using integers
        and floats as booleans in assertions
    - Converting the HIR to SMT directly

In the following steps, more IR's may be added, as well as a possible decorator-based or docstring-based
approach to verifying functions

The source code is contained in the `pysmt` directory and tests in the `tests` directory.
`tests/test_smt.py` contains examples of generated SMT and the tests verify that these
are solvable with z3. For now, the only way to impose constraints is through python `assert`
statements.
