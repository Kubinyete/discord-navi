# NaviBot [discord-navi]
"A experimental bot written using discord.py library for learning purposes"

Um bot experimental escrito utilizando a biblioteca discord.py por razões de aprendizagem, nesse momento já está utilizável com até uma CLI e tudo mais funcionando, porém nada foi testado rigorosamente até este ponto.

### Inicialização

```py
from navibot import NaviBot

bot = NaviBot("release/config.json")
bot.rodar()
```

### Configurações

A configuração geral do bot pode ser localizada em `config.json`, porém é aconselhável copiar esse arquivo de configuração genérico para uma pasta `release/config.json` para que o exemplo seja preservado.

O arquivo de configuração é basicamente estruturado da seguinte forma:

```json
{
	"global": {
		// Token necessária
		"bot_token": "DISCORD_BOT_TOKEN",
		// Prefixo de ativação dos comandos
		"bot_prefix": ";;",
		// Lista de status que podem ser alterados dinâmicamente a cada X segundos
		"bot_playing": ["Status 1", "Status 2"],
		// Especifica o quanto tempo um status permanece até ser alterado para o próximo
		"bot_playing_delay": 60,
		// Caminho padrão para salvar os logs
		"log_path": "messages.log"
	},
	"commands": {
		// Configura quais são os IDs que podem executar comandos restritos
		"owners": []
	},
	"external": {
		// Configurações de APIs externas, podem pedir chaves de autenticação ou outros parâmetros
		"osu": {
			"api_key": "OSU_API_KEY",
			"api_domain": "osu.ppy.sh",
			"api_assets": "a.ppy.sh",
			"api_getuser": "/api/get_user"
		}
	}
}
```

Outras chaves de configurações existem porém são atualmente utilizadas para DEBUG ou implementação de comandos.

### Requerimentos

Testado até o momento somente com **Python >= 3.7**, provavelmente não terá compatibilidade com versões anteriores devido as alterações presentes no asyncio.

Atualmente o bot requer que as bibliotecas:

* discord.py
* aiohttp

### Command Line Interface

O bot te, implantado atualmente somente no Linux (requer o modulo `select`, por isso a restrição de plataforma) uma CLI em tempo real, podemos interagir com o bot enquanto o mesmo está em execução. É utilizado mais para razões de DEBUG ou apenas por diversão, mais comandos serão adicionados eventualmente.

```
[22/08/2019 10:52:28] Informação O bot foi iniciado com sucesso
-> help
[22/08/2019 10:52:55] Debug help
[22/08/2019 10:52:55] Debug echo texto
[22/08/2019 10:52:55] Debug select channelid [--user] [--show]
[22/08/2019 10:52:55] Debug say texto
[22/08/2019 10:52:55] Debug task nomeTarefa [--enable] [--disable] [--show]
[22/08/2019 10:52:55] Debug quit
-> |
```

### Adicionando comandos

Os comandos podem ser encontrados em `navicommands.py`, cada comando é na verdade uma coroutine definida e nomeada com um prefixo de acordo com sua característica.

* `command_`, define um comando normal.
* `comamnd_owner_`, define um comando cujo apenas os "owners" definidos em `commands.owners` (presente no `config.json`) podem utilizar.
* `cli_`, define um comando na CLI.

Exemplo helloworld:

```py
import navibot

async def command_helloworld(bot, handler, client, message, args, flags):
	await bot.sendFeedback(message, navibot.NaviFeedback.SUCCESS, text="Olá mundo!")
```

Cada comando presente em `navicommands.py` já será reconhecido automaticamente pelo bot, através de seu método de inicialização, portanto, você só precisará prestar atenção nas mensagens de descrição e uso presentes no `config.json`, exemplo:

```json
{
	"commands": {
		"owners": [],
		"descriptions": {
			"helloworld": {
				"text": "Envia uma mensagem: Olá mundo!",
				"usage": "helloworld"
			}
		}
	}
}
``` 

Já para manipulação dos comandos, os parâmetros `args` e `flags` são extremamente importantes, o bot já fará o processamento na mensagem do usuário e trará os argumentos separados na lista, exemplo:

O comando:

`;;argtester ola mundo`

Resultará em:

```py
args = ["argtester", "ola", "mundo"]
```

Já às flags, são parâmetros cujo iniciam com - (representam uma sinal ligado) ou -- (representam uma chave=valor), exemplo:

O comando:

`;;argtester ola mundo -myflag --myflag2 --mykey=myvalue`

Resultará em:

```py
flags = {
	"myflag": True,
	"myflag2": True,
	"mykey": "myvalue"
}
```

### Problemas conhecidos

1. Entrada/Saida: Não temos uma forma de interagir com arquivos de uma forma assíncrona nativamente, portanto toda chamada para o `LogManager.write()` cujo não seja uma mensagem de `LogType.DEBUG` fará com que a rotina congele até que a operação conclua, pode resultar em uma perda de performance dependendo da carga de eventos.

2. CLI: Não parece ser a melhor forma de ler a stream de entrada (se eu não estiver enganado), estamos utilizando um callback efetuado a cada intervalo de tempo e lendo o que está presente na entrada até `select.select()` retornar a ausência de dados.
