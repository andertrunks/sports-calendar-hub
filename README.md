# Sports Calendar Hub

Calendário esportivo automatizado com Python, feeds ICS, GitHub Actions e integração futura com Google Calendar e Outlook.

> **Aviso:** a versão `0.1.0` contém somente dados fictícios, identificados como **DADOS DE DEMONSTRAÇÃO — NÃO É CALENDÁRIO OFICIAL**. Eles existem para testar a infraestrutura e serão substituídos em uma etapa futura.

## Objetivo

O projeto mantém eventos esportivos normalizados em JSON, consolida duplicatas e gera feeds públicos no padrão iCalendar. Um evento entra no calendário geral e em exatamente um grupo temático, o de maior prioridade aplicável.

Nesta etapa não há OAuth, coleta extensiva de sites, escrita em calendários pessoais, banco de dados externo nem armazenamento de tokens.

## Arquitetura

O fluxo é deliberadamente pequeno e auditável:

1. `data/events.json` armazena os eventos de origem.
2. `SportsEvent` valida campos, datas, fusos, status e grupo.
3. `normalize.py` limpa texto, cria chaves canônicas, define o grupo e calcula o UID permanente.
4. `deduplicate.py` consolida registros equivalentes sem usar horário como identidade única.
5. `ics_generator.py` produz os feeds em UTF-8, com CRLF e linhas dobradas.
6. `validate_ics.py` reabre e inspeciona todos os arquivos gerados.
7. GitHub Actions executa testes, atualiza `docs/` e publica a pasta pelo GitHub Pages.

## Estrutura

```text
.
├── .github/workflows/
│   ├── tests.yml
│   └── update-calendars.yml
├── data/
│   ├── events.json
│   └── sources.json
├── docs/
│   ├── index.html
│   └── *.ics
├── src/
│   ├── config.py
│   ├── deduplicate.py
│   ├── ics_generator.py
│   ├── main.py
│   ├── models.py
│   ├── normalize.py
│   └── validate_ics.py
├── tests/
├── requirements.txt
└── pyproject.toml
```

## UID permanente

Quando uma fonte fornece `external_id`, o UID usa principalmente a identidade da fonte e esse identificador. Sem `external_id`, o sistema calcula SHA-256 sobre modalidade, competição, categoria, participantes normalizados e fase/rodada, além da fonte. O horário, a data, o local, a transmissão e o status não fazem parte da identidade.

O formato final é:

```text
<sha-256>@sports-calendar-hub
```

Assim, uma mudança normal de horário mantém o mesmo UID e pode ser interpretada por clientes de calendário como atualização do evento existente.

## Deduplicação

A comparação ocorre nesta ordem:

1. `external_id` + fonte;
2. UID permanente;
3. chave canônica de modalidade, categoria, competição, fase e participantes;
4. horário próximo apenas como sinal auxiliar, sempre combinado com participantes, modalidade e competição.

Os participantes são ordenados somente na chave de comparação. A ordem original permanece na exibição. Ao consolidar, o registro mais completo é preferido e campos úteis da outra fonte — transmissão, local e `external_id` — são preservados. Também ficam o maior `sequence`, a maior prioridade de fonte e a verificação mais recente.

## Grupos e prioridade

Cada evento aparece em `all.ics` e em exatamente um dos grupos abaixo. A primeira regra compatível vence:

1. `sao-paulo`
2. `selecao-brasileira`
3. `clubes-regionais`
4. `red-bull`
5. `premier-league`
6. `continentais`
7. `automobilismo`
8. `brasileirao`
9. `olimpiadas-pan`
10. `copas-do-mundo`
11. `outros-esportes`

## Executar localmente

Requer Python 3.12 ou compatível:

```bash
python -m pip install -r requirements.txt
pytest
python -m src.main
python -m src.validate_ics
```

O gerador reescreve arquivos somente quando o conteúdo mudou. A data de geração deriva da verificação mais recente dos dados, evitando alterações artificiais em cada execução.

## GitHub Actions

O workflow **Tests** roda em `push`, `pull_request` e manualmente. Ele instala as dependências, executa o `pytest`, gera os calendários e valida todos os ICS.

