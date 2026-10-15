import builtins
import contextlib
import io
import json
import sys
import types

MAX_STEPS = 300

ALLOWED = [
    "abs", "all", "any", "ascii", "bin", "bool", "bytes", "callable", "chr", "classmethod",
    "dict", "divmod", "enumerate", "filter", "float", "format", "frozenset", "hash", "hex",
    "id", "int", "isinstance", "iter", "len", "list", "map", "max", "min", "next", "object",
    "oct", "ord", "pow", "print", "property", "range", "repr", "reversed", "round", "set",
    "slice", "sorted", "staticmethod", "str", "sum", "super", "tuple", "type", "zip",
    "BaseException", "Exception", "ValueError", "TypeError", "KeyError", "IndexError",
    "ZeroDivisionError", "StopIteration", "AttributeError", "NameError", "RuntimeError",
    "ArithmeticError", "AssertionError", "NotImplementedError",
]


class StepLimit(BaseException):
    pass


def main():
    code = sys.stdin.read()
    safe = {n: getattr(builtins, n) for n in ALLOWED if hasattr(builtins, n)}
    safe["__build_class__"] = builtins.__build_class__
    g = {"__builtins__": safe, "__name__": "__main__"}

    steps = []
    buf = io.StringIO()
    result = {"steps": steps, "output": "", "error": None, "truncated": False}

    def snapshot(frame):
        out = {}
        for k, v in frame.f_locals.items():
            if k.startswith("__"):
                continue
            if isinstance(v, (types.FunctionType, types.ModuleType, type)):
                continue
            try:
                r = repr(v)
            except Exception:
                r = "<unrepresentable>"
            out[k] = r if len(r) <= 80 else r[:77] + "..."
        return out

    def tracer(frame, event, arg):
        if frame.f_code.co_filename != "<user_code>":
            return None
        if event == "line":
            if len(steps) >= MAX_STEPS:
                raise StepLimit()
            # variables = state BEFORE this line runs
            steps.append({
                "step": len(steps) + 1,
                "line": frame.f_lineno,
                "variables": snapshot(frame),
                "output": buf.getvalue()[-2000:],
            })
        return tracer

    try:
        compiled = compile(code, "<user_code>", "exec")
    except SyntaxError as e:
        result["error"] = f"SyntaxError: {e.msg} (line {e.lineno})"
        print(json.dumps(result))
        return

    sys.settrace(tracer)
    try:
        with contextlib.redirect_stdout(buf):
            exec(compiled, g)
    except StepLimit:
        result["truncated"] = True
    except Exception as e:
        result["error"] = f"{type(e).__name__}: {e}"
    finally:
        sys.settrace(None)

    result["output"] = buf.getvalue()[-5000:]
    print(json.dumps(result))


main()