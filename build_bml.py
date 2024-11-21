import os
import sys
import re
from lark import Lark, Tree
import regex
from pathlib import Path

def in_tree(tree, path):
	tree_ = tree
	for ind in path:
		tree_ = tree_.children[ind]
	return tree_

def build_score_cmd(score_tree):
	cmd_str = ''
	scoreif_mod = 0
	if score_tree.data.value == 'scoreif_cmd':
		scoreif_mod = 1
		cmd_str += 'execute ' + in_tree(score_tree, [0, 0]).value + ' run '
	cmd_str += 'scoreboard players '
	name_score = in_tree(score_tree, [0 + scoreif_mod, 0]).value
	if in_tree(score_tree, [0 + scoreif_mod]).data.value == 'selector' and not in_tree(score_tree, [0 + scoreif_mod, 1]) is None:
		name_score += in_tree(score_tree, [0 + scoreif_mod, 1, 0]).value
	name_score += ' ' + in_tree(score_tree, [1 + scoreif_mod, 0]).value
	match (len(score_tree.children) - scoreif_mod):
		case 3:
			match in_tree(score_tree, [2 + scoreif_mod, 0]).value:
				case '++':
					cmd_str += 'add '
				case '--':
					cmd_str += 'remove '
			cmd_str += name_score + ' 1'
		case 4:
			match in_tree(score_tree, [2 + scoreif_mod, 0]).value:
				case '+=':
					cmd_str += 'add '
				case '-=':
					cmd_str += 'remove '
				case '=':
					cmd_str += 'set '
				case '*=':
					cmd_str += 'multiply '
				case '/=':
					cmd_str += 'divide '
				case '%=':
					cmd_str += 'modulus '
			cmd_str += name_score + ' ' + in_tree(score_tree, [3 + scoreif_mod, 0]).value
		case 5:
			cmd_str += 'operation ' + name_score + ' ' + in_tree(score_tree, [2 + scoreif_mod, 0]).value + ' ' + in_tree(score_tree, [3 + scoreif_mod, 0]).value
			if in_tree(score_tree, [3 + scoreif_mod]).data.value == 'selector' and not in_tree(score_tree, [3 + scoreif_mod, 1]) is None:
				cmd_str += in_tree(score_tree, [3 + scoreif_mod, 1, 0]).value
			cmd_str += ' ' + in_tree(score_tree, [4 + scoreif_mod, 0]).value
	return cmd_str

def find_replacements(func_file):
	found_macros = []
	name_regex = regex.compile(r'([a-zA-Z_0-9]+)\s*(\([a-zA-Z_0-9,\s]+\))?\s*')
	value_regex = regex.compile(r'(?<={)[^{}]*({(?R)}[^{}]*)*(?=})')
	for def_match in regex.finditer(r'(^|(?<=[\n\r]))\$define\s+', func_file):
		name_match = name_regex.match(func_file, def_match.end())
		value_match = value_regex.match(func_file, name_match.end() + 1)
		macro_dict = {}
		macro_dict['name_str'] = name_match.group(1)
		macro_dict['value_str'] = value_match.group().strip()
		macro_dict['arg_strs'] = name_match.group(2)
		if not macro_dict['arg_strs'] is None:
			macro_dict['arg_strs'] = macro_dict['arg_strs'][1:-1].split(',')
		found_macros.append(macro_dict)
	return found_macros

