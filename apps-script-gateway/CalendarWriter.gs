function descriptionFor_(event) {
  const lines = [
    '📺 Transmissão no Brasil: ' + (event.broadcaster_br || 'ainda não confirmada'),
    '🏆 Competição: ' + (event.competition || 'não informada'),
    '📍 Fase/Rodada: ' + ([event.phase, event.round].filter(Boolean).join(' — ') || 'não informada'),
    '🏟️ Local: ' + (event.location || 'não informado'),
    '🌎 Cidade/País: ' + ([event.city, event.state, event.country].filter(Boolean).join(', ') || 'não informado'),
    'ℹ️ Status: ' + event.status,
    '🔗 Fonte oficial: ' + (event.source_url || 'ainda não informada'),
    '🕒 Última verificação: ' + (event.last_verified || 'não informada')
  ];
  if (event.all_day) lines.push('🕒 Horário: a confirmar');
  if (event.highlight_reason) lines.push('⭐ Destaque: ' + event.highlight_reason);
  return lines.join('\n');
}

function desiredCalendarEvent_(event, existingId, existingSequence) {
  let summary = event.title;
  if (event.status === 'POSTPONED' && normalizeText_(summary).indexOf('adiado') < 0) summary = 'Adiado — ' + summary;
  const location = [event.location, event.city, event.state, event.country].filter(Boolean).join(' — ');
  const resource = {
    summary: summary,
    description: descriptionFor_(event),
    location: location,
    start: event.all_day ? {date: event.start} : {dateTime: event.start, timeZone: event.timezone},
    end: event.all_day ? {date: event.end} : {dateTime: event.end, timeZone: event.timezone},
    status: event.status === 'CANCELLED' ? 'cancelled' : (event.status === 'TENTATIVE' || event.status === 'POSTPONED' ? 'tentative' : 'confirmed'),
    transparency: 'transparent',
    colorId: String(event.color_id),
    sequence: Math.max(Number(event.sequence || 0), Number(existingSequence || 0)),
    extendedProperties: {private: {
      sports_calendar_uid: event.uid,
      sports_calendar_managed: 'true',
      sports_calendar_scope_version: SCH_SCHEMA_VERSION,
      sports_calendar_external_id_hash: event.external_id_hash || '',
      sports_calendar_sequence: String(event.sequence || 0)
    }}
  };
  if (existingId) resource.id = existingId;
  return resource;
}

function projectedExisting_(event) {
  const privateProps = eventPrivate_(event);
  return {
    summary: event.summary || '', description: event.description || '', location: event.location || '',
    start: event.start || {}, end: event.end || {}, status: event.status || 'confirmed',
    transparency: event.transparency || 'opaque', colorId: String(event.colorId || ''),
    sequence: Number(privateProps.sports_calendar_sequence || 0), extendedProperties: {private: privateProps}
  };
}

function desiredComparable_(desired) {
  return {
    summary: desired.summary, description: desired.description, location: desired.location,
    start: desired.start, end: desired.end, status: desired.status,
    transparency: desired.transparency, colorId: String(desired.colorId || ''),
    sequence: Number(desired.extendedProperties.private.sports_calendar_sequence || 0),
    extendedProperties: desired.extendedProperties
  };
}

function existingScore_(event, incoming) {
  const p = eventPrivate_(event);
  let score = p.sports_calendar_managed === 'true' ? 1000 : 0;
  if (incoming.external_id_hash && externalIdHash_(event.id, '') === incoming.external_id_hash) score += 500;
  if (event.status !== 'cancelled') score += 40;
  if (!(event.attendees && event.attendees.length)) score += 20;
  if (!event.conferenceData) score += 20;
  ['summary', 'description', 'location', 'start', 'end', 'colorId'].forEach(function (field) {
    if (event[field]) score += 1;
  });
  return score;
}

function safeSportsDuplicate_(event) {
  return Boolean(event && event.id && !event.recurringEventId);
}

function uniqueEvents_(items) {
  const seen = {};
  return items.filter(function (item) { if (!item || seen[item.id]) return false; seen[item.id] = true; return true; });
}

function chooseExisting_(matches, incoming) {
  return matches.slice().sort(function (left, right) {
    return existingScore_(right, incoming) - existingScore_(left, incoming);
  })[0] || null;
}

function eventStartValue_(event) {
  return event.start && (event.start.dateTime || event.start.date) || '';
}

function isFutureExisting_(event) {
  const value = eventStartValue_(event);
  return value && new Date(value).getTime() >= new Date().setHours(0, 0, 0, 0);
}

function explicitlyExcludedExisting_(event) {
  const text = normalizeText_([event.summary, event.description, event.location].filter(Boolean).join(' '));
  const paralympic = /paralimp|parapan|goalball|volei sentado|cadeira de rodas|futebol de cegos|bocha paralimp|parabadminton|paratletismo|paranatacao/.test(text);
  const saoPauloBaseWomen = /sao paulo/.test(text) && /feminin|mulheres/.test(text) && /sub 17|sub 20|u17|u20|base/.test(text);
  const motorContext = /formula|f[1-4]|corrida|stock car|tcr|imsa|wec|dtm|automobil/.test(text);
  const prohibitedSession = /treino|classificacao|teste|warm up|shakedown|prologo|cerimon|promocional/.test(text);
  return paralympic || saoPauloBaseWomen || (motorContext && prohibitedSession);
}

