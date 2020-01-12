# Navi
A experimental bot written using discord.py library for learning purposes

## Porquê?

A Navi é um bot experimental escrito utilizando a biblioteca discord.py por razões de aprendizado, mais específicamente para experimentar com o asyncio e também conseguir construir e replicar algumas funcionalidades que já vi serem implementadas, nesse momento já está utilizável com até uma CLI e tudo mais funcionando (sempre quis fazer algo semelhante), porém nada foi testado rigorosamente até este ponto e portanto não deve ser levado em conta sua estabilidade.

## Requerimentos

* Python >= 3.7
* discord.py
* aiohttp
* databases[mysql]

## Como configurar?

A configuração do bot pode ser encontrada no arquivo de exemplo `config.json` presente na raiz do repositório, nele você encontrará um arquivo já configurado com alguns valores, os campos para se prestar atenção são os listados a seguir:

```json
{
    "global": {
		"bot_token": "DISCORD_BOT_TOKEN",
		"bot_prefix": ";;",
		"bot_playing": ["testing!", "with fire!", "eating donuts!", "typing ;;"],
		"bot_playing_delay": 120,
		"bot_modules": [
			"modules.core", 
		],
		"log_path": ""
	}
}
```

A maioria dos campos são auto-explicativos, com excessão do `bot_playing_delay`, que controla o delay entre a mudança automática de cada item da lista de atividade de jogos do bot, juntamente com `bot_modules`, que controla quais modulos serão carregados em sua inicialização.

## Criando o primeiro comando

Por razões de organização, é recomendado construir um conjunto de comandos sobre uma espécie de modulo, todos os modulos são preferêncialmente guardados em `modules/` como um modulo nativo do python. Segue abaixo um modulo de exemplo contendo o comando `helloworld`:

```py
# modules/elloworld.py
import navibot

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
		"bot_modules": [
			"modules.core", 
			"modules.helloworld"
		],
		"log_path": ""
	}
}
```

### TODO

- [x] Verificar BUGs com o comando reload (recarregamento de modulos no Python é algo extremamente complexo e difícil de fazer, pode ser que nunca será arrumado ou será retirado por completo)
- [x] Preferências e variáveis definidas em um contexto diferente para cada Guild, integrado à um banco de dados local.
- [x] Verificar como implementar a verificação de permissão de execução dos comandos, quais usuários tem permissão.
- [x] Modulo de gerênciamento de progressão dos usuários, EXP/PONTOS/PERFIL.
- [ ] Escrever a função NaviBot.feedback() novamente, possibilitando formas mais cosistentes de passar informações.
- [ ] ? Implementar uma espécie de loja de recompensas para poder gastar os créditos recebidos, achar uma forma justa de dar créditos.
- [ ] ? Mostrar mais informações no perfil do membro, como recompensas obtidas, etc...
- [ ] Modulo de integração com a API Danbooru/Safebooru.
- [ ] Integração com a API AniList (possibilidade de integrar várias ideias; buscar personagens ou animes; perfil com top animes/personagens do usuário através do bot).
- [ ] Criação de um script launcher (capaz de atualizar o bot, alterar configurações, gerênciar o banco de dados relacionado e inclusive adicionar novos modulos de um repositório github).
- [ ] Desacoplar a CLI do núcleo do bot presente em navibot.NaviBot, tornar algo totalmente separado que não necessite de uma modificação na classe principal, pode ser necessário uma total reescrita do navilog.LogManager.
