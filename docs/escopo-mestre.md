# Escopo mestre — Sports Calendar Hub

Última atualização: **20/07/2026**  
Fuso de publicação: **America/Sao_Paulo**  
Horizonte de referência: **12 meses**

## Origem e finalidade

Este documento converte o arquivo de escopo esportivo original, anteriormente orientado à operação de uma agenda, em regras funcionais para normalização, filtragem, deduplicação e publicação de feeds ICS. As alterações definitivas desta etapa prevalecem sobre o texto de origem.

O projeto publica somente dados esportivos públicos. Instruções operacionais como criar reuniões, adicionar convidados ou escrever diretamente em agendas foram convertidas em regras de privacidade: não armazenar e-mails, `attendees`, organizadores, dados de conferência, links privados ou identificadores originais do Google Calendar.

## Regras gerais de data e horário

- Todos os horários são convertidos para `America/Sao_Paulo`.
- Um evento com data e horário confirmados é publicado com início e término normais.
- Quando somente a data estiver confirmada, o evento pode ser publicado como dia inteiro e deve indicar que o horário ainda não está confirmado.
- Não são inventados datas, horários, adversários, fases, locais ou transmissões.
- Eventos eliminatórios sem confronto definido aguardam confirmação.
- Eventos passados não fazem parte de futuras coletas.
- O atributo ICS `TRANSP` é sempre `TRANSPARENT`, para não bloquear disponibilidade.

## Fontes e confiabilidade

A ordem de preferência é:

1. sites oficiais das competições;
2. federações e confederações;
3. ligas oficiais;
4. clubes, equipes e atletas;
5. tabelas e comunicados oficiais;
6. veículos esportivos reconhecidos;
7. plataformas especializadas confiáveis.

Uma fonte não oficial não deve contrariar uma fonte oficial mais recente. Divergências devem ser registradas sem inventar uma conclusão.

## Grupos, cores e prioridade

Cada evento aparece uma vez em `all.ics` e em exatamente um grupo. A primeira regra compatível vence:

1. `sao-paulo` — vermelho, `color_id 11`;
2. `selecao-brasileira` — amarelo, `color_id 5`;
3. `clubes-regionais` — verde, `color_id 10`;
4. `red-bull` — laranja, `color_id 6`;
5. `premier-league` — azul-claro, `color_id 1`;
6. `continentais` — azul forte, `color_id 9`;
7. `automobilismo` — roxo, `color_id 3`;
8. `brasileirao` — ciano, `color_id 7`;
9. `olimpiadas-pan` — coral, `color_id 4`;
10. `copas-do-mundo` — verde-água, `color_id 2`;
11. `outros-esportes` — cinza, `color_id 8`.

A prioridade do clube ou seleção prevalece sobre a competição. Por exemplo, São Paulo x Comercial-SP pertence a `sao-paulo`; Botafogo-SP x Palmeiras pertence a `clubes-regionais`; RB Bragantino x Palmeiras pertence a `red-bull`.

## São Paulo FC

Categorias incluídas em todas as competições:

- profissional masculino;
- profissional feminino;
- masculino sub-20;
- masculino sub-17.

Categorias excluídas:

- feminino sub-20;
- feminino sub-17;
- feminino sub-16;
- feminino sub-15;
- qualquer outra equipe feminina de base;
- eventos identificados apenas como feminino de base.

O São Paulo feminino profissional permanece no escopo. A exclusão das equipes femininas de base ocorre na importação, na validação de escopo e antes da geração dos feeds.

## Clubes regionais

São acompanhados os jogos oficiais das equipes masculinas profissionais de:

- Ferroviária-SP;
- Portuguesa-SP;
- Juventus-SP;
- Botafogo-SP;
- Comercial-SP;
- Matonense;
- São Carlos-SP;
- Grêmio Sãocarlense.

Aliases como Botafogo Futebol Clube de Ribeirão Preto e Botafogo de Ribeirão Preto representam Botafogo-SP. Eles nunca são confundidos com Botafogo de Futebol e Regatas, Botafogo-PB ou outros homônimos.

Comercial Futebol Clube e Comercial de Ribeirão Preto representam Comercial-SP. Outros clubes chamados Comercial não são incluídos por esse alias.

## Equipes Red Bull

São acompanhadas as equipes masculinas profissionais:

- Red Bull Bragantino;
- RB Leipzig;
- Red Bull Salzburg;
- New York Red Bulls;
- RB Omiya Ardija.

## Série A e Premier League

- Os clubes da Série A da temporada vigente são acompanhados em todas as competições oficiais. Eventos sem prioridade superior usam `brasileirao`.
- Os clubes da Premier League da temporada vigente são acompanhados em Premier League, copas domésticas e competições internacionais. Eventos sem prioridade superior usam `premier-league`.
- A composição das ligas deve ser revisada a cada temporada por futuros coletores.

## Copa São Paulo de Futebol Júnior

Aliases reconhecidos incluem Copinha, Copa São Paulo, Copa SP de Futebol Júnior, Copa São Paulo Júnior, Copa São Paulo de Juniores e formas equivalentes sem acento.

Pela regra geral, são incluídas somente:

- oitavas de final;
- quartas de final;
- semifinais;
- final.

Primeira fase, fase de grupos, segunda fase, terceira fase e mata-matas anteriores às oitavas ficam fora. A exceção é um clube acompanhado integralmente em uma categoria permitida, como o São Paulo masculino sub-20.

