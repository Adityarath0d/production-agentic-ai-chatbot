import ast
import math

from langchain_core.tools import tool


@tool
def calculator(expression: str) -> str:
    """Evaluate a basic mathematical expression safely.

    Supports arithmetic operators, parentheses, and functions/constants from
    Python's ``math`` module (for example, ``sqrt(16)`` or ``sin(pi / 2)``).
    """
    allowed_names = {
        name: value
        for name, value in vars(math).items()
        if not name.startswith("_")
    }
    allowed_operators = (
        ast.Add,
        ast.Sub,
        ast.Mult,
        ast.Div,
        ast.FloorDiv,
        ast.Mod,
        ast.Pow,
        ast.UAdd,
        ast.USub,
    )

    def evaluate(node: ast.AST) -> int | float:
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return node.value
        if isinstance(node, ast.Name) and node.id in allowed_names:
            value = allowed_names[node.id]
            if isinstance(value, (int, float)):
                return value
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, allowed_operators):
            operand = evaluate(node.operand)
            return +operand if isinstance(node.op, ast.UAdd) else -operand
        if isinstance(node, ast.BinOp) and isinstance(node.op, allowed_operators):
            left, right = evaluate(node.left), evaluate(node.right)
            operations = {
                ast.Add: lambda: left + right,
                ast.Sub: lambda: left - right,
                ast.Mult: lambda: left * right,
                ast.Div: lambda: left / right,
                ast.FloorDiv: lambda: left // right,
                ast.Mod: lambda: left % right,
                ast.Pow: lambda: left**right,
            }
            return operations[type(node.op)]()
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id in allowed_names
            and callable(allowed_names[node.func.id])
            and not node.keywords
        ):
            return allowed_names[node.func.id](*(evaluate(arg) for arg in node.args))
        raise ValueError("Unsupported expression")

    try:
        parsed = ast.parse(expression, mode="eval")
        return str(evaluate(parsed.body))
    except (ArithmeticError, SyntaxError, TypeError, ValueError) as error:
        return f"Unable to calculate expression: {error}"