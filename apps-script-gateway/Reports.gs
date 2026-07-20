function jsonOutput_(value) {
  return ContentService.createTextOutput(JSON.stringify(value))
    .setMimeType(ContentService.MimeType.JSON);
}

function executionId_(sourceHash, dryRun) {
  return (dryRun ? 'dry-' : 'apply-') + Utilities.formatDate(new Date(), 'UTC', 'yyyyMMddHHmmss') + '-' + sourceHash.slice(0, 12);
}

function syncResponse_(request, plan, executionId, result, cfg) {
  return {
    ok: plan.blockers.length === 0,
    schema_version: SCH_SCHEMA_VERSION,
    action: 'sync',
    dry_run: Boolean(request.dry_run),
    source_hash: request.source_hash,
    execution_id: executionId,
    calendar: SCH_CALENDAR_NAME,
    plan: publicPlan_(plan),
    blockers: plan.blockers,
    duplicate_reviews: plan.duplicate_reviews,
    primary_duplicate_reviews: plan.primary_duplicate_reviews,
    result: result || null,
    special_audit: specialAudit_(request.events, cfg),
    privacy: {attendees: false, conference_data: false, primary_calendar_writes: false}
  };
}
