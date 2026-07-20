# Sports Calendar Hub

Calendário esportivo automatizado com Python, feeds ICS, GitHub Actions e sincronização controlada com um calendário Google dedicado.

O projeto normaliza eventos esportivos públicos em JSON, aplica um escopo versionado, consolida duplicatas e publica um calendário geral e feeds temáticos no padrão iCalendar.

## Estado dos dados

Os eventos de produção vêm de uma **exportação sanitizada** da aba `Eventos` da planilha privada “Controle de Eventos Esportivos”. A planilha não é publicada: um Apps Script independente entrega somente o contrato público mínimo, protegido por token.

Os oito eventos fictícios da versão inicial foram removidos de `data/events.json` e permanecem apenas em `tests/fixtures/events_demo.json` para testes.

## Arquitetura

1. `data/scope_rules.json` contém aliases, equipes, competições, fases, exclusões e prioridades.
2. `src/scope_rules.py` carrega essas regras e decide escopo, equipe, competição, grupo e prioridade.
3. `apps-script-gateway/` contém o código-fonte auditável do gateway separado “Sports Calendar Hub Gateway”.
4. `src/importers/apps_script_json.py` valida schema, contagem e hash da exportação antes de gravar `data/events.json`.
5. `src/calendar_payload.py` preserva UID e `SEQUENCE` e cria o payload sem participantes, conferências ou IDs brutos.
6. `src/remote_sync.py` executa exportação, escopo, deduplicação, feeds, validação, varredura de privacidade, dry-run e UPSERT.
7. O gateway usa a API avançada Calendar v3 para atualizar somente o calendário `Eventos esportivos`.
8. `SportsEvent`, normalização, deduplicação e regras de escopo mantêm a camada pública determinística.
9. `ics_generator.py` e `validate_ics.py` produzem e reabrem os feeds em UTF-8/CRLF.
10. GitHub Actions executa testes, sincronização protegida e publicação pelo GitHub Pages.

## Estrutura principal

```text
.
├── .github/workflows/
├── apps-script-gateway/
├── data/
│   ├── events.json
│   ├── scope_rules.json
│   └── sources.json
├── docs/
│   ├── escopo-mestre.md
│   ├── index.html
│   └── *.ics
├── reports/
│   ├── import-summary.json
│   └── import-summary.md
├── src/
│   ├── importers/google_sheet_csv.py
│   ├── importers/apps_script_json.py
│   ├── calendar_payload.py
│   ├── calendar_push.py
│   ├── privacy_scan.py
│   ├── remote_sync.py
│   ├── scope_rules.py
│   └── ...
└── tests/
    └── fixtures/events_demo.json
```

## Escopo mestre

O documento completo está em [`docs/escopo-mestre.md`](docs/escopo-mestre.md). Os pontos principais são:

- fuso de saída `America/Sao_Paulo`;
- horizonte de referência de 12 meses;
- um evento em `all.ics` e em exatamente um grupo;
- transmissão específica do evento, sem inferir emissora por direitos gerais;
- somente dados esportivos públicos;
- prioridade do clube ou seleção sobre a competição.

### São Paulo FC

Categorias incluídas:

- profissional masculino;
- profissional feminino;
- masculino sub-20;
- masculino sub-17.

Categorias excluídas:

- feminino sub-20;
- feminino sub-17;
- feminino sub-16;
- feminino sub-15;
- qualquer outra equipe feminina de base.

O São Paulo feminino profissional continua no escopo. A exclusão de base feminina é aplicada na importação, na validação e na geração.

### Clubes regionais

O grupo `clubes-regionais`, esperado como verde pelo assinante, inclui as equipes masculinas profissionais:

- Ferroviária-SP;
- Portuguesa-SP;
- Juventus-SP;
- Botafogo-SP;
- Comercial-SP;
- Matonense;
- São Carlos-SP;
- Grêmio Sãocarlense.

