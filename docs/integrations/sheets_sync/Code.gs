/**
 * POT26 Supabase → Sheet sync.
 *
 * Two jobs, one hourly trigger (`syncAll`):
 *   1. syncPotAttendees — consolidates `attendees` + `nominations` from Supabase
 *                         into a single `POT Attendees` tab (the source of truth)
 *   2. addFunnelFormulas — adds an `In Funnel` ARRAYFORMULA column to every
 *                          outreach tab + green conditional formatting on TRUE
 *
 * The formulas auto-flag new rows instantly — no wait for the hourly sync.
 * The script only needs to keep `POT Attendees` fresh.
 *
 * Install:
 *   1. Extensions → Apps Script → paste this file
 *   2. Project Settings → Script Properties:
 *        SUPABASE_URL       = https://<project>.supabase.co
 *        SUPABASE_ANON_KEY  = <read-only anon key>
 *   3. Run syncAll() once to verify
 *   4. Triggers → + Add Trigger → syncAll, Time-driven, Hour timer
 */

const POT_TAB       = 'POT Attendees';
const LOG_TAB       = 'POT Sync Log';
const EMAIL_HEADER  = 'Contact Email';
const FUNNEL_HEADER = 'In Funnel';
const PAGE_SIZE     = 1000;

const SKIP_TABS = new Set([
  'Dashboard', 'POT Attendees', 'POT Nominees', 'POT Sync Log',
  'MERGED - All Investors',
  'EXCLUDE - Speakers', 'EXCLUDE - Priority VIP', 'NEW'
]);

const POT_HEADERS = ['Email', 'Name', 'Company', 'Title', 'Category', 'Source', 'Signed Up At', 'Ticket Type', 'Confirmed'];

// ── Master sync (point the hourly trigger here) ─────────────────────────────

function syncAll() {
  var props = PropertiesService.getScriptProperties();
  var url = props.getProperty('SUPABASE_URL');
  var key = props.getProperty('SUPABASE_ANON_KEY');
  if (!url || !key) throw new Error('Missing SUPABASE_URL or SUPABASE_ANON_KEY in Script Properties');

  var ss = SpreadsheetApp.getActive();

  var counts = syncPotAttendees(ss, url, key);
  addFunnelFormulas(ss);

  writeLog(ss, counts.attendees, counts.nominees, 'ok');
}

// ── Consolidated POT Attendees sync ─────────────────────────────────────────

function syncPotAttendees(ss, url, key) {
  var attendees = fetchAll(url, key, 'attendees_sync',
    'email,name,company,title,created_at,ticket_type,ticket_bought_at,category');
  var nominees = fetchAll(url, key, 'nominations_sync',
    'nominee_email,nominee_name,nominee_company,nominee_title,nominee_vertical,nominee_seniority,nominator_name,nominator_email,status,nominee_confirmed,created_at');

  var sheet = ss.getSheetByName(POT_TAB);
  if (!sheet) sheet = ss.insertSheet(POT_TAB);

  sheet.clear();
  sheet.getRange(1, 1, 1, POT_HEADERS.length).setValues([POT_HEADERS]).setFontWeight('bold');
  sheet.setFrozenRows(1);

  var out = [];

  for (var i = 0; i < attendees.length; i++) {
    var r = attendees[i];
    out.push([
      (r.email || '').toLowerCase().trim(),
      r.name || '',
      r.company || '',
      r.title || '',
      r.category || '',
      'TICKET',
      r.created_at || '',
      r.ticket_type || '',
      'YES',
    ]);
  }

  for (var j = 0; j < nominees.length; j++) {
    var n = nominees[j];
    var email = (n.nominee_email || '').toLowerCase().trim();
    out.push([
      email,
      n.nominee_name || '',
      n.nominee_company || '',
      n.nominee_title || (n.nominee_seniority || ''),
      n.nominee_vertical || '',
      'NOMINEE',
      n.created_at || '',
      '',
      n.nominee_confirmed ? 'YES' : '',
    ]);
  }

  if (out.length > 0) {
    sheet.getRange(2, 1, out.length, POT_HEADERS.length).setValues(out);
  }

  return { attendees: attendees.length, nominees: nominees.length };
}

// ── Funnel formulas on all outreach tabs ─────────────────────────────────────

