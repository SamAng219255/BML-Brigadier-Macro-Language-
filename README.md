# BML-Brigadier-Macro-Language-
BML is a custom domain specific language designed to transpile into .mcfunction files as used in Minecraft datapacks. This repository includes a description of BML, a transpiler of BML into .mcfunction files, and build settings file for Sublime Text Editor 3 to allow building BML files from the editor. 

The sublime build file is written for Mac and Linux and can be adapted for Windows by replacing the forward slashes ("/") with back slashes ("\\") to account for the differing file path separators. The transpiler ("build_bml.py") is written in Python and functions on Mac, Linux, and Windows.
## Build Program
The build program (transpiler) requires the `regex` and `lark` libraries and uses Python 3.

The build program takes two arguments, the Lark language description and the target file, as follows:
`$ python3 build_bml.py bml.lark example.bml`
## BML Language
BML uses two types of commands, called macro commands and Minecraft commands respectively. Minecraft commands begin with a forward slash ("/") and are passed to the output file after getting reformatted. Macro commands begin with a dollar sign ("$") and indicate a task for the transpiler.

A formal description of BML can be found in bml.lark which uses ebnf to describe the language and is used by the script to parse files.
### Minecraft Commands
Minecraft commands are reformatted by removing the leading slash, replacing all whitespace outside of snbt strings with a single space character, removing all whitespace at the beginning and end of the command, and by changing the arguments of the /say and /me commands to require their arguments be placed inside of double quotation marks (").

These changes allow commands to be spread over multiple lines while writing to increase readability. I have found the greatest use out of these changes in writing length components or nbt data with nested elements, spreading the elements over multiple lines while indenting lines drastically improves their readability.

Minecraft commands cannot be used outside of a function.
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

`$namespace "<namespace>"`

This command specifies the namespace that you are working in and will be used when calling any generated function.

Defaults to `"minecraft"` if not specified.

`$buildpath "<file path>"` and `$startpath "<file path>"`

Together, these two variables specify the file path where generated functions are placed. All functions created using the `$function` command are placed at `./<build path>/function/<start path>/<function name>.mcfunction`. Trailing slashes at the end of the file path are optional.

Default to blank (the current directory, equivalent to `"./"`) if not specified.

`$generated "<file path>"`

This variable is used, along with `$buildpath` and `$startpath`, to specify where automatically generated functions as part of other commands are placed. All these functions are placed at `./<build path>/function/<start path>/<generated>/<parent function name>_<automatically generated identifiers>.mcfunction`.

Defaults to blank (the current directory, equivalent to `"./"`) if not specified.

**Replacement Rules**

`$define <rule name> { ... }`

Define a simple replacement rule. Wherever `$<rule name>$` appears in the file, it will be replaced with the contents of the braces before building.

`$define <rule name>(<argument 1>, <argument 2>, ...) { ... }`

Define a function replacement rule. Wherever `$<rule name>$(<value 1>; <value 2>; ...;)` appears in the file, it will be replaced with the contents of the braces before building. Wherever `$<argument 1>$` appears in the contents of the braces, it will be first replaced with `<value 1>` and likewise for all the listed arguments.

Rule names and arguments can only include upper and lower case letters ("A"–"Z",), numbers ("0"–"9"), and underscores ("_"). Argument names in the `$define` command must be separated by commas (",") and values given when the rule is used must end in a semicolon (";").

**Functions**

Most function commands must be used inside of a function.

`$function <function name> { ... }` or `$func <function name> { ... }`

Creates a new .mcfunction file with the given name. If this command is used inside of a function, it also adds a `/function` Minecraft command to the current function to call the function file.

Function names can only be composed of upper and lower case letters ("A"–"Z"), numbers ("0"–"9"), periods ("."), underscores ("_"), dashes ("-"), and forward slashes ("/").

`$if ( <execute arguments>; ) { ... }` or `$with ( <execute arguments>; ) { ... }` or `$execute ( <execute arguments>; ) { ... }`

Creates an automatically generated function file which is called from the current function in the format `/execute <execute arguments> run function ...`. In this way, it creates and executes a function with the conditions and context given inside the parentheses ("(" and ")"). The arguments to the execute command, found in the parentheses, must end in a semicolon.

`$if ( <execute arguments>; ) { ... } $else { ... }` or `$if ( <execute arguments>; ) { ... } $elseif ( <execute arguments>; ) { ... } $else { .. }` or `$if ( <execute arguments>; ) { ... } $else if ( <execute arguments>; ) { ... } $else { .. }`

This command creates two or more separate generated function files. Each one contains the contents of one of the pairs of braces ("{" and "}"). The values of the parentheses ("(" and ")") operate the same as the standalone `$if` command.

The "else" function is called directly from the current function (`/function ...`). All other functions are called in order from the beginning of the "else" function with an "execute...return" call (`/execute ... run return run function ...`). This makes them end execution of the else file if the conditions pass.

`$ifreturn ( <execute arguments>; ) { ... }`

Creates a generated function. Functions as a standalone `$if` command except it calls it as `/execute ... run return run function ...` instead causing the current function to end execution if it passes.

`$while ( <execute arguments>; ) { ... }` or `$w ( <execute arguments>; ) { ... }`

Creates a generated function that is called with the listed execute arguments in the current function and again at the end of its execution. This function will therefore loop until the arguments no longer pass. The arguments to the execute command, found in the parentheses, must end in a semicolon.

`$do { ... } $while ( <execute arguments>; )` or `$do { ... } $w ( <execute arguments>; )` or `$d { ... } $while ( <execute arguments>; )` or `$d { ... } $w ( <execute arguments>; )`

Creates a generated function that is called in the current function and again with the listed execute arguments at the end of its execution. This function will therefore always run at least once and then loop until the arguments do not pass. The arguments to the execute command, found in the parentheses, must end in a semicolon.

`$for (<initial command>; <execute arguments>; <increment command>;) { ... }` or `$f (<initial command>; <execute arguments>; <increment command>;) { ... }`

Creates a generated function that is called with the listed execute arguments in the current function and again at the end of its execution. Before the function is called from the current function, the initial command is executed. Before the function is called again at the end of its own execution, the increment command can be executed. Both commands can either be a Minecraft command or a `$score` command.

Both commands and the execute arguments must end in a semicolon.

**Shorthands**

All shorthand commands must be used inside of a function.

`$score <name> <score> <operator> ...` or `$s <name> <score> <operator> ...`

This command functions as a variable-use command for setting and changing scoreboard values. The number of arguments varies depending on the desired operation.

The first three arguments are always a name, score, and operator. The name can be any name to which a score can be ascribed, including selectors. The score is the technical name of a scoreboard value. The operator can be `+=`, `-=`, `*=`, `/=`, `%=`, `<`, `>`, `><`, `=`, `++`, or `--`.

If the operator is `++` or `--`, the command takes no more arguments and evaluates to `/scoreboard players add <name> <score> 1` or `/scoreboard players remove <name> <score> 1` respectively.

If the operator is `+=`, `-=`, or `=` and there is only one more argument, it must be a number and the command evaluates to `/scoreboard players add <name> <score> <number>`, `/scoreboard players remove <name> <score> <number>`, or `/scoreboard players set <name> <score> <number>` respectively.

If the operator is anything other than `--` or `++` and there are two more arguments, they must be a second name and a second score and the command evaluates to `/scoreboard players operation <name 1> <score 1> <operation> <name 2> <score 2>`.

`$scoreif ( <execute arguments>; ) <name> <score> <operator> ...` or  `$sif ( <execute arguments>; ) <name> <score> <operator> ...`

Functions as `$score` except the command is run by an execute command with the listed arguments (`/execute <execute arguments> run scoreboard ...`).

### Comments
.mcfunction comments can be added by starting with a `/#`. They are not evaluated any differently than other Minecraft commands and whitespace is compressed and trimmed the same way and the next line/command is assumed to start at the next forward slash ("/") or dollar sign ("$") that is preceded with whitespace and not inside of a double quote (") or brace ("{" and "}") bounded string or snbt object.

BML comments are designated using `$# ...` and last until the end of the line. Any characters between the beginning of the command and the end of the line are ignored.

Multi-line BML comments are designated using `$## ... ##$` and any characters between the two ends are ignored.

### Minecraft Macros

Minecraft's own macro functions can be used as normal  with the following notes. 

Minecraft functions containing macros are still preceded by a slash which comes before the dollar sign ("/$"). 

Whenever a dollar sign begins an argument, it must be escaped ("\") or else it will be treated as the beginning of a new macro command.
