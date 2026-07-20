function listCalendarEvents_(calendarId, timeMin, timeMax) {
  const items = [];
  let pageToken;
  do {
    const response = Calendar.Events.list(calendarId, {
      timeMin: timeMin, timeMax: timeMax, singleEvents: true, maxResults: 2500,
      showDeleted: true, pageToken: pageToken
    });
    (response.items || []).forEach(function (event) {
      if (!isDeletedTombstone_(event)) items.push(event);
    });
    pageToken = response.nextPageToken;
  } while (pageToken);
  return items;
}

function isDeletedTombstone_(event) {
  return event.status === 'cancelled' && !eventPrivate_(event).sports_calendar_uid;
}

function calendarWindow_() {
  const now = new Date();
  const min = new Date(now.getTime() - 35 * 86400000);
  const max = new Date(now.getTime() + 370 * 86400000);
  return {timeMin: min.toISOString(), timeMax: max.toISOString()};
}

function eventPrivate_(event) {
  return ((event.extendedProperties || {}).private || {});
}

function existingIndexes_(events) {
  const indexes = {byUid: {}, byExternal: {}, byCanonical: {}};
  events.forEach(function (event) {
    const privateProps = eventPrivate_(event);
    const uid = privateProps.sports_calendar_uid;
    const external = privateProps.sports_calendar_external_id_hash || externalIdHash_(event.id, '');
    if (uid) (indexes.byUid[uid] = indexes.byUid[uid] || []).push(event);
    if (external) (indexes.byExternal[external] = indexes.byExternal[external] || []).push(event);
    const start = event.start && (event.start.dateTime || event.start.date) || '';
    const canonical = normalizeText_(event.summary) + '|' + String(start).slice(0, 10);
    (indexes.byCanonical[canonical] = indexes.byCanonical[canonical] || []).push(event);
  });
  return indexes;
}

function primaryDuplicateReviews_(incoming, primaryEvents) {
  const index = {};
  primaryEvents.forEach(function (event) {
    const start = event.start && (event.start.dateTime || event.start.date) || '';
    const key = normalizeText_(event.summary) + '|' + String(start).slice(0, 10);
    (index[key] = index[key] || []).push(event);
  });
  const reviews = [];
  incoming.forEach(function (event) {
    const key = normalizeText_(event.title) + '|' + String(event.start).slice(0, 10);
    if (index[key] && index[key].length) {
      reviews.push({uid: event.uid, title: event.title, reason: 'exact_title_and_date_in_primary', action: 'REVISÃO_MANUAL'});
    }
  });
  return reviews;
}