function buildSyncPlan_(events, cfg) {
  const window = calendarWindow_();
  const existing = listCalendarEvents_(cfg.SPORTS_CALENDAR_ID, window.timeMin, window.timeMax);
  const indexes = existingIndexes_(existing);
  const primary = listCalendarEvents_('primary', window.timeMin, window.timeMax);
  const plan = {
    create: [], update: [], unchanged: [], delete: [], duplicate_reviews: [],
    primary_duplicate_reviews: primaryDuplicateReviews_(events, primary), blockers: [],
    missing_uid: 0, privacy_violations: 0, primary_delete: 0,
    existing_future: existing.filter(isFutureExisting_).length, protected_ids: {}, delete_ids: {}
  };
  const incomingUids = {};
  events.forEach(function (event) {
    const issues = validateIncomingEvent_(event);
    if (issues.length) {
      plan.privacy_violations += issues.filter(function (issue) { return issue.indexOf('forbidden') === 0 || issue === 'email' || issue === 'private_url'; }).length;
      if (issues.indexOf('invalid_uid') >= 0 || issues.some(function (i) { return i.indexOf('missing:') === 0; })) plan.missing_uid += 1;
      plan.blockers.push({uid: event.uid || '', issues: issues});
      return;
    }
    if (incomingUids[event.uid]) {
      plan.blockers.push({uid: event.uid, issues: ['duplicate_uid_in_request']});
      return;
    }
    incomingUids[event.uid] = true;
    const canonical = normalizeText_(event.title) + '|' + String(event.start).slice(0, 10);
    const matches = uniqueEvents_([].concat(indexes.byUid[event.uid] || [],
      indexes.byExternal[event.external_id_hash] || [], indexes.byCanonical[canonical] || []));
    const selected = chooseExisting_(matches, event);
    const desired = desiredCalendarEvent_(event, selected && selected.id, selected && selected.sequence);
    if (!selected) {
      desired.id = sha256Hex_(event.uid).slice(0, 64);
      plan.create.push({event: event, desired: desired});
    } else if (JSON.stringify(canonicalize_(projectedExisting_(selected))) === JSON.stringify(canonicalize_(desiredComparable_(desired))) &&
        !(selected.attendees && selected.attendees.length) && !selected.conferenceData) {
      plan.unchanged.push({event: event, existing: selected});
    } else {
      plan.update.push({event: event, existing: selected, desired: desired});
    }
    if (selected) plan.protected_ids[selected.id] = true;
    matches.filter(function (item) { return !selected || item.id !== selected.id; }).forEach(function (duplicate) {
      if (safeSportsDuplicate_(duplicate)) {
        if (!plan.delete_ids[duplicate.id]) {
          plan.delete.push({event: event, existing: duplicate, reason: 'confirmed_duplicate'});
          plan.delete_ids[duplicate.id] = true;
        }
      } else {
        plan.duplicate_reviews.push({uid: event.uid, title: event.title, reason: 'duplicate_not_safe_to_delete', action: 'REVISÃO_MANUAL'});
      }
    });
  });
  plan.delete = plan.delete.filter(function (item) { return !plan.protected_ids[item.existing.id]; });
  const retainedDeleteIds = {};
  plan.delete.forEach(function (item) { retainedDeleteIds[item.existing.id] = true; });
  plan.delete_ids = retainedDeleteIds;
  existing.forEach(function (event) {
    if (!isFutureExisting_(event) || plan.protected_ids[event.id] || plan.delete_ids[event.id]) return;
    if (!event.recurringEventId && explicitlyExcludedExisting_(event)) {
      plan.delete.push({event: null, existing: event, reason: 'explicit_scope_exclusion'});
      plan.delete_ids[event.id] = true;
    }
  });
  return plan;
}

function publicPlan_(plan) {
  const duplicateDeletes = plan.delete.filter(function (item) { return item.reason === 'confirmed_duplicate'; }).length;
  const scopeDeletes = plan.delete.filter(function (item) { return item.reason === 'explicit_scope_exclusion'; }).length;
  return {
    create: plan.create.length, update: plan.update.length, unchanged: plan.unchanged.length,
    delete: plan.delete.length, primary_delete: 0, missing_uid: plan.missing_uid,
    duplicate_delete: duplicateDeletes, scope_delete: scopeDeletes,
    existing_future: plan.existing_future, privacy_violations: plan.privacy_violations,
    duplicate_reviews: plan.duplicate_reviews.length
  };
}

function snapshotRecord_(operation, item) {
  if (operation === 'create') return {operation: operation, id: item.desired.id};
  const event = item.existing;
  return {operation: operation, id: event.id, resource: {
    summary: event.summary || '', description: event.description || '', location: event.location || '',
    start: event.start, end: event.end, status: event.status, transparency: event.transparency,
    colorId: event.colorId, sequence: event.sequence || 0, extendedProperties: event.extendedProperties || {}
  }};
}