Nos jogos permitidos, São Paulo prevalece em `sao-paulo`, clube regional em `clubes-regionais` e Red Bull Bragantino em `red-bull`. Sem prioridade anterior, o evento usa `outros-esportes`. Palmeiras x Santos nas oitavas, por exemplo, usa `outros-esportes`.

## Competições internacionais de clubes

- Libertadores e Champions League: todos os jogos a partir das quartas de final.
- Sul-Americana, Europa League e Conference League: a partir das semifinais.
- Mundial de Clubes e Copa Intercontinental da FIFA: todos os jogos.
- Outros torneios continentais ou internacionais: a partir das semifinais.
- Um clube acompanhado por regra mais abrangente mantém seus jogos em fases anteriores.

## Seleções e Copas do Mundo

São acompanhadas as seleções brasileiras de futebol principal, sub-20 e sub-17, masculinas e femininas. A seleção olímpica masculina não é tratada como principal.

Também entram competições masculinas relevantes de seleções e todas as eliminatórias da Copa do Mundo nas confederações reconhecidas.

São incluídos todos os jogos das Copas do Mundo masculina e feminina, principal, sub-20 e sub-17. Eventos com Brasil usam `selecao-brasileira`; os demais usam `copas-do-mundo`.

As seleções brasileiras principais masculina e feminina de vôlei, basquete e futsal são acompanhadas. Seleções de base dessas modalidades entram somente quando abrangidas por Olimpíadas ou Pan.

## Automobilismo

Categorias acompanhadas:

- Formula Regional European Championship;
- Fórmula 4 Brasil;
- Fórmula 4 Italiana;
- Fórmula 4 Espanhola;
- E4 Championship.

Entram somente corridas principais e corridas sprint. Ficam fora treinos livres, classificações, testes, warm-up, shakedown, coletivas, cerimônias e demais sessões não competitivas.

## Tênis

Somente partidas individuais de simples. Duplas masculinas, femininas ou mistas são sempre excluídas, inclusive em Copa Davis, Billie Jean King Cup e United Cup.

João Fonseca é prioritário. Futuros coletores devem revisar os rankings ATP e WTA de simples e monitorar os três brasileiros e as três brasileiras mais bem colocados, sem duplicar João Fonseca.

Para atletas brasileiros prioritários, qualquer fase oficial de simples pode entrar quando adversário, data e horário estiverem confirmados.

Para os demais jogos:

- ATP/WTA 250 e 500: semifinais e final;
- ATP/WTA 1000: quartas, semifinais e final;
- Grand Slams: oitavas, quartas, semifinais e final;
- Copa Davis, Billie Jean King Cup e United Cup: simples a partir das quartas;
- ATP Finals, WTA Finals e Next Gen ATP Finals: todas as partidas de simples desde a fase de grupos.

## Esportes americanos

- NFL: temporada regular do New York Giants e todos os jogos de Wild Card, Divisional, finais de conferência e Super Bowl.
- MLB: todos os jogos confirmados da World Series.
- NBA: todos os jogos confirmados das finais, sem publicar partidas opcionais como garantidas.
- MLS: final da MLS Cup ou série final, conforme o formato vigente.

## Olimpíadas, Pan e esportes individuais

Em Jogos Olímpicos de Verão ou Inverno e Jogos Pan-Americanos, entram todas as provas e partidas com Brasil e todas as disputas por medalha. Preliminares sem brasileiros ficam fora quando não decidem medalha.

Em esportes individuais, entram finais, disputas por medalha e fases realmente decisivas envolvendo atletas brasileiros de destaque, incluindo surfe, skate, ginásticas, judô, atletismo e natação.

## Transmissão no Brasil

A transmissão é pesquisada para o evento específico; direitos gerais de uma competição não bastam. Todas as opções confirmadas podem ser listadas. Sem confirmação confiável, a descrição usa `ainda não confirmada`.

## Cancelamentos e adiamentos

- Cancelados permanecem publicados com `STATUS:CANCELLED`.
- Adiados preservam o UID, usam `STATUS:TENTATIVE` no ICS e mostram `Adiado` na descrição.
- Atualizações devem manter o UID permanente e aumentar `SEQUENCE` quando houver histórico suficiente.

## Deduplicação e UID

A ordem de deduplicação é:

1. fonte mais identificador externo sanitizado;
2. UID permanente;
3. chave canônica de modalidade, categoria, competição, fase e participantes;
4. horário apenas como auxílio, nunca como único critério.

Diferenças de acentuação, abreviação, ordem dos participantes, separadores e pequenos ajustes de horário não devem criar cópias. O registro mais completo é preservado e reúne transmissão, local, fonte e maior `SEQUENCE`.

IDs originais do Google Calendar são substituídos por SHA-256 de `google-calendar:` mais o ID original. A data e o horário não participam da identidade permanente.

## Títulos e descrição pública

Os títulos devem ser objetivos e consistentes, indicando modalidade, confronto ou prova, competição e fase. A descrição pública pode conter somente transmissão, competição, fase, local, cidade/país, status, fonte pública e última verificação.

## Dados proibidos

Não são armazenados ou publicados:

- e-mails, convidados ou `attendees`;
- organizador, criador ou confirmação de presença;
- ID privado de agenda;
- ID original do evento do Google Calendar;
- chave de sincronização original;
- Google Meet, links privados de Zoom ou dados de conferência;
- links de edição ou resposta;
- tokens, credenciais, chaves privadas ou secrets;
- notas privadas e dados das abas internas da planilha.

O snapshot de produção usa somente a aba `Eventos`. A automação do GitHub gera os feeds a partir de `data/events.json` e não acessa a planilha privada.
