import navilog

# @SECTION
# Esse modulo fica responsável por servir de container para um set de comandos no qual a classe principal NaviBot irá examinar e referenciar as funções que estão aqui

async def callbackLog(bot, message=None):
	if not message:
		bot.log.write("O bot foi iniciado com sucesso")
	else:
		bot.log.write(message, logtype=navilog.MESSAGE)