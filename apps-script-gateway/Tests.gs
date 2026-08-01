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

function testCalendarSequence_() {
  const event = {
    uid: 'sequence@sports-calendar-hub', title: 'Evento', status: 'CONFIRMED',
    start: '2026-08-01T20:00:00-03:00', end: '2026-08-01T22:00:00-03:00',
    timezone: 'America/Sao_Paulo', color_id: 7, sequence: 2
  };
  const desired = desiredCalendarEvent_(event, 'existing', 8);
  assertGateway_(desired.sequence === 8, 'calendar_sequence_not_lowered');
  assertGateway_(desiredComparable_(desired).sequence === 2, 'source_sequence_preserved');
}

function testDeletedTombstone_() {
  assertGateway_(isDeletedTombstone_({status: 'cancelled', summary: 'Evento antigo'}), 'legacy_cancelled_is_tombstone');
  assertGateway_(!isDeletedTombstone_({
    status: 'cancelled', extendedProperties: {private: {sports_calendar_uid: 'cancelled@sports-calendar-hub'}}
  }), 'managed_cancelled_is_event');
}

function testRollbackSnapshotRetention_() {
  const values = {
    'ROLLBACK_apply-20260720100000-aaaaaaaaaaaa_COUNT': '2',
    'ROLLBACK_apply-20260720100000-aaaaaaaaaaaa_0': 'old-0',
    'ROLLBACK_apply-20260720100000-aaaaaaaaaaaa_1': 'old-1',
    'ROLLBACK_apply-20260721100000-bbbbbbbbbbbb_COUNT': '1',
    'ROLLBACK_apply-20260721100000-bbbbbbbbbbbb_0': 'new-0',
    'UNRELATED_PROPERTY': 'keep'
  };
  const mockProps = {
    getProperties: function () { return Object.assign({}, values); },
    deleteProperty: function (key) { delete values[key]; }
  };
  const ids = rollbackExecutionIds_(values);
  assertGateway_(ids.length === 2, 'rollback_ids_found');
  assertGateway_(ids[0] === 'apply-20260721100000-bbbbbbbbbbbb', 'rollback_ids_newest_first');
  pruneRollbackSnapshots_(mockProps, 1);
  assertGateway_(!values['ROLLBACK_apply-20260720100000-aaaaaaaaaaaa_COUNT'], 'old_snapshot_count_removed');
  assertGateway_(!values['ROLLBACK_apply-20260720100000-aaaaaaaaaaaa_0'], 'old_snapshot_chunks_removed');
  assertGateway_(values['ROLLBACK_apply-20260721100000-bbbbbbbbbbbb_COUNT'] === '1', 'new_snapshot_retained');
  assertGateway_(values.UNRELATED_PROPERTY === 'keep', 'unrelated_property_retained');
}

function testPhaseRoundCompaction_() {
  assertGateway_(
    compactPhaseRound_('rodada 1 — rodada 1 — rodada 1') === 'rodada 1',
    'identical_phase_segments_collapsed'
  );
  assertGateway_(
    compactPhaseRound_('fase inicial — rodada não informada — fase inicial — rodada não informada') ===
      'fase inicial — rodada não informada',
    'repeated_phase_round_pair_collapsed'
  );
  assertGateway_(
    compactPhaseRound_('Corrida 1 — Etapa 5') === 'Corrida 1 — Etapa 5',
    'distinct_phase_round_preserved'
  );
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
  testCalendarSequence_();
  testDeletedTombstone_();
  testRollbackSnapshotRetention_();
  testPhaseRoundCompaction_();
  testExportSafe_();
  return {ok: true, tests: 8, calendar_writes: 0};
}
