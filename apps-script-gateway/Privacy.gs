function cleanText_(value) {
  return String(value || '').replace(/<[^>]*>/g, ' ').replace(/[\r\n\t]+/g, ' ')
    .replace(/\s+/g, ' ').trim()
    .replace(/[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/ig, '')
    .replace(/https?:\/\/(?:calendar\.google\.com|meet\.google\.com|(?:www\.)?zoom\.us)\S*/ig, '')
    .replace(/\s+/g, ' ').trim();
}

function cleanUrl_(value) {
  const candidate = String(value || '').trim();
  if (!/^https?:\/\//i.test(candidate)) return '';
  if (/calendar\.google\.com|meet\.google\.com|(?:www\.)?zoom\.us/i.test(candidate)) return '';
  return candidate.split('#')[0];
}

function privacyViolations_(event) {
  const text = JSON.stringify(event);
  const issues = [];
  ['attendees', 'organizer', 'creator', 'conferenceData', 'conference_data', 'calendar_id',
    'event_id', 'edit_link', 'response_link', 'token'].forEach(function (field) {
      if (Object.prototype.hasOwnProperty.call(event, field)) issues.push('forbidden_field:' + field);
  });
  if (/[A-Z0-9._%+-]+@(?!sports-calendar-hub)[A-Z0-9.-]+\.[A-Z]{2,}/i.test(text)) issues.push('email');
  if (/meet\.google\.com|calendar\.google\.com|(?:www\.)?zoom\.us/i.test(text)) issues.push('private_url');
  return issues;
}

function validateIncomingEvent_(event) {
  const required = ['uid', 'title', 'sport', 'category', 'start', 'end', 'timezone',
    'status', 'color_group', 'color_id', 'transparency', 'managed_by', 'scope_version'];
  const missing = required.filter(function (key) { return event[key] === undefined || event[key] === null || event[key] === ''; });
  const issues = privacyViolations_(event);
  if (missing.length) issues.push('missing:' + missing.join(','));
  if (!/@sports-calendar-hub$/.test(String(event.uid || ''))) issues.push('invalid_uid');
  if (event.timezone !== 'America/Sao_Paulo') issues.push('invalid_timezone');
  if (event.transparency !== 'TRANSPARENT') issues.push('invalid_transparency');
  if (event.managed_by !== SCH_MANAGED_BY || event.scope_version !== SCH_SCHEMA_VERSION) issues.push('invalid_management_marker');
  if (!SCH_COLOR_IDS[event.color_group] || SCH_COLOR_IDS[event.color_group] !== String(event.color_id)) issues.push('invalid_color');
  if (['CONFIRMED', 'TENTATIVE', 'POSTPONED', 'CANCELLED'].indexOf(event.status) < 0) issues.push('invalid_status');
  if (!isEventInScope_(event)) issues.push('out_of_scope');
  return issues;
}
