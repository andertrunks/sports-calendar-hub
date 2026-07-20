function assertGateway_(condition, message) {
  if (!condition) throw new Error('test_failed:' + message);
}

function testCanonicalKey_() {
  const first = {sport: 'Futebol', category: 'Masculino', competition: 'Brasileirão', phase: 'Rodada 1', round: '', participant_1: 'São Paulo', participant_2: 'Palmeiras'};
  const second = {sport: 'futebol', category: 'masculino', competition: 'Brasileirao', phase: 'Rodada 1', round: '', participant_1: 'Palmeiras', participant_2: 'Sao Paulo'};
  assertGateway_(canonicalKey_(first) === canonicalKey_(second), 'canonical_participant_order');
}

function testPrivacy_() {
  const event = {uid: 'abc@sports-calendar-hub', title: 'Evento público'};
  assertGateway_(privacyViolations_(event).length === 0, 'public_uid');
  event.attendees = ['private@example.com'];
  assertGateway_(privacyViolations_(event).length > 0, 'attendees_blocked');
}

function testPermanentUid_() {
  const event = {external_id_hash: sha256Hex_('stable'), sport: 'Futebol', category: 'Masculino', competition: 'Copa', phase: 'Final', round: '', participant_1: 'A', participant_2: 'B'};
  const uid = permanentUid_(event);
  event.start = '2026-08-01T20:00:00-03:00';
  assertGateway_(uid === permanentUid_(event), 'uid_time_independent');
}

function testExportSafe_() {
  const exported = exportSanitizedEvents_();
  assertGateway_(exported.event_count === exported.events.length, 'export_count');
  assertGateway_(exported.data_hash === dataHash_(exported.events), 'export_hash');
  exported.events.forEach(function (event) { assertGateway_(privacyViolations_(event).length === 0, 'export_privacy'); });
}

function runGatewayTests() {
  testCanonicalKey_();
  testPrivacy_();
  testPermanentUid_();
  testExportSafe_();
  return {ok: true, tests: 4, calendar_writes: 0};
}
