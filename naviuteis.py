ANSI_ESCAPE = "\033[{}m"

ANSI_CODES = {
	"reset": "0",
	"bold": "1",
	"underline": "4",
	"blink": "5",
	"reverse": "7",
	"invisible": "8",

	"black": "30",
	"red": "31",
	"green": "32",
	"yellow": "33",
	"blue": "34",
	"magenta": "35",
	"cyan": "36",
	"white": "37",

	"bblack": "40",
	"bred": "41",
	"bgreen": "42",
	"byellow": "43",
	"bblue": "44",
	"bmagenta": "45",
	"bcyan": "46",
	"bwhite": "47"
}

# @SECTION
# Funções uteis que manipulam os dados independentemente do bot

def get_args(string):
	# @NOTE
	# Estou fazendo a divisão da string para varias chaves de argumentos e flags, provavelmente já exista
	# uma biblioteca que faça isso
	
	args = []
	flags = {}
	buffer = ""
	stringAtiva = False
	stringEscape = False

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
				if stringEscape:
					buffer += "\\"
				stringEscape = False
				buffer += c

	if len(buffer) > 0:
		args.append(buffer)

	# @PERFORMANCE
	# Essa parte poderia ser feita juntamente com a parte de cima, dispensando a necessidade de iterar pelos dados novamente
	
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

def translate_sequences(str):
	fstr = ""
	cor = ""
	corsequence = None
	sequence = False

	for c in str:
		if c == "{":
			sequence = True
		elif c == "}":
			sequence = False

			corsequence = cor.split(".")
			erro = False
			for i in range(len(corsequence)):
				if corsequence[i] in ANSI_CODES.keys():
					corsequence[i] = ANSI_CODES[corsequence[i]]
				else:
					erro = True
			
			if not erro:
				fstr = fstr + ANSI_ESCAPE.format(";".join(corsequence))
			else:
				fstr = fstr + "{" + cor + "}"

			cor = ""
		else:
			if sequence:
				cor = cor + c
			else:
				fstr = fstr + c

	return fstr
	