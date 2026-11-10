/** @OnlyCurrentDoc */
// このスクリプトが触れるのは、貼り付けたスプレッドシート1つだけ（上の1行で権限を限定）。
// Google Apps Script（スプレッドシートの「拡張機能 → Apps Script」に貼り、ウェブアプリとしてデプロイする）
// v1.18：保存するシートを group で分ける。空欄 → responses（通常のデモ）、A・B → pilot（実証）、J → judge（審査員）
//   1行目（見出し）：ts, group, ageBand, region, pre, post, ipre, ipost, choices, chosen, sec, cpre, cpost, quiz, idh, dup
//   初めて使うときは、エディタで setupSheets を1回実行すると、3枚のシートと見出しがそろう。
const SHEET_NAME = 'responses';                                   // 「みんなの結果」（doGet）はこのシートだけを集計する
const SHEET_OF = { '': 'responses', A: 'pilot', B: 'pilot', J: 'judge' };
const COLS = ['ts', 'group', 'ageBand', 'region', 'pre', 'post', 'ipre', 'ipost', 'choices', 'chosen', 'sec', 'cpre', 'cpost', 'quiz', 'idh', 'dup'];
const HEX64 = /^[0-9a-f]{64}$/;
const BOTH = '両群';

function doPost(e) {
  const d = JSON.parse(e.postData.contents);
  const small = (v) => v === undefined || v === null || v === '' || (Number.isInteger(v) && v >= 0 && v <= 10);   // 回答は0〜10の整数か空
  const group = d.group || '';
  if (!(Number.isInteger(d.ageBand) && d.ageBand >= 10 && d.ageBand <= 90) || !(group in SHEET_OF) ||
      !['pre', 'post', 'ipre', 'ipost', 'chosen', 'cpre', 'cpost', 'quiz'].every((k) => small(d[k]))) return out({ ok: false });   // 想定外の値は保存しない
  const idh = HEX64.test(String(d.idh || '').toLowerCase()) ? String(d.idh).toLowerCase() : '';   // 64文字の16進数でなければ空
  const vals = {};
  COLS.forEach((k) => { vals[k] = k === 'ts' ? new Date() : k === 'choices' ? (d.choices || []).join(',') : k === 'idh' ? idh : k === 'dup' ? '' : String(d[k] ?? '').slice(0, 20); });
  vals.group = group;
  const lock = LockService.getScriptLock();
  lock.waitLock(5000);
  try {
    const name = SHEET_OF[group], sh = sheetFor_(name), head = header_(sh);
    const row = () => head.map((h) => (h in vals ? vals[h] : ''));
    if (name === 'pilot' && idh) {
      // 同じ idh・同じ group → 新しい回答で上書き（ts も更新）。同じ idh で違う group → 新しい行を足し、その idh の行すべての dup を「両群」に
      const data = sh.getDataRange().getValues(), iI = head.indexOf('idh'), iG = head.indexOf('group'), iD = head.indexOf('dup');
      const mine = [];
      for (let r = 1; r < data.length; r++) if (String(data[r][iI]).toLowerCase() === idh) mine.push({ r: r + 1, g: String(data[r][iG]) });
      const same = mine.filter((m) => m.g === group), other = mine.some((m) => m.g !== group);
      if (other) vals.dup = BOTH;
      if (same.length) sh.getRange(same[same.length - 1].r, 1, 1, head.length).setValues([row()]);
      else sh.appendRow(row());
      if (other) mine.forEach((m) => sh.getRange(m.r, iD + 1).setValue(BOTH));
    } else {
      sh.appendRow(row());
    }
  } finally {
    lock.releaseLock();
  }
  return out({ ok: true });
}

function doGet() {   // 「みんなの結果」用の集計だけを返す（1人ずつの行は返さない）。今までどおり responses だけ
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

// エディタから1回実行：responses・pilot・judge の3枚と見出しをそろえる（既存の responses には idh・dup を右端に足すだけ）
function setupSheets() {
  ['responses', 'pilot', 'judge'].forEach((n) => sheetFor_(n));
}

// シートが無ければ作り、1行目に見出しを書く。見出しが足りなければ右端に足す（既存の列の順番は変えない）
function sheetFor_(name) {
  const ss = SpreadsheetApp.getActive();
  const sh = ss.getSheetByName(name) || ss.insertSheet(name);
  if (sh.getLastRow() === 0) sh.getRange(1, 1, 1, COLS.length).setValues([COLS]);
  else {
    const head = header_(sh);
    COLS.forEach((c) => { if (!head.includes(c)) { head.push(c); sh.getRange(1, head.length).setValue(c); } });
  }
  sh.getRange(1, header_(sh).indexOf('idh') + 1, sh.getMaxRows(), 1).setNumberFormat('@');   // idh は文字列のまま保存（数字に変換させない）
  return sh;
}

function header_(sh) {
  const n = sh.getLastColumn();
  return n ? sh.getRange(1, 1, 1, n).getValues()[0].map(String) : [];
}

const out = (o) => ContentService.createTextOutput(JSON.stringify(o)).setMimeType(ContentService.MimeType.JSON);
