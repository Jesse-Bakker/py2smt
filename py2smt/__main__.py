import argparse
import ast
import sys
import traceback as tb

from py2smt.check import check_inner


def format_counterexample(filename, source_code, exc):
    frames = []
    model = exc.model
    ctx = exc.context
    for val, var in model:
        var_name = ast.get_source_segment(source_code, var.ast_node)
        frames.append(
            tb.FrameSummary(
                filename=filename,
                lineno=var.ast_node.lineno,
                name=ctx.ctx_name,
                locals={var_name: val},
            )
        )
    context_lines = tb.format_list(frames)
    failing_assert = tb.format_list(
        [
            tb.FrameSummary(
                filename=filename, lineno=ctx.ast_node.lineno, name=ctx.ctx_name
            )
        ]
    )

    return ["The following assert fails:", *failing_assert, "When:", *context_lines]


parser = argparse.ArgumentParser(description="Program validator for python")
parser.add_argument("--output-smt", dest="output_smt", action="store_true")
parser.add_argument("filename", action="store", type=str)

args = parser.parse_args(sys.argv[1:])
with open(args.filename, "r") as file:
    text = file.read()
    _, smt, errors = check_inner(text)

if args.output_smt:
    print("\n".join(smt))
if errors:
    print("\n".join(format_counterexample(args.filename, text, errors)))
    sys.exit(1)
sys.exit(0)