O workflow **Update calendars** pode ser iniciado em **Actions → Update calendars → Run workflow**. Também executa diariamente às **06h00, 12h00 e 18h00** com `timezone: America/Sao_Paulo`, recurso atualmente aceito pela sintaxe oficial do GitHub Actions. Ele usa somente o `GITHUB_TOKEN` padrão, com permissão mínima `contents: write`, e cria commit apenas se `docs/` mudou.

O workflow de atualização não reage a `push`; portanto, o commit automático não dispara outra atualização e não forma loop.

## Publicação no GitHub Pages

Em **Settings → Pages**, selecione **Deploy from a branch**, branch `main` e pasta `/docs`. A página lista todos os feeds, suas finalidades, quantidades e ações para abrir ou copiar o link.

Publicação confirmada em: https://andertrunks.github.io/sports-calendar-hub/

### Feeds públicos

- Geral: https://andertrunks.github.io/sports-calendar-hub/all.ics
- São Paulo: https://andertrunks.github.io/sports-calendar-hub/sao-paulo.ics
- Seleção Brasileira: https://andertrunks.github.io/sports-calendar-hub/selecao-brasileira.ics
- Clubes regionais: https://andertrunks.github.io/sports-calendar-hub/clubes-regionais.ics
- Red Bull: https://andertrunks.github.io/sports-calendar-hub/red-bull.ics
- Premier League: https://andertrunks.github.io/sports-calendar-hub/premier-league.ics
- Competições continentais: https://andertrunks.github.io/sports-calendar-hub/continentais.ics
- Automobilismo: https://andertrunks.github.io/sports-calendar-hub/automobilismo.ics
- Brasileirão: https://andertrunks.github.io/sports-calendar-hub/brasileirao.ics
- Olimpíadas e Pan: https://andertrunks.github.io/sports-calendar-hub/olimpiadas-pan.ics
- Copas do Mundo: https://andertrunks.github.io/sports-calendar-hub/copas-do-mundo.ics
- Outros esportes: https://andertrunks.github.io/sports-calendar-hub/outros-esportes.ics

## Assinar um feed

Use a URL pública do arquivo `.ics` desejado, obtida na página do projeto.

### Outlook

No Outlook na web, abra **Calendário → Adicionar calendário → Assinar pela Web**, cole a URL e confirme. Em versões de desktop, a opção pode aparecer como **Adicionar calendário → Da Internet**.

### Google Calendar

Na versão web, ao lado de **Outros calendários**, clique em **+ → Do URL**, cole a URL e adicione. O Google controla a frequência de atualização e não oferece sincronização instantânea garantida.

### Apple Calendar

No macOS, use **Arquivo → Nova Assinatura de Calendário**, cole a URL e escolha a frequência de atualização. No iPhone ou iPad, use **Ajustes → Apps → Calendário → Contas de Calendário → Adicionar Conta → Outra → Adicionar Calendário Assinado**.

## Limitações de calendários assinados

Clientes como Google Calendar, Outlook e Apple Calendar mantêm cache próprio. Uma mudança publicada no feed pode levar horas para aparecer, e o projeto não controla esse intervalo. Assinatura é diferente de importar um `.ics`: a importação costuma ser uma cópia estática; a assinatura consulta o feed periodicamente.

Eventos adiados usam `STATUS:TENTATIVE` no ICS, pois `POSTPONED` não é um valor previsto pelo padrão iCalendar; a descrição preserva o status original `POSTPONED`.

## Próximos passos

- substituir os oito eventos fictícios por fontes públicas verificadas;
- criar adaptadores de coleta com limites e rastreabilidade;
- adicionar histórico de alterações e observabilidade;
- planejar integrações OAuth separadas para Google Calendar e Microsoft Outlook;
- ampliar regras de entidades e competições sem quebrar UIDs existentes.

## Segurança

- Nenhuma senha, chave, token, credencial ou dado pessoal é necessário.
- Os workflows usam apenas o `GITHUB_TOKEN` efêmero fornecido pelo GitHub.
- Os arquivos publicados contêm somente dados esportivos públicos ou fictícios.
- Google Calendar e Outlook não são acessados nem alterados por esta versão.
- Não há serviço pago, domínio personalizado, banco externo ou segredo configurado.

## Licença

Distribuído sob a licença MIT. Consulte `LICENSE`.
