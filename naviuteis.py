import math

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
	"""Devolve dois objetos de argumentos e flags baseado na string passada por parâmetro.
	
	Args:
	    string (str): Cadeia de caracteres a ser processada.
	
	Returns:
	    tuple(list(str), dict): Retorna uma tuple com dois valores, sendo eles uma list de argumentos e um dict de flags.
	"""

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
	"""Traduz todas as ocorrências de sequências de formatação no estilo {atributo1.atributo2} na cadeia de caracteres passada. 
	
	Args:
	    str (str): A cadeia de caracteres a ser processada.
	
	Returns:
	    str: A cadeia de caracteres após a inserção das sequências ANSI.
	"""

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
	
def bytes_string(bytes):
	"""Devolve uma string de representação de acordo com a quantidade em bytes passada.
	
	Args:
	    bytes (int): Número de bytes.
	
	Returns:
	    str: A string de representação.
	"""
	sizes = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")

	i = 0
	while (bytes / 1024.0 >= 1):
		bytes = math.floor(bytes / 1024.0)
		i += 1

	return f"{bytes:.0f} {sizes[i]}"
	
def seconds_string(seconds):
	"""Devolve uma string de representação de acordo com a quantidade em segundos passado.
	
	Args:
	    seconds (int): Segundos.
	
	Returns:
	    str: A string de representação.
	"""

	d = math.floor(seconds / 86400)
	seconds -= d * 86400

	h = math.floor(seconds / 3600)
	seconds -= h * 3600
	
	m = math.floor(seconds / 60)
	seconds -= m * 60

	output = []

	if d >= 1:
		output.append(f"{d} dia(s)")
	if h >= 1:
		output.append(f"{h} hora(s)")
	if m >= 1:
		output.append(f"{h} minuto(s)")
		
	output.append(f"{seconds} segundo(s)")
	
	return ", ".join(output)
	