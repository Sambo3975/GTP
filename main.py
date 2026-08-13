from pathlib import Path
import sys

from lark import Lark
from lark.visitors import Interpreter
from lark.lexer import Token
import re

script_path = str(Path(__file__).resolve().parent)
parser = Lark(open(script_path + '/gtp.lark').read())
scopes = [dict()]


class GenerateCode(Interpreter):

    def __init__(self):
        super().__init__()

        self.outputs = []

    def statement(self, tree):
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
        self.outputs.append(str(self._get_value(tree.children[0])) + '\n')

    def enclosure(self, tree):
        """Run code in a new local scope.

        Args:
            tree (ParseTree): Enclosure node
        """
        scopes.append(dict())
        self.visit_children(tree)
        scopes.pop()

    def for_loop(self, tree):
        """Run a for loop. This creates a new inner scope for the iterator variable, then runs the enclosed expressions
        once with the iterator set to each value between the start and end values, inclusive.

        Args:
            tree (ParseTree): For loop node
        """
        scopes.append(dict())
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
        scopes.pop()

    def conditional(self, tree):
        """Evaluate a conditional branch with optional 'elif' and 'else' clauses.

        Args:
            tree (ParseTree): Conditional node
        """
        child_index = 0
        took_branch = False
        while child_index < len(tree.children) - 1:
            condition = self._get_value(tree.children[child_index])
            if condition:
                self.visit(tree.children[child_index + 1])
                took_branch = True
            child_index += 2
        if not took_branch and child_index < len(tree.children):
            self.visit(tree.children[child_index])

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
        for i in range(len(scopes) - 1, -1, -1):
            if name in scopes[i]:
                return scopes[i][name]
        return None

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
        elif literal.type == "BOOL":
            return True if tree.children[0] == 'true' else False

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
        for i in range(len(scopes) - 1, -2, -1):
            if i == -1 or name in scopes[i]:
                scopes[i][name] = value


def add_partial_line(output_lines : list[str], text : str):
    if (len(output_lines) > 0):
        output_lines[-1] += text
    else:
        output_lines.append(text)


class GTPBlock:

    def __init__(self, start_line : int, start_col : int, end_line : int, end_col : int, contents : str):
        self.start_line = start_line
        self.start_col = start_col
        self.end_line = end_line
        self.end_col = end_col
        self.parse_tree = parser.parse(contents)

    def run(self) -> list[str]:
        interpreter = GenerateCode()
        interpreter.visit(self.parse_tree)
        return interpreter.outputs


if __name__ == '__main__':
    file_name = sys.argv[1] if len(sys.argv) >= 2 else 'test.txt.gtp'

    # This is necessary to prevent overwriting the input file if the .gtp extension is missing.
    if not file_name.endswith('.gtp'):
        raise ValueError(f"Cannot generate code from file '{file_name}': it lacks the .gtp exension.")

    line_number = 0
    block_start_line = -1
    block_start_column = -1
    inputs = []

    # Instead of parsing the entire file with the GTP grammar, we separate it into raw text and individual code blocks.
    # Those code blocks are then parsed individually. This is so syntax errors in a code block are recognized as such 
    # instead of being interpreted as raw text and copied to the output file.

    with open(file_name, 'r') as template:

        for line in (lines := template.readlines()):

            if block_start_line == -1:

                if (block_start_column := line.find('<?gtp')) == -1:
                    inputs.append(line)
                else:
                    add_partial_line(inputs, line[0:block_start_column])
                    block_start_line = line_number

            else:

                # GTP blocks may not be nested, so finding another opening tag while inside one means the user failed to
                # close a block.
                if line.find('<?gtp') != -1:
                    break

                if (block_end_column := line.find('?>')) != -1:
                    block = lines[block_start_line][block_start_column + 5:]
                    for i in range(block_start_line + 1, line_number):
                        block += lines[i]
                    block += lines[line_number][:block_end_column]
                    inputs.append(GTPBlock(block_start_line, block_start_column, line_number, block_end_column, block))
                    block_start_line = -1

            line_number += 1

    # Opened a new GTP block before closing the previous one, or reached EOF without closing the block
    if block_start_line != -1:
        raise SyntaxError(f"{file_name}:{line_number + 1}: Expected '?>' to close '<?gtp' on line {block_start_line + 1}.")

    outputs = []
    for i in range(len(inputs)):
        if type(inputs[i]) == str:
            outputs += inputs[i]
        elif isinstance(inputs[i], GTPBlock):
            output_first = False
            prefix = inputs[i].start_col * ' '
            for output in inputs[i].run():
                if output_first:
                    outputs += prefix + output
                else:
                    outputs += output
                    output_first = True

    with open(file_name.removesuffix('.gtp'), 'w') as output_file:

        for line in outputs:
            output_file.write(line)
