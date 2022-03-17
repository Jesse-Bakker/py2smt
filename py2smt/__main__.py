import argparse
import sys

from py2smt.check import check_inner

parser = argparse.ArgumentParser(description="Program validator for python")
parser.add_argument("--output-smt", dest="output_smt", action="store_true")
parser.add_argument("file", action="store", type=argparse.FileType("r"))

args = parser.parse_args(sys.argv[1:])
_, smt, errors = check_inner(args.file.read())

if args.output_smt:
    print("\n".join(smt))
if errors:
    print(errors)
    sys.exit(1)
sys.exit(0)