Aliases de Botafogo-SP e Comercial-SP são resolvidos de forma exata para não confundir clubes homônimos de outros estados.

### Copinha

A Copa São Paulo de Futebol Júnior é acompanhada pela regra geral a partir das oitavas de final: oitavas, quartas, semifinais e final.

Uma prioridade de clube pode preservar um jogo anterior, como o São Paulo masculino sub-20. Nos jogos permitidos sem clube prioritário, o grupo é `outros-esportes`.

## Grupos e prioridade

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

## Importação sanitizada

O caminho automatizado recebe JSON do gateway e valida o hash antes de aceitar qualquer evento:

```bash
python -m src.importers.apps_script_json tests/fixtures/apps_script_export.json
```

O CSV permanece apenas como ferramenta de migração local e compatibilidade.

Exporte temporariamente somente a aba `Eventos` para CSV e execute:

```bash
python -m src.importers.google_sheet_csv /caminho/temporario/eventos.csv
```

O importador:

- encontra colunas pelo cabeçalho, não pela posição;
- interpreta datas, horários, eventos de dia inteiro e fusos;
- sanitiza HTML, URLs e textos;
- converte status confirmados, provisórios, adiados e cancelados;
- aplica o escopo e a prioridade de grupos;
- consolida duplicatas;
- grava `data/events.json`;
- gera `reports/import-summary.json` e `.md`.

O CSV bruto é temporário e está bloqueado no Git por `data/import/*.csv`. O snapshot não representa sincronização automática: uma nova exportação e importação são necessárias para incorporar alterações da planilha.

## UID permanente e privacidade

O ID original do Google Calendar nunca é publicado. Quando disponível, o gateway calcula:

```text
SHA-256("google-calendar:" + id_original)
```

Somente o hash entra em `external_id_hash` e serve de base estável para o UID. Data, horário, local, transmissão e status podem mudar sem alterar a identidade do evento.

No calendário de destino, a identidade fica em propriedades estendidas privadas: `sports_calendar_uid`, `sports_calendar_managed` e `sports_calendar_scope_version`. O `eventId` selecionado é preservado em atualizações. `SEQUENCE` aumenta somente quando um campo esportivo relevante muda; `last_verified` isolado não altera a sequência.

Não são armazenados:

- e-mail ou ID privado de agenda;
- organizador, convidados ou `attendees`;
- Google Meet, links privados de Zoom ou dados de conferência;
- links de edição ou resposta;
- tokens, OAuth, secrets ou chaves privadas;
- chave de sincronização e ID originais.

## Deduplicação

A comparação ocorre nesta ordem:

1. `external_id` sanitizado e fonte;
2. UID permanente;
3. chave canônica de modalidade, categoria, competição, fase e participantes;
4. proximidade de horário apenas como auxílio.

A ordem dos participantes é irrelevante somente para comparação. O registro mais completo preserva transmissão, local, fonte, maior `sequence` e maior prioridade.

## Executar localmente

Requer Python 3.12 ou compatível:

```bash
python -m pip install -r requirements.txt
pytest
python -m src.main
python -m src.validate_ics
python -m src.privacy_scan
```

A segunda importação do mesmo CSV deve produzir o mesmo `events.json`. A segunda geração deve informar `changed_files: 0`.

## GitHub Actions

O workflow **Tests** roda em `push`, `pull_request` e manualmente. Ele instala dependências, executa todos os testes, gera os feeds e valida os ICS.

O workflow **Update calendars** pode ser iniciado em **Actions → Update calendars → Run workflow** e também executa aproximadamente às **05h30, 11h30 e 17h30**, com `timezone: America/Sao_Paulo`. A antecipação deixa margem para o processamento e a publicação estarem disponíveis perto das 06h, 12h e 18h.

