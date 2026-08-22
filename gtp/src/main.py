from pathlib import Path
import sys

from lark import Lark

from gtp.src.parsers import GTPVisitor

script_path = str(Path(__file__).resolve().parent)
header_parser = Lark(open(script_path + '/gtp-header.lark').read())
parser = Lark(open(script_path + '/gtp2.lark').read())
scopes = [dict()]
readonly_names = set()


class GTPBlock:

    def __init__(self, scopes: list[dict], readonlies: set, outputs: list[str], start_line : int, start_col : int, 
                 contents : str):
        self.scopes = scopes
        self.readonlies = readonlies
        self.outputs = outputs
        self.start_line = start_line
        self.start_col = start_col
        self.parse_tree = parser.parse(contents)
        print(self.parse_tree.pretty())

    def run(self) -> list[str]:
        interpreter = GTPVisitor(self.scopes, self.readonlies, self.outputs)
        interpreter.visit(self.parse_tree)
        return interpreter.outputs


def add_partial_line(output_lines : list[str], text : str):
    if (len(output_lines) > 0):
        output_lines[-1] += text
    else:
        output_lines.append(text)


if __name__ == '__main__':
    file_name = sys.argv[1] if len(sys.argv) >= 2 else 'test.txt.gtp'

    # This is necessary to prevent overwriting the input file if the .gtp extension is missing.
    if not file_name.endswith('.gtp'):
        raise ValueError(f"Cannot generate code from file '{file_name}': it lacks the .gtp exension.")

    # Instead of parsing the entire file with the GTP grammar, we separate it into raw text and individual code blocks.
    # Those code blocks are then parsed individually. This is so syntax errors in a code block are recognized as such 
    # instead of being interpreted as raw text and copied to the output file.

    with open(file_name, 'r') as template:

        lines = template.readlines()

        output_files = [file_name.removesuffix('.gtp')]
        skip_first_line = False
        for line in lines:
            if line.startswith('['):
                if (closing := line.find(']', 1)) == -1:
                    raise SyntaxError(f"{file_name}:1: Expected ']' to close '[additional-files' on line 1")
                skip_first_line = True
                tree = header_parser.parse(line[:closing + 1])
                for filename in tree.children:
                    output_files.append(str(filename))
            break

        readonly_names.add('OUTPUT_FILE')

        for filename in output_files:

            line_number = 0
            block_start_line = -1
            block_start_column = -1
            inputs = []

            scopes[0]['OUTPUT_FILE'] = filename

            for line in lines:

                if not skip_first_line or line_number > 0:

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
                            inputs.append(GTPBlock(scopes, readonly_names, outputs, block_start_line, block_start_column, 
                                                   block))
                            block_start_line = -1

                line_number += 1

            # Opened a new GTP block before closing the previous one, or reached EOF without closing the block
            if block_start_line != -1:
                raise SyntaxError(f"{file_name}:{line_number + 1}: Expected '?>' to close '<?gtp' on line "
                                    f"{block_start_line + 1}.")

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

            with open(filename, 'w') as output_file:

                for line in outputs:
                    output_file.write(line)