function saveRollbackSnapshot_(executionId, plan) {
  const records = [];
  plan.create.forEach(function (item) { records.push(snapshotRecord_('create', item)); });
  plan.update.forEach(function (item) { records.push(snapshotRecord_('update', item)); });
  plan.delete.forEach(function (item) { records.push(snapshotRecord_('delete', item)); });
  const text = JSON.stringify(records);
  const props = PropertiesService.getScriptProperties();
  const size = 7000;
  const parts = Math.ceil(text.length / size);
  props.setProperty('ROLLBACK_' + executionId + '_COUNT', String(parts));
  for (let i = 0; i < parts; i += 1) props.setProperty('ROLLBACK_' + executionId + '_' + i, text.slice(i * size, (i + 1) * size));
}

function loadRollbackSnapshot_(executionId) {
  const props = PropertiesService.getScriptProperties();
  const count = Number(props.getProperty('ROLLBACK_' + executionId + '_COUNT') || 0);
  if (!count) throw new Error('rollback_snapshot_not_found');
  let text = '';
  for (let i = 0; i < count; i += 1) text += props.getProperty('ROLLBACK_' + executionId + '_' + i) || '';
  return JSON.parse(text);
}

function applySyncPlan_(plan, cfg, executionId) {
  saveRollbackSnapshot_(executionId, plan);
  const result = {created: 0, updated: 0, unchanged: plan.unchanged.length, deleted: 0};
  try {
    plan.create.forEach(function (item) {
      Calendar.Events.insert(item.desired, cfg.SPORTS_CALENDAR_ID, {sendUpdates: 'none', conferenceDataVersion: 1});
      result.created += 1;
    });
    plan.update.forEach(function (item) {
      Calendar.Events.update(item.desired, cfg.SPORTS_CALENDAR_ID, item.existing.id,
        {sendUpdates: 'none', conferenceDataVersion: 1});
      result.updated += 1;
    });
    plan.delete.forEach(function (item) {
      Calendar.Events.remove(cfg.SPORTS_CALENDAR_ID, item.existing.id, {sendUpdates: 'none'});
      result.deleted += 1;
    });
    return result;
  } catch (error) {
    try {
      rollback_(executionId, false, cfg);
    } catch (rollbackError) {
      throw new Error('apply_operation_failed: ' + safeGatewayError_(error) +
        '; rollback_failed: ' + safeGatewayError_(rollbackError));
    }
    throw new Error('apply_operation_failed: ' + safeGatewayError_(error) + '; rollback_restored');
  }
}

function rollback_(executionId, dryRun, cfg) {
  const records = loadRollbackSnapshot_(executionId);
  const plan = {remove_created: 0, restore: 0};
  records.forEach(function (record) { if (record.operation === 'create') plan.remove_created += 1; else plan.restore += 1; });
  if (dryRun) return {ok: true, schema_version: SCH_SCHEMA_VERSION, action: 'rollback', dry_run: true, execution_id: executionId, calendar: SCH_CALENDAR_NAME, plan: plan, blockers: []};
  records.forEach(function (record) {
    if (record.operation === 'create') {
      try { Calendar.Events.remove(cfg.SPORTS_CALENDAR_ID, record.id, {sendUpdates: 'none'}); } catch (error) {}
    } else {
      const current = Calendar.Events.get(cfg.SPORTS_CALENDAR_ID, record.id);
      const resource = JSON.parse(JSON.stringify(record.resource));
      resource.sequence = Math.max(Number(resource.sequence || 0), Number(current.sequence || 0));
      Calendar.Events.update(resource, cfg.SPORTS_CALENDAR_ID, record.id,
        {sendUpdates: 'none', conferenceDataVersion: 1});
    }
  });
  return {ok: true, schema_version: SCH_SCHEMA_VERSION, action: 'rollback', dry_run: false, execution_id: executionId, calendar: SCH_CALENDAR_NAME, plan: plan, blockers: []};
}

function specialAudit_(events, cfg) {
  const target = events.filter(function (event) { return normalizeText_(event.title).indexOf('coritiba x palmeiras') >= 0; });
  if (!target.length) return {found_in_source: false, action: 'not_recreated'};
  const window = calendarWindow_();
  const calendarEvents = listCalendarEvents_(cfg.SPORTS_CALENDAR_ID, window.timeMin, window.timeMax);
  const matches = calendarEvents.filter(function (event) { return normalizeText_(event.summary).indexOf('coritiba x palmeiras') >= 0; });
  return {
    found_in_source: true, versions_in_sports_calendar: matches.length,
    color_7: matches.every(function (event) { return String(event.colorId) === '7'; }),
    transparent: matches.every(function (event) { return event.transparency === 'transparent'; }),
    no_attendees_or_conference: matches.every(function (event) { return !(event.attendees && event.attendees.length) && !event.conferenceData; })
  };
}
