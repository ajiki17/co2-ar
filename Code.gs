/** @OnlyCurrentDoc */
// このスクリプトが触れるのは、貼り付けたスプレッドシート1つだけ（上の1行で権限を限定）。
// Google Apps Script（スプレッドシートの「拡張機能 → Apps Script」に貼り、ウェブアプリとしてデプロイする）
// シート名 responses、1行目：ts, group, ageBand, region, pre, post, ipre, ipost, choices, chosen, sec, cpre, cpost, quiz
const SHEET_NAME = 'responses';
const COLS = ['ts', 'group', 'ageBand', 'region', 'pre', 'post', 'ipre', 'ipost', 'choices', 'chosen', 'sec', 'cpre', 'cpost', 'quiz'];

function doPost(e) {
  const d = JSON.parse(e.postData.contents);
  const small = (v) => v === undefined || v === null || v === '' || (Number.isInteger(v) && v >= 0 && v <= 10);   // 回答は0〜10の整数か空
  const okGroup = ['', 'A', 'B'].includes(d.group || '');
  if (!(Number.isInteger(d.ageBand) && d.ageBand >= 10 && d.ageBand <= 90) || !okGroup ||
      !['pre', 'post', 'ipre', 'ipost', 'chosen', 'cpre', 'cpost', 'quiz'].every((k) => small(d[k]))) return out({ ok: false });   // 想定外の値は保存しない
  const lock = LockService.getScriptLock();
  lock.waitLock(5000);
  try {
    SpreadsheetApp.getActive().getSheetByName(SHEET_NAME).appendRow(
      COLS.map((k) => (k === 'ts' ? new Date() : k === 'choices' ? (d.choices || []).join(',') : String(d[k] ?? '').slice(0, 20))));
  } finally {
    lock.releaseLock();
  }
  return out({ ok: true });
}

function doGet() {   // 「みんなの結果」用の集計だけを返す（1人ずつの行は返さない）
  const rows = SpreadsheetApp.getActive().getSheetByName(SHEET_NAME).getDataRange().getValues().slice(1);
  const num = (v) => (v === '' ? null : Number(v));
  const both = rows.filter((r) => num(r[4]) && num(r[5])), ib = rows.filter((r) => num(r[6]) && num(r[7]));
  const cnt = (a, f) => a.filter(f).length;
  return out({
    n: rows.length,
    bothN: both.length, preInv: cnt(both, (r) => num(r[4]) >= 4), postInv: cnt(both, (r) => num(r[5]) >= 4),
    ibN: ib.length, preKnow: cnt(ib, (r) => num(r[6]) === 1), postKnow: cnt(ib, (r) => num(r[7]) === 1),
    sel0: cnt(rows, (r) => String(r[8]).split(',').includes('0')),
    up: cnt(both, (r) => num(r[5]) > num(r[4])),
  });
}

const out = (o) => ContentService.createTextOutput(JSON.stringify(o)).setMimeType(ContentService.MimeType.JSON);
