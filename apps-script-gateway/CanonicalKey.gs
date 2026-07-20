function normalizeText_(value) {
  return String(value || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '')
    .toLowerCase().replace(/<[^>]*>/g, ' ').replace(/[^a-z0-9]+/g, ' ')
    .replace(/\s+/g, ' ').trim();
}

function sha256Hex_(value) {
  const bytes = Utilities.computeDigest(Utilities.DigestAlgorithm.SHA_256, String(value), Utilities.Charset.UTF_8);
  return bytes.map(function (byte) { const n = (byte + 256) % 256; return ('0' + n.toString(16)).slice(-2); }).join('');
}

function normalizeGoogleEventId_(value) {
  return String(value || '').trim().replace(/@google\.com$/i, '');
}

function externalIdHash_(rawId, syncKey) {
  const id = normalizeGoogleEventId_(rawId);
  if (id) return sha256Hex_('google-calendar:' + id);
  if (syncKey) return sha256Hex_('google-sheet-sync:' + String(syncKey).trim());
  return '';
}

function canonicalParticipants_(event) {
  return [normalizeText_(event.participant_1), normalizeText_(event.participant_2)].filter(Boolean).sort();
}

function canonicalKey_(event) {
  return [normalizeText_(event.sport), normalizeText_(event.category),
    normalizeText_(event.competition), normalizeText_(event.phase),
    normalizeText_(event.round)].concat(canonicalParticipants_(event)).join('|');
}

function permanentUid_(event) {
  if (event.uid && /@sports-calendar-hub$/.test(event.uid)) return event.uid;
  const identity = event.external_id_hash ? 'external|' + event.external_id_hash : 'canonical|' + canonicalKey_(event);
  return sha256Hex_(identity) + '@sports-calendar-hub';
}

function canonicalize_(value) {
  if (Array.isArray(value)) return value.map(canonicalize_);
  if (value && typeof value === 'object') {
    const out = {};
    Object.keys(value).sort().forEach(function (key) { out[key] = canonicalize_(value[key]); });
    return out;
  }
  return value;
}

function dataHash_(events) {
  return sha256Hex_(JSON.stringify(canonicalize_(events)));
}
