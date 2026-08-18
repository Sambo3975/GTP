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


@v_args(inline=True)
class GTPTransformer(Transformer):

    def __init__(self, scopes: list[dict], readonlies: set, output: list[str]):
        super().__init__()

        self.scopes = scopes
        self.readonlies = readonlies
        self.output = output

    def operation(self, result: Any) -> Any:
        return result

    def print(self, value: Any) -> bool:
        value = self._eval(value)
        self.output.append(self.tostring(value, type(value) == list) + '\n')
        return True

    def set_value(self, lhs: Variable | Indexer, rhs: Any):
        value = self._eval(rhs)
        lhs.set(value)
        return value

    def and_(self, lhs: Any, rhs: Any):
        return self._eval(lhs) and self._eval(rhs)

    def or_(self, lhs: Any, rhs: Any):
        return self._eval(lhs) or self._eval(rhs)

    def add(self, lhs: Any, rhs: Any):
        return self._eval(lhs) + self._eval(rhs)

    def sub(self, lhs: Any, rhs: Any):
        return self._eval(lhs) - self._eval(rhs)

    def mul(self, lhs: Any, rhs: Any):
        return self._eval(lhs) * self._eval(rhs)

    def div(self, lhs: Any, rhs: Any):
        if type(lhs) is str and type(rhs) is str:
            return lhs.split(rhs)
        return self._eval(lhs) // self._eval(rhs)

    @v_args(inline=True)
    def prefix_operation(self, op: Token, var: Variable) -> int:
        value = var.get()
        match op:
            case '--':
                if type(value) == int:
                    value -= 1
                else:
                    raise ValueError(f"Attempt to decrement '{var.name}', a {type(value)} value")
            case '++':
                if type(value) == int:
                    value += 1
                else:
                    raise ValueError(f"Attempt to increment '{var.name}', a {type(value)} value")
        var.set(value)
        return value

    @v_args(inline=True)
    def postfix_operation(self, var: Variable, op: Token) -> int:
        value = var.get()
        match op:
            case '--':
                if type(value) == int:
                    var.set(value - 1)
                else:
                    raise ValueError(f"Attempt to decrement '{var.name}', a {type(value)} value")
            case '++':
                if type(value) == int:
                    var.set(value + 1)
                else:
                    raise ValueError(f"Attempt to increment '{var.name}', a {type(value)} value")
        return value

    def assignment_operation(self, var: Variable, op: Token, value: Any) -> Any:
        value = self._eval(value)
        old_value = var.get()
        match op:
            case '+=':
                value = old_value + value
            case '-=':
                value = old_value - value
            case '*=':
                value = old_value * value
            case '/=':
                value = old_value // value
            case '^=':
                value = old_value ** value
        var.set(value)
        return value

    def variable(self, name: Token):
        return Variable(str(name), self.scopes, self.readonlies)

    def integer(self, s: str):
        return int(s)

    def string(self, s: str):
        return s[1:-1]

    def boolean(self, s: Token):
        return True if s.type == "TRUE" else False

    def null(self):
        return None

    def f_string(self, *l: list):
        return "".join([re.sub(r'\\(.)', r'\1', str(self._eval(x))) for x in l])

    def array(self, *l: list):
        return [self._eval(x) for x in l]

    def indexer(self, variable: Variable, index: Any):
        return Indexer(variable, index)

    @v_args
    def value_range(self, args: list):
        args = [self._eval(x) for x in args]
        return range(*args)


    @staticmethod
    def _eval(value: Any):
        if isinstance(value, Variable):
            return value.get()
        if isinstance(value, Indexer):
            return value.get()
        return value

    @staticmethod
    def tostring(value: Any, encase_strings: bool = False):
        if type(value) is bool and value == True:
            return 'true'
        elif type(value) is bool and value == False:
            return 'false'
        elif value == None:
            return 'null'
        elif type(value) == list:
            return '{' + ', '.join([GTPTransformer.tostring(x, encase_strings) for x in value]) + '}'
        elif type(value) is str and encase_strings:
            return f'"{value}"'
        else:
            return str(value)


class OperationError(Exception):
    pass


class Indexer:

    def __init__(self, array: Variable, index: Any):
        self.array = array
        self.index = index

    def get(self):
        array, index = self._get_array_and_index()
        return array[index]

    def set(self, value: Any):
        array, index = self._get_array_and_index()
        array[index] = value
        return value

    def _get_array_and_index(self):
        array = self.array.get()
        index = self.index
        if isinstance(index, Variable):
            index = index.get()
        return array, index


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
