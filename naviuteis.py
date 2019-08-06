# @SECTION: Funções uteis que manipulam os dados independentemente do bot

def listarArgumentos(string):
	# @NOTE: Estou fazendo a divisão da string para varias chaves de argumentos, seria realmente necessário fazer isso do zero, deve existir já uma biblioteca que faça isso
	args = []
	flags = {}
	buffer = ""
	stringAtiva = False
	stringEscape = False

	# @NOTE: Simplificar o código abaixo
	for c in string:
		if not stringAtiva:
			if c == "\"":
				stringAtiva = True
			elif c != " ":
				buffer += c
			else:
				if len(buffer) > 0:
					args.append(buffer)
					buffer = ""
		else:
			if c == "\\":
				if not stringEscape:
					stringEscape = True
				else:
					stringEscape = False
					buffer += c
			elif c == "\"":
				if stringEscape:
					stringEscape = False
					buffer += c
				else:
					stringAtiva = False
					args.append(buffer)
					buffer = ""
			else:
				stringEscape = False
				buffer += c

	if len(buffer) > 0:
		args.append(buffer)

	i = 0
	while i < len(args):
		arg = args[i]

		if arg.startswith("--"):
			kv = arg.split("=")

			if len(kv) > 1:
				flags[kv[0][2:]] = "=".join(kv[1:])
				
				args.remove(arg)
				i = i - 1
			else:
				if len(kv[0][2:]) > 0:
					flags[kv[0][2:]] = True
					
					args.remove(arg)
					i = i - 1

		elif arg.startswith("-"):
			if len(arg) > 1:
				flags[arg[1:]] = True
				
				args.remove(arg)
				i = i - 1

		i = i + 1

	return args, flags