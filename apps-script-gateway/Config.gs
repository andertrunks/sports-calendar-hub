const SCH_SCHEMA_VERSION = '2.0';
const SCH_MANAGED_BY = 'sports-calendar-hub';
const SCH_CALENDAR_NAME = 'Eventos esportivos';
const SCH_MAX_REQUEST_BYTES = 1900000;
const SCH_COLOR_IDS = {
  'sao-paulo': '11', 'selecao-brasileira': '5', 'clubes-regionais': '10',
  'red-bull': '6', 'premier-league': '1', 'continentais': '9',
  'automobilismo': '3', 'brasileirao': '7', 'olimpiadas-pan': '4',
  'copas-do-mundo': '2', 'outros-esportes': '8'
};

function config_() {
  const p = PropertiesService.getScriptProperties().getProperties();
  const required = ['SPREADSHEET_ID', 'SHEET_NAME', 'SPORTS_CALENDAR_ID', 'TIMEZONE',
    'EXPORT_TOKEN', 'SYNC_TOKEN', 'SCHEMA_VERSION', 'ALLOW_PRIMARY_DUPLICATE_CLEANUP',
    'DRY_RUN_DEFAULT'];
  const missing = required.filter(function (key) { return !p[key]; });
  if (missing.length) throw new Error('missing_script_properties:' + missing.join(','));
  if (p.SCHEMA_VERSION !== SCH_SCHEMA_VERSION) throw new Error('invalid_schema_property');
  if (p.EXPORT_TOKEN === p.SYNC_TOKEN || p.EXPORT_TOKEN.length < 48 || p.SYNC_TOKEN.length < 48) {
    throw new Error('invalid_tokens');
  }
  return p;
}
