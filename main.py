from pathlib import Path
import sys

from lark import Lark
from lark.visitors import Interpreter
from lark.lexer import Token
import re

script_path = str(Path(__file__).resolve().parent)
parser = Lark(open(script_path + '/gtp.lark').read())


class GenerateCode(Interpreter):

    def __init__(self):
        super().__init__()

        self.output_file = None
        self.scopes = [dict()]

    def header(self, tree):
        self.visit(tree.children[0])

    def path(self, tree):
        """Open the output file for reading.

        Args:
            tree (ParseTree): Path node
        """
        self.output_file = open(tree.children[0], 'w')

    def body(self, tree):
        self.visit_children(tree)

    def block(self, tree):
        self.visit_children(tree)

    def expression(self, tree):
        self.visit(tree.children[0])

    def command(self, tree):
        self.visit(tree.children[0])

    def assignment(self, tree):
        """Assign a variable. If the variable exists in an enclosing scope, set its value there.
        Otherwise, set its value in the current scope.

        Args:
            tree (ParseTree): Assignment node
        """
        name = str(tree.children[0].children[0])
        value = self._get_value(tree.children[1])
        self._set_variable(name, value)

    def echo(self, tree):
        """Generate a line of code in the output file.

        Args:
            tree (ParseTree): Echo node
        """
        self.output_file.write(str(self._get_value(tree.children[0])) + '\n')

    def enclosure(self, tree):
        """Run code in a new local scope.

        Args:
            tree (ParseTree): Enclosure node
        """
        self.scopes.append(dict())
        self.visit_children(tree)
        self.scopes.pop()

    def for_loop(self, tree):
        """Run a for loop. This creates a new inner scope for the iterator variable, then runs the enclosed expressions
        once with the iterator set to each value between the start and end values, inclusive.

        Args:
            tree (ParseTree): For loop node
        """
        self.scopes.append(dict())
        name = str(tree.children[0].children[0])
        start = self._get_value(tree.children[1])
        if type(start) != int:
            raise TypeError(f"Loop start value must be int, not {type(start)}")
        end = self._get_value(tree.children[2])
        if type(end) != int:
            raise TypeError(f"Loop end value must be int, not {type(start)}")
        for i in range(start, end + 1):
            self._set_variable(name, i)
            self.visit(tree.children[3])
        self.scopes.pop()

    def raw_text(self, tree):
        """Pass raw text to the output file as-is.

        Args:
            tree (ParseTree): Raw text node
        """
        self.output_file.write(tree.children[0] + '\n')

    def _get_value(self, tree):
        """Get a value.

        Args:
            tree (ParseTree): Value node. If this has a variable, return that variable's value in the
            smallest enclosing scope in which it exists. If this has a literal, return that literal's
            value. If this has an f-string, build it into a string, and return that string.

        Returns:
            Any: Value of the node
        """
        value = tree.children[0]
        if value.data == "variable":
            return self._get_variable(value)
        elif value.data == "literal":
            return self._get_literal(value)
        elif value.data == "f_string":
            return self._get_fstring(value)
        elif value.data == "array":
            return self._get_array(value)
        elif value.data == "indexer":
            return self._get_indexer(value)

    def _get_variable(self, tree):
        """Get the value of a variable.

        Args:
            tree (ParseTree): Variable node

        Raises:
            NameError: Variable is not defined in any enclosing scope.

        Returns:
            Any: Value of the node
        """
        name = str(tree.children[0])
        for i in range(len(self.scopes) - 1, -1, -1):
            if name in self.scopes[i]:
                return self.scopes[i][name]
        raise NameError(f"name '{tree.children[0]}' is not defined")

    def _get_literal(self, tree):
        """Get the value of a literal

        Args:
            tree (ParseTree): Literal node

        Returns:
            Any: Value of the literal
        """
        literal = tree.children[0]
        if literal.type == "STRING":
            return tree.children[0][1:-1]
        elif literal.type == "INT":
            return int(tree.children[0])

    def _get_fstring(self, tree):
        """Get the result of building an f-string.

        Args:
            tree (ParseTree): F-string node

        Returns:
            str: Result of building the f-string
        """
        result = ''
        for node in tree.children:
            if isinstance(node, Token):
                result += node
            else:
                result += str(self._get_value(node))
        return re.sub(r'\\(.)', r'\1', result)

    def _get_array(self, tree):
        """Get the value of an array.

        Args:
            tree (ParseTree): Array node
        """
        result = []
        for child in tree.children:
            result.append(self._get_value(child))
        return result

    def _get_indexer(self, tree):
        """Get the value in an array at an index.

        Args:
            tree (ParseTree): Indexer node

        Raises:
            TypeError: Attempt to index a non-array variable
            TypeError: Attempt to index an array with a non-int index

        Returns:
            Any: Value from the array
        """
        target = self._get_variable(tree.children[0])
        if type(target) != list:
            raise TypeError(f"attempt to index '{tree.children[0].children[0]},' a {type(target)} value")
        index = self._get_value(tree.children[1])
        if type(index) != int:
            raise TypeError(f"array index must be int, not {type(index)}")
        return target[index]

    def _set_variable(self, name, value):
        """Set the value of a variable. If it defined in an enclosing scope, set it in that scope. Otherwise, define it 
        in the current scope and set it.

        Args:
            name (_type_): _description_
            value (_type_): _description_
        """
        for i in range(len(self.scopes) - 1, -2, -1):
            if i == -1 or name in self.scopes[i]:
                self.scopes[i][name] = value


if __name__ == '__main__':
    file_name = sys.argv[1] if len(sys.argv) == 2 else 'fastPaletteSwapUber.shadertemplate'
    with open(file_name, 'r') as template:
        tree = parser.parse(template.read())

    generator = GenerateCode()
    generator.visit(tree)
