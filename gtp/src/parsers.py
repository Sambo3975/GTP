import re
from typing import Any

from lark import ParseTree, Token, v_args
from lark.visitors import Interpreter, Transformer


class GTPVisitor(Interpreter):

    def __init__(self, scopes: list[dict], readonlies: list[set], output: list[str]):
        super().__init__()

        self.scopes = scopes
        self.readonlies = readonlies
        self.output = output
        self.transformer = GTPTransformer(scopes, readonlies, output)

    def statement(self, tree: ParseTree):
        self.visit_children(tree)

    @v_args
    def conditional(self, args: list):
        child_index = 0
        branched = False
        while child_index < len(args) - 1:
            if self._eval(args[child_index]):
                self.visit(args[child_index + 1])
                branched = True
                break
            child_index += 2
        if child_index < len(args) and not branched:
            self.visit(args[-1])


    @v_args(inline=True)
    def iterator_loop(self, iterator: Variable, iterable: Any, scope: ParseTree):
        if type(value := self._eval(iterable)) == list or type(value) == range:
            self.scopes.append(dict())
            for i in value:
                iterator.set(i)
                self.visit(scope)
            self.scopes.pop()
        raise ValueError(f"Attempt to iterate over '{iterator.name}', a(n) {type(value)} value")

    def scope(self, tree: ParseTree):
        self.scopes.append(dict())
        self.visit_children(tree)
        self.scopes.pop()

    @v_args(inline=True)
    def operation(self, op: ParseTree):
        self._eval(op)

    def _eval(self, tree: ParseTree):
        value = self.transformer.transform(tree)
        if isinstance(value, Variable):
            return value.get()
        return value


class GTPTransformer(Transformer):

    def __init__(self, scopes: list[dict], readonlies: set, output: list[str]):
        super().__init__()

        self.scopes = scopes
        self.readonlies = readonlies
        self.output = output

    @v_args(inline=True)
    def operation(self, result: Any) -> Any:
        return result

    @v_args(inline=True)
    def unary_operation(self, lhs: Any, rhs: Any) -> None:
        match lhs:
            case 'echo':
                self.output.append(self._eval(rhs))
                return None
            case _:
                raise OperationError(f"Unknown unary operator '{lhs}'")

    @v_args(inline=True)
    def binary_operation(self, lhs: Any, op: Token, rhs: Any):
        match op:
            case '=':
                if isinstance(lhs, Variable):
                    value = self._eval(rhs)
                    lhs.set(value)
                    return value
                raise OperationError(f"Cannot assign value to symbol '{lhs}': it is not a variable")
            case '==':
                return self._eval(lhs) == self._eval(rhs)
            case _:
                raise OperationError(f"Unknown binary operator '{op}'")

    @v_args(inline=True)
    def variable(self, name: Token):
        return Variable(str(name), self.scopes, self.readonlies)

    @v_args(inline=True)
    def integer(self, s: str):
        return int(s)

    @v_args(inline=True)
    def string(self, s: str):
        return s[1:-1]

    @v_args(inline=True)
    def boolean(self, s: Token):
        return True if s.type == "TRUE" else False

    def null(self, _):
        return None

    def f_string(self, l: list):
        return "".join([re.sub(r'\\(.)', r'\1', str(self._eval(x))) for x in l])

    @v_args
    def array(self, l: list):
        return [self._eval(x) for x in l]

    @v_args(inline=True)
    def indexer(self, variable: Any, index: Any):
        if isinstance(variable, Variable):
            if type(l := self._eval(variable)) == list:
                if type(i := self._eval(index)) == int:
                    return l[i]
                raise TypeError(f"Attempt to index array with '{i}', a(n) {type(i)} value")
            raise TypeError(f"Attempt to index symbol '{variable.name}', a(n) {type(l)} value")
        raise OperationError(f"Cannot index symbol '{variable}': it is not a variable")

    @v_args
    def value_range(self, args: list):
        args = [self._eval(x) for x in args]
        return range(*args)


    @staticmethod
    def _eval(value: Any):
        if isinstance(value, Variable):
            return value.get()
        return value


class OperationError(Exception):
    pass


class Variable:
    def __init__(self, name: str, scopes: list[dict], readonlies: set):
        self.name = name
        self.scopes = scopes
        self.readonlies = readonlies

    def get(self):
        """Get the value of this variable.

        Returns:
            Any: Value of the variable. None if this variable is not declared.
        """
        for i in range(len(self.scopes) - 1, -1, -1):
            if self.name in self.scopes[i]:
                return self.scopes[i][self.name]
        return None

    def set(self, value):
        """Set the value of this variable.

        Args:
            value (Any): Value to set

        Raises:
            AssignmentException: Attempt to set a readonly variable

        Returns:
            Any: Value that was set
        """
        if self.name in self.readonlies:
            raise OperationError(f"Cannot assign value to symbol '{self.name}': it is readonly")
        for i in range(len(self.scopes) - 1, -2, -1):
            if i == -1 or self.name in self.scopes[i]:
                self.scopes[i][self.name] = value
                return value
