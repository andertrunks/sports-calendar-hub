function containsAny_(text, terms) {
  text = normalizeText_(text);
  return terms.some(function (term) { return text.indexOf(normalizeText_(term)) >= 0; });
}

function colorGroupFor_(event) {
  const participants = normalizeText_([event.participant_1, event.participant_2, event.title].join(' '));
  const competition = normalizeText_(event.competition);
  const all = normalizeText_([event.sport, event.category, event.competition, event.phase, event.title].join(' '));
  if (participants.indexOf('sao paulo') >= 0) return 'sao-paulo';
  if (/(^| )brasil( |$)|selecao brasileira/.test(participants)) return 'selecao-brasileira';
  if (containsAny_(participants, ['Ferroviária', 'Portuguesa-SP', 'Juventus-SP', 'Matonense', 'São Carlos-SP', 'Grêmio Sãocarlense', 'Botafogo-SP', 'Comercial-SP'])) return 'clubes-regionais';
  if (containsAny_(participants, ['Red Bull', 'RB Leipzig', 'RB Salzburg', 'RB Omiya'])) return 'red-bull';
  if (competition.indexOf('premier league') >= 0) return 'premier-league';
  if (containsAny_(competition, ['Libertadores', 'Sul-Americana', 'Champions League', 'Europa League', 'Conference League', 'Mundial de Clubes', 'Intercontinental'])) return 'continentais';
  if (containsAny_(all, ['automobilismo', 'motorsport', 'formula', 'fórmula', 'indycar', 'nascar', 'dtm'])) return 'automobilismo';
  if (containsAny_(competition, ['Brasileirão', 'Campeonato Brasileiro Série A'])) return 'brasileirao';
  if (containsAny_(competition, ['Olimpíadas', 'Jogos Olímpicos', 'Pan-Americanos'])) return 'olimpiadas-pan';
  if (containsAny_(competition, ['Copa do Mundo', 'World Cup'])) return 'copas-do-mundo';
  return 'outros-esportes';
}

function isEventInScope_(event) {
  const all = normalizeText_([event.title, event.sport, event.category, event.competition,
    event.phase, event.participant_1, event.participant_2].join(' '));
  if (containsAny_(all, ['Paralimpíadas', 'Parapan', 'paralímpico', 'paralimpico'])) return false;
  const participants = normalizeText_([event.participant_1, event.participant_2, event.title].join(' '));
  if (participants.indexOf('sao paulo') >= 0 && all.indexOf('feminin') >= 0 &&
      containsAny_(all, ['sub-17', 'sub 17', 'u17', 'sub-20', 'sub 20', 'u20', 'base'])) return false;
  if (containsAny_(all, ['automobilismo', 'motorsport', 'formula', 'fórmula', 'indycar', 'nascar', 'dtm'])) {
    if (containsAny_(all, ['treino', 'practice', 'qualifying', 'classificação', 'teste', 'warm-up', 'warm up'])) return false;
    return containsAny_(all, ['corrida', 'race', 'sprint']);
  }
  if (containsAny_(all, ['tênis', 'tenis', 'tennis']) && containsAny_(all, ['duplas', 'doubles'])) {
    return containsAny_(all, ['Copa Davis', 'Billie Jean King', 'United Cup']);
  }
  return true;
}
