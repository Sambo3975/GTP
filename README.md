# GTP (Generalized Text Preprocessor)

Like PHP, but for any type of file.

This is extremely early in development and lacks many basic features (useful error messages, arithmetic, array modification).

Written in Python.

## Installation

### Linux

Clone or download the source, then run the following command inside its root directory: `chmod +x install.sh && sudo ./install.sh`. This will install GTP in your `usr/bin` directory.

### Windows/Mac

You can probably get this to work on Windows or Mac, but it's currently only being developed for Linux.

If you get it to work on one of these systems, consider opening a PR that adds instructions here.

## Usage

GTP runs on files with the `NAME.EXT.gtp` naming convention, where `NAME` is the name of the file to be generated and `EXT` is the file extension of that file. For example, a GTP file named `hello.py.gtp` would generate a file named `hello.py`.

GTP code blocks are delimited with `<?gtp` and `?>` markers. Any text outside these markers will be left as-is when the output file is generated. Any number of statements may be included inside these markers. The end of each statement is marked with a semicolon `;`.

## Language Features

### Types

GTP is a loosely-typed language 3 variable types: `string`, `int`, and `array`. 

Strings are delimited using either single quotes `''` or double quotes. `""`. Escaped characters (such as `\"`) are supported.

Arrays are delimited with `{` and `}`, with values separated by commas `,`.

### Variables

Variable names can be any name that is legal in C.

Variables are set using the standard `variable = value;` syntax.

Variables are declared in the current scope the first time they are set. A variable may be accessed in any scope below the one in which it was declared.

### F-Strings

GTP also has formatted strings, marked either with `f''` or `f""`. Values inside `{}` in these strings are evaluated and catenated into the result when the string is evaluated. If you want a literal `{` in the result, escape it as `\{`.

### Echo

Use an `echo <value>;` statement to generate code in the output file. The generated code is placed at the position of the GTP block that generated it.

`value` may be an f-string, or it may be a literal or variable of any type.

### For-Loops

For-loops are declared as `for <variable> = <start>, <end> { <body> }`, with start and end being `int` values. `start` and `end` may be literals or variables. However, variables are only evaluated once at the start of the loop. The body of the loop is then run `end - start` times, once for each value between `start` and `end`, inclusive.

The iterator `variable` is created in its own scope, and can only be accessed from within the loop.

### Scope

Every variable declared between `{` and `}` is in its own local scope and cannot be accessed from a larger scope. `{` and `}` can be used without a loop to create a local scope, if desired.

## Example

Consider the following GTP script (stored in a file named `hello.py.gtp`):

```
if __name__ == '__main__':
    <? names = { 'Billy', 'Bob', 'Joe', 'Wendy', 'Laura' };
    for i = 1, 3 {
        echo f'    print("Hello, {names[i]}!")';
    } ?>
```

Running `gtp hello.py.gtp` will generate a file named `hello.py` that contains the following:

```python
if __name__ == '__main__':
    print("Hello, Billy!")
    print("Hello, Bob!")
    print("Hello, Joe!")
    print("Hello, Wendy!")
    print("Hello, Laura!")
```