function addFunnelFormulas(ss) {
  var sheets = ss.getSheets();
  for (var s = 0; s < sheets.length; s++) {
    var sheet = sheets[s];
    var name = sheet.getName();
    if (SKIP_TABS.has(name)) continue;
    if (sheet.getLastRow() < 2) continue;

    var header = sheet.getRange(1, 1, 1, sheet.getLastColumn()).getValues()[0];
    var emailIdx = header.indexOf(EMAIL_HEADER);
    if (emailIdx === -1) continue;

    // Find or create the In Funnel column
    var funnelIdx = header.indexOf(FUNNEL_HEADER);
    var funnelCol;
    if (funnelIdx === -1) {
      funnelCol = sheet.getLastColumn() + 1;
      sheet.getRange(1, funnelCol).setValue(FUNNEL_HEADER).setFontWeight('bold');
    } else {
      funnelCol = funnelIdx + 1;
    }

    // Clear old static values so the ARRAYFORMULA can expand
    sheet.getRange(2, funnelCol, sheet.getMaxRows() - 1, 1).clearContent();

    // Build the ARRAYFORMULA — references the email column by letter
    var emailColLetter = columnToLetter(emailIdx + 1);
    var formula = '=ARRAYFORMULA(IF(' + emailColLetter + '2:' + emailColLetter
      + '="","",IF(COUNTIF(\'' + POT_TAB + '\'!A:A,' + emailColLetter + '2:' + emailColLetter + ')>0,TRUE,FALSE)))';

    sheet.getRange(2, funnelCol).setFormula(formula);

    // Add green conditional formatting on TRUE (idempotent — clears old rules for this range first)
    var range = sheet.getRange(2, funnelCol, sheet.getMaxRows() - 1, 1);
    var rules = sheet.getConditionalFormatRules();
    var newRules = [];
    for (var r = 0; r < rules.length; r++) {
      var ruleRanges = rules[r].getRanges();
      var overlaps = false;
      for (var rr = 0; rr < ruleRanges.length; rr++) {
        if (ruleRanges[rr].getColumn() === funnelCol) { overlaps = true; break; }
      }
      if (!overlaps) newRules.push(rules[r]);
    }
    var greenRule = SpreadsheetApp.newConditionalFormatRule()
      .whenTextEqualTo('TRUE')
      .setBackground('#b7e1cd')
      .setRanges([range])
      .build();
    newRules.push(greenRule);
    sheet.setConditionalFormatRules(newRules);
  }
}

function columnToLetter(col) {
  var letter = '';
  while (col > 0) {
    var mod = (col - 1) % 26;
    letter = String.fromCharCode(65 + mod) + letter;
    col = Math.floor((col - 1) / 26);
  }
  return letter;
}

// ── Shared fetch ────────────────────────────────────────────────────────────

function fetchAll(url, key, view, select) {
  var all = [];
  var offset = 0;
  while (true) {
    var endpoint = url + '/rest/v1/' + view
      + '?select=' + select
      + '&order=created_at.asc&limit=' + PAGE_SIZE + '&offset=' + offset;
    var res = UrlFetchApp.fetch(endpoint, {
      headers: { apikey: key, Authorization: 'Bearer ' + key },
      muteHttpExceptions: true,
    });
    if (res.getResponseCode() >= 300) {
      throw new Error('Supabase ' + res.getResponseCode() + ' on ' + view + ': ' + res.getContentText());
    }
    var batch = JSON.parse(res.getContentText());
    for (var i = 0; i < batch.length; i++) all.push(batch[i]);
    if (batch.length < PAGE_SIZE) break;
    offset += PAGE_SIZE;
  }
  return all;
}

// ── Logging ─────────────────────────────────────────────────────────────────

function writeLog(ss, attCount, nomCount, note) {
  var log = ss.getSheetByName(LOG_TAB);
  if (!log) {
    log = ss.insertSheet(LOG_TAB);
    log.appendRow(['Timestamp', 'Attendees synced', 'Nominees synced', 'Note']);
    log.setFrozenRows(1);
  }
  log.appendRow([new Date(), attCount, nomCount, note]);
}

// ── Trigger installer ───────────────────────────────────────────────────────

function installTrigger() {
  var triggers = ScriptApp.getProjectTriggers();
  for (var i = 0; i < triggers.length; i++) {
    var fn = triggers[i].getHandlerFunction();
    if (fn === 'syncAll' || fn === 'syncFromSupabase') {
      ScriptApp.deleteTrigger(triggers[i]);
    }
  }
  ScriptApp.newTrigger('syncAll').timeBased().atHour(23).everyDays(1).create();
}
