function doGet(e) {
  let cfg;
  try { cfg = config_(); } catch (error) { return jsonOutput_({ok: false, error: 'configuration_error'}); }
  if (!e || e.parameter.action !== 'export' || !authorized_(e.parameter.token, cfg.EXPORT_TOKEN)) return unauthorized_();
  try { return jsonOutput_(exportSanitizedEvents_()); }
  catch (error) { return jsonOutput_({ok: false, error: 'export_failed'}); }
}

function doPost(e) {
  let cfg;
  try { cfg = config_(); } catch (error) { return jsonOutput_({ok: false, error: 'configuration_error'}); }
  const raw = e && e.postData && e.postData.contents || '';
  if (!raw || raw.length > SCH_MAX_REQUEST_BYTES) return jsonOutput_({ok: false, error: 'invalid_request'});
  let request;
  try { request = JSON.parse(raw); } catch (error) { return jsonOutput_({ok: false, error: 'invalid_json'}); }
  if (!authorized_(request.token, cfg.SYNC_TOKEN)) return unauthorized_();
  if (request.action === 'rollback') {
    if (!request.execution_id) return jsonOutput_({ok: false, error: 'invalid_rollback_request'});
    try { return jsonOutput_(rollback_(request.execution_id, request.dry_run !== false, cfg)); }
    catch (error) { return jsonOutput_({ok: false, error: 'rollback_failed'}); }
  }
  if (request.action !== 'sync' || request.schema_version !== SCH_SCHEMA_VERSION || !Array.isArray(request.events)) {
    return jsonOutput_({ok: false, error: 'invalid_request'});
  }
  if (request.source_hash !== dataHash_(request.events)) return jsonOutput_({ok: false, error: 'invalid_source_hash'});
  request.dry_run = request.dry_run !== false;
  const executionId = executionId_(request.source_hash, request.dry_run);
  if (request.dry_run) {
    try {
      const plan = buildSyncPlan_(request.events, cfg);
      return jsonOutput_(syncResponse_(request, plan, executionId, null, cfg));
    } catch (error) { return jsonOutput_({ok: false, error: 'dry_run_failed'}); }
  }
  const lock = LockService.getScriptLock();
  if (!lock.tryLock(30000)) return jsonOutput_({ok: false, error: 'sync_locked'});
  try {
    const plan = buildSyncPlan_(request.events, cfg);
    if (plan.blockers.length) return jsonOutput_(syncResponse_(request, plan, executionId, null, cfg));
    const result = applySyncPlan_(plan, cfg, executionId);
    const verification = buildSyncPlan_(request.events, cfg);
    result.post_validation = publicPlan_(verification);
    if (verification.create.length || verification.update.length || verification.delete.length || verification.blockers.length) {
      verification.blockers.push({issues: ['post_apply_validation_failed']});
      return jsonOutput_(syncResponse_(request, verification, executionId, result, cfg));
    }
    return jsonOutput_(syncResponse_(request, verification, executionId, result, cfg));
  } catch (error) {
    return jsonOutput_({ok: false, error: 'apply_failed'});
  } finally {
    lock.releaseLock();
  }
}