def apply_replacements(_func_file, known_macros):
	func_file = _func_file
	args_regex = regex.compile(r'(?<=\()[^()]*(\((?R)\)[^()]*)*(?=\))')
	arg_regex = regex.compile(r'(?<=^|;|\()\s*([^"\'()]*?(?:(?:(?P<quote>[\'"])[\s\S]*?(?<!\\)[^\\]*?(?:\\\\)*?\g<quote>|\([^()]*(?R)[^()]*\))[^"\'()]*?)*?)(?=;|\))')
	for macro_dict in known_macros:
		if macro_dict['arg_strs'] is None:
			func_file = func_file.replace('$' + macro_dict['name_str'] + '$', macro_dict['value_str'])
		else:
			current_ind = 0
			while not (macro_match := regex.compile(r'\$' + macro_dict['name_str'] + r'\$\s*').search(func_file, current_ind)) is None:
				args_match = args_regex.match(func_file, macro_match.end() + 1)
				arg_val_strs = arg_regex.findall(args_match.group())
				temp_value_str = macro_dict['value_str']
				for i in range(0, len(macro_dict['arg_strs'])):
					temp_value_str = temp_value_str.replace('$' + macro_dict['arg_strs'][i].strip() + '$', arg_val_strs[i][0].strip())
				func_file = func_file[:macro_match.start()] + temp_value_str + func_file[args_match.end()+1:]
				current_ind = macro_match.start() + len(temp_value_str)
	return func_file

def process_mc_command(_cmd_str):
	cmd_str = _cmd_str.strip()
	cmd_str = regex.sub(r'[\s]+(?=(?:(?:\\.|[^"\\])*"(?:\\.|[^"\\])*")*(?:\\.|[^"\\])*\Z)', ' ', cmd_str)
	if cmd_str[:4] == 'say ' or cmd_str[:3] == 'me ':
		cmd_str = regex.sub(r'(?P<quote>[\'"])([\s\S]*?(?<!\\)[^\\]*?(\\\\)*?)\g<quote>', '\\2', cmd_str)
	return cmd_str + '\n'

