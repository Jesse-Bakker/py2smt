import fileinput
from py2smt import compile

if __name__ == "__main__":
    source = "\n".join(fileinput.input(encoding="utf-8"))
    compile(source)
