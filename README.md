# Python-to-smt converter

A python library to convert a subset of python to smtlib2

Python programs are verified using the following steps:

- Parsing the source code using python's ast module
- Lowering the AST into a High-level Intermediate Representation (HIR), which adds 
    type information, generalizes some forms of expressions and implements python's "truthiness" for using integers
    and floats as booleans in assertions
- Lowering HIR to MIR, which converts into Dynamic Single Assignment form,
    with scoping for variable names in branches and functions. This layer
    also completely desugars loops into a series of assumptions and assertions 
    and incorporates function pre- and postconditions into the function body.
- Lowering MIR to LIR, which converts to a form close to SMT that is easily convertible to it
- Running a checking routing on the LIR using z3, partly by converting LIR to SMT

All steps maintain references to the original AST nodes for counter-example generation.

# Tests
The source code is contained in the `pysmt` directory and tests in the `tests` directory.
`tests/test_smt.py` contains examples of generated SMT and the tests verify that these
are solvable with z3. `tests/test_ast_to_hir.py` tests conversion from AST to HIR.
I did not have time to implement detailed tests for the other layers or for all SMT.

`tests/integration` contains a series of input files that are automatically checked as part of the test suite.
Files ending in `_incorrect.py` are assumed incorrect and expected to fail validation.
These are all runnable using a standard python executable, with py2smt installed (so that the imports resolve).

These files demonstrate all implemented features, but I will summarize them here:

# Features

### Variables
Variables of types `bool` and `int` are supported. Trying to use other types will result in an `UnsupportedException` error.
Automatic conversion of `int` expressions to `bool` expressions, for example for use in assert statements `a = 1; assert a` is also supported.

### Operators
All arithmatic and boolean binary and unary operators that are supported in the `Core` and `Ints` theories are supported on operands of equal types.
Operands of mixed type are not supported.
The "augmented assignment" operators `+=, -=, ...` are also supported.

### Control flow
If statements are supported using path conditions and can be arbitrarily nested. While loops are supported and require loop invariants, specified using the following syntax:

```python
a = 0
while a < 10:
    loop_invariant(a >= 0)
    a += 1
```

which desugars into something like:

```python
a = 0
assert a >= 0
havoc(a)
assume a < 10 and a >= 0
a += 1
assert a >= 0
havoc(a)
assume a >= 0 and not a < 10
```

`loop_invariant` can be imported from the `py2smt` module, which makes the python code runnable. For verification, it does not need to be imported.

### Functions
Functions are supported, with a few restrictions. Firstly, recursive function calls are not supported.
Furthermore, functions require their parameters and return type to be annotated. Pre- and postconditions can be specified using the following syntax:

```python
@assumes(param.a > 0 and param.b > 0)
@ensures(__return__ == param.a + param.b)
def plus(a: int, b: int):
    return a + b
```
which desugars to:

```python
def plus(a: int, b: int):
    assume a > 0 and b > 0
    __return__ = a + b
    assert __return__ == a + b
    return __return__
```

The `param` part is importable and makes the code runnable. `@assumes(a > 0)` in the last example is also 
verifiable, but of course not runnable, because of an undefined variable.

Function calls are of course also supported, including in composite expressions

```python
a = plus(1, plus(1, 2))
```

desugars to something equivalent to:

```python
assert 1 > 0 and 2 > 0
!call_0!plus!__return__ = 1 + 2
assert 1 > 0 and !call_0!plus!__return__ > 0
!call_1!plus!__return__ = 1 + !call_0!plus!__return__
a = !call_1!plus!__return__
```

### Expr side-effects
Functions cannot have side-effects, because the only supported types are value types. Python
does have one operator that has a side effect, namely the "assignment expression" or "walrus" operator `:=`.
This is implemented by storing the `ast.NamedExpr` as an expression with an inner assignment in HIR. Then the other layers take
care of it automatically when visiting its components.

### Counter-example generation
If a program does not pass validation (and is thus satisfiable), the failing assertion is passed up from the check and the originating
statements of the declarations in the satisfiable model are included. These declarations are mapped back to their LIR nodes, which include the
original AST. These parts of the model are then formatted nicely by the command-line tool.

# Running the program
The program can be run from its top-level directory using `python -m py2smt [--output-smt] filename` and just requires z3 and the python standard library.
The `--output-smt` flag will output the SMTLIB-2 code used to validate the program, which is runnable with z3.
