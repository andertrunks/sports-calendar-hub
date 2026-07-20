function headerMap_(headers) {
  const map = {};
  headers.forEach(function (value, index) { map[normalizeText_(value)] = index; });
  return map;
}

function cell_(row, headers, names) {
  for (let i = 0; i < names.length; i += 1) {
    const index = headers[normalizeText_(names[i])];
    if (index !== undefined && row[index] !== '') return String(row[index]).trim();
  }
  return '';
}

function parseDate_(value) {
  const match = String(value || '').match(/(\d{1,2})[\/-](\d{1,2})[\/-](\d{4})/);
  if (!match) throw new Error('invalid_date');
  return {year: Number(match[3]), month: Number(match[2]), day: Number(match[1])};
}

function parseTime_(value) {
  const match = String(value || '').match(/(\d{1,2}):(\d{2})/);
  return match ? {hour: Number(match[1]), minute: Number(match[2])} : null;
}

function isoDateTime_(date, time, timezone) {
  const local = new Date(date.year, date.month - 1, date.day, time.hour, time.minute, 0, 0);
  return Utilities.formatDate(local, timezone, "yyyy-MM-dd'T'HH:mm:ssXXX");
}

function verifiedIso_(value, timezone) {
  const text = String(value || '').trim();
  if (!text) return Utilities.formatDate(new Date(), timezone, "yyyy-MM-dd'T'HH:mm:ssXXX");
  const match = text.match(/(\d{1,2})[\/-](\d{1,2})[\/-](\d{4})(?:\s+(\d{1,2}):(\d{2})(?::(\d{2}))?)?/);
  if (!match) return text;
  const date = new Date(Number(match[3]), Number(match[2]) - 1, Number(match[1]),
    Number(match[4] || 0), Number(match[5] || 0), Number(match[6] || 0));
  return Utilities.formatDate(date, timezone, "yyyy-MM-dd'T'HH:mm:ssXXX");
}

function normalizeStatus_(value) {
  const text = normalizeText_(value);
  if (text.indexOf('cancel') >= 0) return 'CANCELLED';
  if (text.indexOf('adiad') >= 0 || text.indexOf('postpon') >= 0) return 'POSTPONED';
  if (text.indexOf('tentativ') >= 0 || text.indexOf('provisori') >= 0 || text.indexOf('a confirmar') >= 0) return 'TENTATIVE';
  return 'CONFIRMED';
}

function ageAndGender_(category) {
  const text = normalizeText_(category);
  const age = text.match(/(?:sub|u)\s*(\d{2})/);
  return {
    age_group: age ? 'u' + age[1] : (text.indexOf('profissional') >= 0 ? 'senior' : ''),
    gender: text.indexOf('feminin') >= 0 ? 'feminino' : (text.indexOf('masculin') >= 0 ? 'masculino' : '')
  };
}