Ele usa o `GITHUB_TOKEN` efêmero com `contents: write` e três repository secrets: `SPORTS_GATEWAY_URL`, `SPORTS_EXPORT_TOKEN` e `SPORTS_SYNC_TOKEN`. Os valores não ficam no código, nos logs, nos relatórios ou nos artefatos públicos. A execução sempre faz dry-run antes do apply, rejeita exclusões em massa e não cria commit vazio.

## Proteções da escrita no Google Calendar

- destino único: calendário `Eventos esportivos`;
- calendário principal somente leitura para auditoria de duplicatas;
- `sendUpdates: none`, sem convidados, RSVP, Meet, Zoom ou conferência;
- todos os eventos são `transparent` e usam a prioridade fixa de cores;
- UPSERT por UID, hash do ID externo e chave canônica;
- cancelamentos e adiamentos preservam UID e evento selecionado;
- nenhum evento fora de escopo é criado;
- duplicatas não seguras no calendário principal viram `REVISÃO_MANUAL`;
- snapshot privado de rollback antes de cada aplicação;
- segunda execução deve resultar em zero criações, atualizações e exclusões.

## Publicação

- Página: https://andertrunks.github.io/sports-calendar-hub/
- Geral: https://andertrunks.github.io/sports-calendar-hub/all.ics
- São Paulo: https://andertrunks.github.io/sports-calendar-hub/sao-paulo.ics
- Seleção Brasileira: https://andertrunks.github.io/sports-calendar-hub/selecao-brasileira.ics
- Clubes regionais: https://andertrunks.github.io/sports-calendar-hub/clubes-regionais.ics
- Red Bull: https://andertrunks.github.io/sports-calendar-hub/red-bull.ics
- Premier League: https://andertrunks.github.io/sports-calendar-hub/premier-league.ics
- Continentais: https://andertrunks.github.io/sports-calendar-hub/continentais.ics
- Automobilismo: https://andertrunks.github.io/sports-calendar-hub/automobilismo.ics
- Brasileirão: https://andertrunks.github.io/sports-calendar-hub/brasileirao.ics
- Olimpíadas e Pan: https://andertrunks.github.io/sports-calendar-hub/olimpiadas-pan.ics
- Copas do Mundo: https://andertrunks.github.io/sports-calendar-hub/copas-do-mundo.ics
- Outros esportes: https://andertrunks.github.io/sports-calendar-hub/outros-esportes.ics

## Assinar versus escrever em uma agenda

Um feed ICS assinado é consultado periodicamente pelo Google Calendar, Outlook ou Apple Calendar. A automação também mantém eventos no calendário Google dedicado `Eventos esportivos`; ela não escreve no calendário principal e não acessa o Outlook.

Clientes assinantes mantêm cache próprio; alterações publicadas podem levar horas para aparecer. Importar um `.ics` cria normalmente uma cópia estática, enquanto assinar mantém uma URL que será consultada novamente.

## Configuração do gateway

Crie um projeto Apps Script independente, copie os arquivos de `apps-script-gateway/`, habilite os serviços avançados Calendar v3 e Sheets v4 e mantenha para a planilha apenas o escopo OAuth `spreadsheets.readonly`. Configure as propriedades `SPREADSHEET_ID`, `SHEET_NAME`, `SPORTS_CALENDAR_ID`, `TIMEZONE`, `EXPORT_TOKEN`, `SYNC_TOKEN`, `SCHEMA_VERSION`, `ALLOW_PRIMARY_DUPLICATE_CLEANUP` e `DRY_RUN_DEFAULT`. O Web App executa como o proprietário e é protegido por tokens diferentes com no mínimo 48 caracteres.

## Próximos passos

- revisar sazonalmente os clubes da Série A e Premier League;
- incorporar novas fontes oficiais com rastreabilidade;
- atualizar rankings ATP e WTA para brasileiros prioritários;
- ampliar a auditoria de destaques excepcionais com justificativa;
- manter qualquer integração com Outlook separada e sem compartilhar credenciais.

## Licença

Distribuído sob a licença MIT. Consulte `LICENSE`.
