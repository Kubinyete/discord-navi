# Navi
A experimental bot written using discord.py library for learning purposes

## Porquê?

A Navi é um bot experimental escrito utilizando a biblioteca discord.py por razões de aprendizado, mais específicamente para experimentar com o asyncio e também conseguir construir e replicar algumas funcionalidades que já vi serem implementadas, nesse momento já está utilizável com até uma CLI e tudo mais funcionando (sempre quis fazer algo semelhante), porém nada foi testado rigorosamente até este ponto e portanto não deve ser levado em conta sua estabilidade.

## Requerimentos

* Python >= 3.7
* discord.py
* aiohttp

## Como configurar?

A configuração do bot pode ser encontrada no arquivo de exemplo `config.json` presente na raiz do repositório, nele você encontrará um arquivo já configurado com alguns valores, os campos para se prestar atenção são os listados a seguir:

```json
{
    "global": {
		"bot_token": "DISCORD_BOT_TOKEN",
		"bot_prefix": ";;",
		"bot_playing": ["testing!", "with fire!", "eating donuts!", "typing ;;"],
		"bot_playing_delay": 120,
		"bot_modules": ["modules.commands", "modules.commands_cli", "modules.commands_yandere"],
		"log_path": ""
	}
}
```

A maioria dos campos são auto-explicativos, com excessão do `bot_playing_delay`, que controla o delay entre a mudança automática de cada item da lista de atividade de jogos do bot, juntamente com `bot_modules`, que controla quais modulos serão carregados em sua inicialização.

## Criando o primeiro comando

Por razões de organização, é recomendado construir um conjunto de comandos sobre uma espécie de modulo, todos os modulos são preferêncialmente guardados em `modules/` como um modulo nativo do python. Segue abaixo um modulo de exemplo contendo o comando `helloworld`:

```py
# modules/commands_helloworld.py
import navibot

# bot: navibot.NaviBot
# message: discord.Message
# args: list
# flags: dict
# handler: naviclient.NaviCommand
async def command_helloworld(bot, message, args, flags, handler):
    await bot.feedback(message, navibot.SUCCESS, text=f"Olá mundo {message.author.name}!")

```

Ao término do modulo, será necessário atualizar a lista de modulos a serem carregados:

```json
{
    "global": {
		"bot_token": "DISCORD_BOT_TOKEN",
		"bot_prefix": ";;",
		"bot_playing": ["testing!", "with fire!", "eating donuts!", "typing ;;"],
		"bot_playing_delay": 120,
		"bot_modules": ["modules.commands", "modules.commands_cli", "modules.commands_yandere", "modules.commands_helloworld"],
		"log_path": ""
	}
}
```

## Problemas/Correções/Notas

###### Command Line Interface

Atualmente a CLI está rodando na mesma thread que o resto do bot, ou seja, está sendo implementada como uma rotina cujo objetivo é obter a entrada de dados da STDIN e interpretá-la, ao mesmo tempo que preserva a formatação do input gráficamente, isso acaba indiretamente impactando a performance do bot. Possíveis soluções para o mesmo seria a possibilidade de desativá-la e implementar uma melhor forma de rodar o bot em produção (sem cli, performance máxima) ou rodá-la opcionalmente em uma thread separada.

###### Logs

Todas as mensagens são guardadas, dependendo do seu nível, em um arquivo de log pré-determinado pelo arquivo de configurações, isso causa um gargalo em produção devido a necessidade de pausar para escrever em disco. Possíveis soluções para o mesmo seria a implementação opcional da funcionalidade, implementação assíncrona de I/O utilizando o asyncio ou biblioteca ou até mesmo jogá-la para outra thread.

###### Componentes/Integração/Aproveitamento

Será necessário abstrair ao máximo os componentes do bot, permitindo uma maior flexibilidade e aproveitamento de código, ou seja, precisamos implementar componentes que podem ser quebrados em pequenas partes. O maior exemplo da quebra deste princípio atualmente é a integração da própria CLI como se fosse uma rotina do bot, ou seja, estamos integrando forçadamente duas coisas que não precisam se misturar.