def build(lang_def, file, _namespace = "minecraft", _buildpath = "", _startpath = "", _generated = "", primary=True):
	#setup variables
	namespace = _namespace
	buildpath = _buildpath
	startpath = _startpath
	generated = _generated
	layers=[]
	depth=0
	#get files
	f = open(lang_def, "r")
	bml_parser = Lark(f.read(), start="function_file", regex=True)
	f.close()
	f = open(file, "r")
	func_file = f.read()
	f.close()
	#check if root
	if primary and not (root_match := regex.match(r'\$root (?P<quote>[\'"])(?P<root_file>[\s\S]*?(?<!\\)[^\\]*?(\\\\)*?)\g<quote>', func_file)) is None:
		root_str = root_match.group('root_file')
		print('Found root file: ' + root_str)
		ret = build(lang_def, root_str, _namespace, _buildpath, _startpath, _generated, False)
		if ret < 0:
			print("Failed to get root: " + root_str)
			return ret
		return 0
	#Perform replacements
	func_file = regex.sub(r'\$#[^\n\r]*', '', func_file)
	known_macros = find_replacements(func_file)
	for import_match in regex.finditer(r'(^|(?<=[\n\r]))\$import\s+(?P<quote>[\'"])(?P<import_file>[\s\S]*?(?<!\\)[^\\]*?(\\\\)*?)\g<quote>', func_file):
		f = open(import_match.group('import_file'), "r")
		import_file = f.read()
		f.close()
		known_macros.extend(find_replacements(import_file))
	func_file = apply_replacements(func_file, known_macros)
	#Process commands
	layers = [{'tree':bml_parser.parse(func_file),'ind':0,'type':'root'}]
	lastType=''
	while(len(layers) > 0):
		if layers[0]["ind"] >= len(layers[0]["tree"].children):
			if len(layers) > 1:
				if layers[0]['type'] == 'loop':
					layers[0]['cmd_str'] += layers[0]['tail']
				parent_dir = os.path.dirname(os.path.join('.', layers[0]['filename']))
				Path(parent_dir).mkdir(parents=True, exist_ok=True)
				f = open(layers[0]['filename'], 'w')
				f.write(layers[0]['cmd_str'])
				f.close()
				print('Created function: ' + layers[0]['filename'])
			lastType=layers[0]['type']
			layers.pop(0)
			if len(layers) > 0:
				if layers[0]['type'] == 'ifelse':
					if layers[0]['if_ind'] < layers[0]['if_func_count']:
						condition = in_tree(layers[0]['if_functions'][layers[0]['if_ind']], [0, 0])
						function_name = layers[0]['function_name'] + '_' + str(layers[0]['if_ind'] + 2)
						layers[0]["cmd_str"] += 'execute ' + condition + ' run return run function ' + namespace + ':' + (startpath.replace(os.sep, '/') + '/' if len(startpath) > 0 else '') + (generated.replace(os.sep, '/') + '/' if len(generated) > 0 else '') + function_name.replace(os.sep, '/') + '\n'
						layers.insert(0, {
							'tree': in_tree(layers[0]['if_functions'][layers[0]['if_ind']], [1]),
							'ind': 0,
							'cmd_str': "",
							'filename': os.path.join(buildpath, "function", startpath, generated, function_name + ".mcfunction"),
							'function_name': function_name,
							'directory': os.path.join(buildpath, "function", startpath, generated),
							'if_count': 0,
							'loop_count': 0,
							'type': 'if'
						})
						layers[1]['if_ind'] += 1
						continue
					elif lastType != 'if':
						layers[0]['ind'] += 1
				else:
					layers[0]['ind'] += 1
		else:
			match in_tree(layers[0]["tree"], [layers[0]["ind"]]).data.value:
				case 'macro_command':
					#macro command code
					match in_tree(layers[0]["tree"], [layers[0]["ind"], 0]).data.value:
						case "function_cmd":
							function_name = in_tree(layers[0]["tree"], [layers[0]["ind"], 0, 0]).value
							if len(layers) > 1:
								layers[0]["cmd_str"] += 'function ' + namespace + ':' + (startpath.replace(os.sep, '/') + '/' if len(startpath) > 0 else '') + function_name.replace(os.sep, '/') + '\n'
							layers.insert(0, {
								'tree': in_tree(layers[0]["tree"], [layers[0]["ind"], 0, 1]),
								'ind': 0,
								'cmd_str': "",
								'filename': os.path.join(buildpath, "function", startpath, function_name + ".mcfunction"),
								'function_name': function_name,
								'directory': os.path.join(buildpath, "function", startpath),
								'if_count': 0,
								'loop_count': 0,
								'type': 'function'
							})
							continue
						case "while_cmd":
							if len(layers) == 1:
								print("\"while\" macro commands may only appear inside a function.")
								return -1
							layers[0]['loop_count'] += 1
							function_name = layers[0]['function_name'] + '_loop_' + str(layers[0]['loop_count'])
							condition = in_tree(layers[0]["tree"], [layers[0]["ind"], 0, 0, 0])
							call_str = 'execute ' + condition + ' run function ' + namespace + ':' + (startpath.replace(os.sep, '/') + '/' if len(startpath) > 0 else '') + (generated.replace(os.sep, '/') + '/' if len(generated) > 0 else '') + function_name.replace(os.sep, '/') + '\n'
							layers[0]["cmd_str"] += call_str
							layers.insert(0, {
								'tree': in_tree(layers[0]["tree"], [layers[0]["ind"], 0, 1]),
								'ind': 0,
								'cmd_str': "",
								'filename': os.path.join(buildpath, "function", startpath, generated, function_name + ".mcfunction"),
								'function_name': function_name,
								'directory': os.path.join(buildpath, "function", startpath, generated),
								'if_count': 0,
								'loop_count': 0,
								'type': 'loop',
								'tail': call_str
							})
							continue
						case "do_while_cmd":
							if len(layers) == 1:
								print("\"do\" macro commands may only appear inside a function.")
								return -1
							layers[0]['loop_count'] += 1
							function_name = layers[0]['function_name'] + '_loop_' + str(layers[0]['loop_count'])
							condition = in_tree(layers[0]["tree"], [layers[0]["ind"], 0, 1, 0])
							call_str = 'function ' + namespace + ':' + (startpath.replace(os.sep, '/') + '/' if len(startpath) > 0 else '') + (generated.replace(os.sep, '/') + '/' if len(generated) > 0 else '') + function_name.replace(os.sep, '/') + '\n'
							layers[0]["cmd_str"] += call_str
							layers.insert(0, {
								'tree': in_tree(layers[0]["tree"], [layers[0]["ind"], 0, 0]),
								'ind': 0,
								'cmd_str': "",
								'filename': os.path.join(buildpath, "function", startpath, generated, function_name + ".mcfunction"),
								'function_name': function_name,
								'directory': os.path.join(buildpath, "function", startpath, generated),
								'if_count': 0,
								'loop_count': 0,
								'type': 'loop',
								'tail': 'execute ' + condition + ' run ' + call_str
							})
							continue
						case "for_cmd":
							if len(layers) == 1:
								print("\"for\" macro commands may only appear inside a function.")
								return -1
							layers[0]['loop_count'] += 1
							function_name = layers[0]['function_name'] + '_loop_' + str(layers[0]['loop_count'])
							condition = in_tree(layers[0]["tree"], [layers[0]["ind"], 0, 1, 0])
							call_str = 'execute ' + condition + ' run function ' + namespace + ':' + (startpath.replace(os.sep, '/') + '/' if len(startpath) > 0 else '') + (generated.replace(os.sep, '/') + '/' if len(generated) > 0 else '') + function_name.replace(os.sep, '/') + '\n'
							if in_tree(layers[0]['tree'], [layers[0]['ind'], 0, 0]).data.value == 'mc_command':
								layers[0]["cmd_str"] += process_mc_command(in_tree(layers[0]['tree'], [layers[0]['ind'], 0, 0, 0]).data[1:])
							elif in_tree(layers[0]['tree'], [layers[0]['ind'], 0, 0, 0]).data.value == 'score_cmd':
								layers[0]["cmd_str"] += build_score_cmd(in_tree(layers[0]['tree'], [layers[0]['ind'], 0, 0, 0])) + '\n'
							layers[0]["cmd_str"] += call_str
							if in_tree(layers[0]['tree'], [layers[0]['ind'], 0, 2]).data.value == 'mc_command':
								call_str = process_mc_command(in_tree(layers[0]['tree'], [layers[0]['ind'], 0, 2, 0]).data[1:]) + call_str
							elif in_tree(layers[0]['tree'], [layers[0]['ind'], 0, 2, 0]).data.value == 'score_cmd':
								call_str = build_score_cmd(in_tree(layers[0]['tree'], [layers[0]['ind'], 0, 2, 0])) + '\n' + call_str
							layers.insert(0, {
								'tree': in_tree(layers[0]["tree"], [layers[0]["ind"], 0, 3]),
								'ind': 0,
								'cmd_str': "",
								'filename': os.path.join(buildpath, "function", startpath, generated, function_name + ".mcfunction"),
								'function_name': function_name,
								'directory': os.path.join(buildpath, "function", startpath, generated),
								'if_count': 0,
								'loop_count': 0,
								'type': 'loop',
								'tail': call_str
							})
							continue
						case "scoreif_cmd":
							if len(layers) == 1:
								print("\"scoreif\" macro commands may only appear inside a function.")
								return -1
							layers[0]["cmd_str"] += build_score_cmd(in_tree(layers[0]["tree"], [layers[0]["ind"], 0])) + "\n"
						case "score_cmd":
							if len(layers) == 1:
								print("\"score\" macro commands may only appear inside a function.")
								return -1
							layers[0]["cmd_str"] += build_score_cmd(in_tree(layers[0]["tree"], [layers[0]["ind"], 0])) + "\n"
						case "ifelse_cmd":
							if len(layers) == 1:
								print("\"ifelse\" macro commands may only appear inside a function.")
								return -1
							layers[0]['if_count'] += 1
							function_name = layers[0]['function_name'] + '_if_' + str(layers[0]['if_count'])
							condition = in_tree(layers[0]["tree"], [layers[0]["ind"], 0, 0, 0])
							layers[0]["cmd_str"] += 'function ' + namespace + ':' + (startpath.replace(os.sep, '/') + '/' if len(startpath) > 0 else '') + (generated.replace(os.sep, '/') + '/' if len(generated) > 0 else '') + function_name.replace(os.sep, '/') + '\n'
							inner_tree = in_tree(layers[0]["tree"], [layers[0]["ind"], 0])
							layers.insert(0, {
								'tree': inner_tree.children[-1],
								'ind': 0,
								'cmd_str': "",
								'filename': os.path.join(buildpath, "function", startpath, generated, function_name + ".mcfunction"),
								'function_name': function_name,
								'directory': os.path.join(buildpath, "function", startpath, generated),
								'if_count': 0,
								'loop_count': 0,
								'type': 'ifelse',
								'if_func_count': len(inner_tree.children) - 3,
								'if_functions': inner_tree.children[2:-1],
								'if_ind': 0
							})
							function_name += '_1'
							layers[0]["cmd_str"] += 'execute ' + condition + ' run return run function ' + namespace + ':' + (startpath.replace(os.sep, '/') + '/' if len(startpath) > 0 else '') + (generated.replace(os.sep, '/') + '/' if len(generated) > 0 else '') + function_name.replace(os.sep, '/') + '\n'
							layers.insert(0, {
								'tree': inner_tree.children[1],
								'ind': 0,
								'cmd_str': "",
								'filename': os.path.join(buildpath, "function", startpath, generated, function_name + ".mcfunction"),
								'function_name': function_name,
								'directory': os.path.join(buildpath, "function", startpath, generated),
								'if_count': 0,
								'loop_count': 0,
								'type': 'if'
							})
							continue
						case "ifelseif_cmd":
							if len(layers) == 1:
								print("\"ifelse\" macro commands may only appear inside a function.")
								return -1
							layers[0]['if_count'] += 1
							function_name = layers[0]['function_name'] + '_if_' + str(layers[0]['if_count'])
							condition = in_tree(layers[0]["tree"], [layers[0]["ind"], 0, 0, 0])
							layers[0]["cmd_str"] += 'function ' + namespace + ':' + (startpath.replace(os.sep, '/') + '/' if len(startpath) > 0 else '') + (generated.replace(os.sep, '/') + '/' if len(generated) > 0 else '') + function_name.replace(os.sep, '/') + '\n'
							inner_tree = in_tree(layers[0]["tree"], [layers[0]["ind"], 0])
							layers.insert(0, {
								'tree': Tree('mcfunction', []),
								'ind': 0,
								'cmd_str': "",
								'filename': os.path.join(buildpath, "function", startpath, generated, function_name + ".mcfunction"),
								'function_name': function_name,
								'directory': os.path.join(buildpath, "function", startpath, generated),
								'if_count': 0,
								'loop_count': 0,
								'type': 'ifelse',
								'if_func_count': len(inner_tree.children) - 2,
								'if_functions': inner_tree.children[2:],
								'if_ind': 0
							})
							function_name += '_1'
							layers[0]["cmd_str"] += 'execute ' + condition + ' run return run function ' + namespace + ':' + (startpath.replace(os.sep, '/') + '/' if len(startpath) > 0 else '') + (generated.replace(os.sep, '/') + '/' if len(generated) > 0 else '') + function_name.replace(os.sep, '/') + '\n'
							layers.insert(0, {
								'tree': inner_tree.children[1],
								'ind': 0,
								'cmd_str': "",
								'filename': os.path.join(buildpath, "function", startpath, generated, function_name + ".mcfunction"),
								'function_name': function_name,
								'directory': os.path.join(buildpath, "function", startpath, generated),
								'if_count': 0,
								'loop_count': 0,
								'type': 'if'
							})
							continue
						case "if_cmd":
							if len(layers) == 1:
								print("\"if\" macro commands may only appear inside a function.")
								return -1
							layers[0]['if_count'] += 1
							function_name = layers[0]['function_name'] + '_if_' + str(layers[0]['if_count'])
							condition = in_tree(layers[0]["tree"], [layers[0]["ind"], 0, 0, 0])
							layers[0]["cmd_str"] += 'execute ' + condition + ' run function ' + namespace + ':' + (startpath.replace(os.sep, '/') + '/' if len(startpath) > 0 else '') + (generated.replace(os.sep, '/') + '/' if len(generated) > 0 else '') + function_name.replace(os.sep, '/') + '\n'
							layers.insert(0, {
								'tree': in_tree(layers[0]["tree"], [layers[0]["ind"], 0, 1]),
								'ind': 0,
								'cmd_str': "",
								'filename': os.path.join(buildpath, "function", startpath, generated, function_name + ".mcfunction"),
								'function_name': function_name,
								'directory': os.path.join(buildpath, "function", startpath, generated),
								'if_count': 0,
								'loop_count': 0,
								'type': 'function'
							})
							continue
						case "elseif_cmd":
							if len(layers) == 1:
								print("\"elseif\" macro commands may only appear inside a function.")
								return -1
							layers[0]['if_count'] += 1
							function_name = layers[0]['function_name'] + '_if_' + str(layers[0]['if_count'])
							condition = in_tree(layers[0]["tree"], [layers[0]["ind"], 0, 0, 0])
							layers[0]["cmd_str"] += 'execute ' + condition + ' run return run function ' + namespace + ':' + (startpath.replace(os.sep, '/') + '/' if len(startpath) > 0 else '') + (generated.replace(os.sep, '/') + '/' if len(generated) > 0 else '') + function_name.replace(os.sep, '/') + '\n'
							layers.insert(0, {
								'tree': in_tree(layers[0]["tree"], [layers[0]["ind"], 0, 1]),
								'ind': 0,
								'cmd_str': "",
								'filename': os.path.join(buildpath, "function", startpath, generated, function_name + ".mcfunction"),
								'function_name': function_name,
								'directory': os.path.join(buildpath, "function", startpath, generated),
								'if_count': 0,
								'loop_count': 0,
								'type': 'function'
							})
							continue
						case "import_cmd":
							if len(layers) == 1:
								ret = build(lang_def, in_tree(layers[0]["tree"], [layers[0]["ind"], 0, 0]).value[1:-1], namespace, buildpath, startpath, generated, False)
								if ret < 0:
									print("Failed to import " + in_tree(layers[0]["tree"], [layers[0]["ind"], 0, 0]))
									return ret
							else:
								print("Additional files cannot be imported inside of a function.")
								return -1
						case "namespace_cmd":
							namespace = in_tree(layers[0]["tree"], [layers[0]["ind"], 0, 0]).value[1:-1]
						case "buildpath_cmd":
							buildpath = in_tree(layers[0]["tree"], [layers[0]["ind"], 0, 0]).value[1:-1]
							buildpath = os.path.join(*regex.split(r'/|\\', buildpath))
							if len(buildpath) > 0 and buildpath[-1] == "/":
								buildpath = buildpath[:-1]
						case "startpath_cmd":
							startpath = in_tree(layers[0]["tree"], [layers[0]["ind"], 0, 0]).value[1:-1]
							startpath = os.path.join(*regex.split(r'/|\\', startpath))
							if len(startpath) > 0 and startpath[-1] == "/":
								startpath = startpath[:-1]
						case "generated_cmd":
							generated = in_tree(layers[0]["tree"], [layers[0]["ind"], 0, 0]).value[1:-1]
							generated = os.path.join(*regex.split(r'/|\\', generated))
							if len(generated) > 0 and generated[-1] == "/":
								generated = generated[:-1]
						case "comment" | "multiline_comment" | "define_cmd" | "root_cmd":
							pass #Do nothing with it and allow the parser to move to the next command.
						case _:
							layers.reverse()
							index_str = ''
							first = True
							for layer in layers:
								if first:
									first = False
								else:
									index_str += ', '
								index_str += str(layer['ind'])
							print("Unrecognized macro command found at [ " + index_str + " ]: " + in_tree(layers[0]["tree"], [layers[0]["ind"], 0]).data.value)
							return -1
				case 'mc_command':
					#Minecraft command code.
					if len(layers) == 1:
						print("Minecraft commands must be typed in a function.")
						return -1
					else:
						layers[0]["cmd_str"] += process_mc_command(in_tree(layers[0]["tree"], [layers[0]["ind"], 0]).value[1:])
				case _:
					print("Error while iterating commands. Noncommand found.")
					return -1
			layers[0]["ind"] += 1
	return 0

if __name__=='__main__':
	build(sys.argv[1], sys.argv[2])