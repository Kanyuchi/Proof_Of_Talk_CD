/**
 * POT26 Supabase → Sheet sync.
 * Writes Supabase `attendees` into a dedicated `POT Attendees` tab.
 * Safe alongside mergeInvestorTabs() — never touches MERGED.
 *
 * Install:
 *   1. Extensions → Apps Script → add this as a new script file
 *   2. Project Settings → Script Properties:
 *        SUPABASE_URL       = https://<project>.supabase.co
 *        SUPABASE_ANON_KEY  = <read-only anon key, scoped to attendees_sync view>
 *   3. Run syncFromSupabase() once to verify, then add an hourly trigger
 *      (Triggers → + Add Trigger → syncFromSupabase, Time-driven, Hour timer)
 *
 * Supabase prep (one-time):
 *   create or replace view public.attendees_sync as
 *   select email, name, company, created_at, ticket_type, ticket_bought_at
 *   from public.attendees;
 *   grant select on public.attendees_sync to anon;
 */

const POT_TAB   = 'POT Attendees';
const LOG_TAB   = 'POT Sync Log';
const PAGE_SIZE = 1000;
const HEADERS   = ['Email', 'Name', 'Company', 'Signed Up At', 'Ticket Type', 'Ticket Bought At'];

function syncFromSupabase() {
  const props = PropertiesService.getScriptProperties();
  const url = props.getProperty('SUPABASE_URL');
  const key = props.getProperty('SUPABASE_ANON_KEY');
  if (!url || !key) throw new Error('Missing SUPABASE_URL or SUPABASE_ANON_KEY in Script Properties');

  const rows = fetchAll(url, key);
  const ss = SpreadsheetApp.getActive();
  let sheet = ss.getSheetByName(POT_TAB);
  if (!sheet) sheet = ss.insertSheet(POT_TAB);

  sheet.clear();
  sheet.getRange(1, 1, 1, HEADERS.length).setValues([HEADERS]).setFontWeight('bold');
  sheet.setFrozenRows(1);

  if (rows.length === 0) { writeLog(ss, 0, 'no rows'); return; }

  const out = rows.map(r => [
    (r.email || '').toLowerCase().trim(),
    r.name || '',
    r.company || '',
    r.created_at || '',
    r.ticket_type || '',
    r.ticket_bought_at || '',
  ]);
  sheet.getRange(2, 1, out.length, HEADERS.length).setValues(out);

  writeLog(ss, rows.length, 'ok');
}

function fetchAll(url, key) {
  const all = [];
  let offset = 0;
  while (true) {
    const endpoint = `${url}/rest/v1/attendees_sync`
      + `?select=email,name,company,created_at,ticket_type,ticket_bought_at`
      + `&order=created_at.asc&limit=${PAGE_SIZE}&offset=${offset}`;
    const res = UrlFetchApp.fetch(endpoint, {
      headers: { apikey: key, Authorization: `Bearer ${key}` },
      muteHttpExceptions: true,
    });
    if (res.getResponseCode() >= 300) {
      throw new Error(`Supabase ${res.getResponseCode()}: ${res.getContentText()}`);
    }
    const batch = JSON.parse(res.getContentText());
    all.push(...batch);
    if (batch.length < PAGE_SIZE) break;
    offset += PAGE_SIZE;
  }
  return all;
}

function writeLog(ss, count, note) {
  let log = ss.getSheetByName(LOG_TAB);
  if (!log) {
    log = ss.insertSheet(LOG_TAB);
    log.appendRow(['Timestamp', 'Rows synced', 'Note']);
    log.setFrozenRows(1);
  }
  log.appendRow([new Date(), count, note]);
}

function installTrigger() {
  ScriptApp.getProjectTriggers()
    .filter(t => t.getHandlerFunction() === 'syncFromSupabase')
    .forEach(t => ScriptApp.deleteTrigger(t));
  ScriptApp.newTrigger('syncFromSupabase').timeBased().everyHours(1).create();
}
