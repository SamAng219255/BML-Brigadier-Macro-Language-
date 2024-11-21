# BML-Brigadier-Macro-Language-
BML is a custom domain specific language designed to transpile into .mcfunction files as used in Minecraft datapacks. This repository includes a description of BML, a transpiler of BML into .mcfunction files, and build settings file for Sublime Text Editor 3 to allow building BML files from the editor. 

The sublime build file is written for Mac and Linux and can be adapted for Windows by replacing the forward slashes ("/") with back slashes ("\\") to account for the differing file path separators. The transpiler ("build_bml.py") is written in Python and functions on Mac, Linux, and Windows.
## Build Program
The build program (transpiler) requires the `regex` and `lark` libraries and uses Python 3.

The build program takes two arguments, the Lark language description and the target file, as follows:
`$ python3 build_bml.py bml.lark example.bml`
## BML Language
BML uses two types commands, called macro commands and Minecraft commands respectively. Minecraft commands begin with a forward slash ("/") and are passed to the output file after getting reformatted. Macro commands begin with a dollar sign ("$") and indicate a task for the transpiler.

A formal description of BML can be found in bml.lark which uses ebnf to describe the language and is used by the script to parse files.
### Minecraft Commands
Minecraft commands are reformatted by removing the leading slash, replacing all whitespace outside of snbt strings with a single space character, removing all whitespace at the beginning and end of the command, and by changing the arguments of the /say and /me commands to require their arguments be placed inside of double quotation marks (").

These changes allow commands to be spread over multiple lines while writing to increase readability. I have found the greatest use out of these changes in writing length components or nbt data with nested elements, spreading the elements over multiple lines while indenting lines drastically imporves their readability.
### Macro Commands
Each macro command gives a specific instruction to the transpiler and they roughly fall into five categories: meta commands, environment variables, replacement rules, functions, and shorthands. All file paths used by these commands automatically convert the file path separators to those of the system the transpiler is run on.

**Meta Commands**

`$root "<file path>"`

This command instructs the build program to stop building this file and instead build the file at the specified path. If this command is encountered while building an imported file, it is ignored.

This command must be the first line of the file.

`$import "<file path>"`

This command instructs the build program to pause building this file and then build the file at the specified path.

Any environment variables set prior to this command are inherited by the file and used in place of the defaults but, if any of the environment variables are changed by the imported file, they are not passed back to the current file. Conversely, any replacement rules set by the current file are not applied to files it imports though any replacement rules found in a file it directly imports are applied to the current file after the rules given in the current file.

**Environment Variables**

Environment variables include `$namespace`, `$buildpath`, `$startpath`, and `$generated`. They set specific variables in the transpiler and have a default value if not set. These variables can be specified multiple times throughout the file. They affect all functions which come after the command until the command is used again.

`$namepace "<namespace>"`

This command specifies the namepace that you are working in and will be used when calling any generated function.

Defaults to `"minecraft"` if not specified.

`$buildpath "<file path>"` and `$startpath "<file path>"`

Together, these two variables specify the file path where generated functions are placed. All functions created using the `$function` command are placed at `./<build path>/function/<start path>/<function name>.mcfunction`. Trailing slashes at the end of the file path are optional.

Default to blank (the current directory, equivalent to `"./"`) if not specified.

`$generated "<file path>"`

This variable is used, along with `$buildpath` and `$startpath`, to specify where automatically generated functions as part of other commands are placed. All these functions are placed at `./<build path>/function/<start path>/<generated>/<parent function name>_<automatically generated identifiers>.mcfunction`.

Defaults to blank (the current directory, equivalent to `"./"`) if not specified.

**Replacement Rules**

TODO

**Functions**

TODO

**Shorthands**

TODO
