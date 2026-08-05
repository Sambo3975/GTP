from lark import Lark

parser = Lark(open('template.lark').read())


if __name__ == '__main__':
    with open('test.template') as f:
        text = f.read()
    tree = parser.parse(text)
    print(tree.pretty())