function rowToExportEvent_(row, headers, cfg) {
  const date = parseDate_(cell_(row, headers, ['Data']));
  const startTime = parseTime_(cell_(row, headers, ['Hora de início', 'Início']));
  const endTime = parseTime_(cell_(row, headers, ['Hora de término', 'Término']));
  const timezone = cfg.TIMEZONE;
  const allDay = !startTime;
  let start;
  let end;
  if (allDay) {
    const local = new Date(date.year, date.month - 1, date.day);
    start = Utilities.formatDate(local, timezone, 'yyyy-MM-dd');
    local.setDate(local.getDate() + 1);
    end = Utilities.formatDate(local, timezone, 'yyyy-MM-dd');
  } else {
    start = isoDateTime_(date, startTime, timezone);
    const endValue = endTime || {hour: startTime.hour + 2, minute: startTime.minute};
    const startLocal = new Date(date.year, date.month - 1, date.day, startTime.hour, startTime.minute);
    const endLocal = new Date(date.year, date.month - 1, date.day, endValue.hour, endValue.minute);
    if (endLocal <= startLocal) endLocal.setDate(endLocal.getDate() + 1);
    end = Utilities.formatDate(endLocal, timezone, "yyyy-MM-dd'T'HH:mm:ssXXX");
  }
  const category = cleanText_(cell_(row, headers, ['Categoria']));
  const ageGender = ageAndGender_(category);
  const cityRaw = cleanText_(cell_(row, headers, ['Cidade']));
  const stateMatch = cityRaw.match(/,\s*([A-Z]{2})$/);
  const event = {
    external_id_hash: externalIdHash_(cell_(row, headers, ['ID do evento']), cell_(row, headers, ['Chave de sincronização'])),
    title: cleanText_(cell_(row, headers, ['Título'])),
    sport: cleanText_(cell_(row, headers, ['Modalidade'])),
    category: category,
    age_group: ageGender.age_group,
    gender: ageGender.gender,
    competition: cleanText_(cell_(row, headers, ['Competição'])),
    phase: cleanText_(cell_(row, headers, ['Fase ou rodada', 'Fase'])),
    round: cleanText_(cell_(row, headers, ['Fase ou rodada', 'Rodada'])),
    participant_1: cleanText_(cell_(row, headers, ['Participante 1'])),
    participant_2: cleanText_(cell_(row, headers, ['Participante 2'])),
    start: start, end: end, timezone: timezone, all_day: allDay,
    location: cleanText_(cell_(row, headers, ['Local'])),
    city: stateMatch ? cityRaw.replace(/,\s*[A-Z]{2}$/, '') : cityRaw,
    state: stateMatch ? stateMatch[1] : '',
    country: cleanText_(cell_(row, headers, ['País'])),
    broadcaster_br: cleanText_(cell_(row, headers, ['Transmissão no Brasil', 'Transmissão'])),
    status: normalizeStatus_(cell_(row, headers, ['Status'])),
    source_url: cleanUrl_(cell_(row, headers, ['Fonte oficial', 'Fonte'])),
    source_name: 'Controle de Eventos Esportivos — aba Eventos',
    color_group: '', color_id: '', transparency: 'TRANSPARENT', sequence: 0,
    last_verified: '', highlight_reason: ''
  };
  event.color_group = colorGroupFor_(event);
  event.color_id = SCH_COLOR_IDS[event.color_group];
  event.uid = permanentUid_(event);
  event.last_verified = verifiedIso_(cell_(row, headers, ['Última verificação']), timezone);
  return event;
}

function exportSanitizedEvents_() {
  const cfg = config_();
  const escapedSheetName = cfg.SHEET_NAME.replace(/'/g, "''");
  const response = Sheets.Spreadsheets.Values.get(
    cfg.SPREADSHEET_ID,
    "'" + escapedSheetName + "'!A:Z",
    {valueRenderOption: 'FORMATTED_VALUE', dateTimeRenderOption: 'FORMATTED_STRING'}
  );
  const values = response.values || [];
  if (!values.length) throw new Error('sheet_empty');
  const headers = headerMap_(values[0]);
  const events = [];
  values.slice(1).forEach(function (row) {
    if (!row.some(Boolean)) return;
    try {
      const event = rowToExportEvent_(row, headers, cfg);
      if (event.title && event.start && isEventInScope_(event)) events.push(event);
    } catch (error) {
      // Incomplete rows are ignored by the public export and remain visible in the audit sheet.
    }
  });
  events.sort(function (left, right) { return left.uid.localeCompare(right.uid); });
  return {
    ok: true,
    schema_version: SCH_SCHEMA_VERSION,
    timezone: cfg.TIMEZONE,
    generated_at: Utilities.formatDate(new Date(), cfg.TIMEZONE, "yyyy-MM-dd'T'HH:mm:ssXXX"),
    event_count: events.length,
    data_hash: dataHash_(events),
    events: events
  };
}
