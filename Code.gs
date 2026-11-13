/** @OnlyCurrentDoc */
// このスクリプトが触れるのは、貼り付けたスプレッドシート1つだけ（上の1行で権限を限定）。
// Google Apps Script（スプレッドシートの「拡張機能 → Apps Script」に貼り、ウェブアプリとしてデプロイする）
// v1.18：保存するシートを group で分ける。空欄 → responses（通常のデモ）、A・B → pilot（実証）、J → judge（審査員）
//   1行目（見出し）：ts, group, ageBand, region, pre, post, ipre, ipost, choices, chosen, sec, cpre, cpost, quiz, idh, dup
//   初めて使うときは、エディタで setupSheets を1回実行すると、3枚のシートと見出しがそろう。
// v1.24：setupSheets で、1行目の固定・列名の説明（メモ）・「見方」シート・「集計」シート（pilot から数式で自動集計）も作る
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
// v1.24：1行目を固定し、列名のセルに日本語の説明（メモ）を付ける。「見方」と「集計」のシートも作り直す（1行目の列名と列の順番は変えない）
function setupSheets() {
  ['responses', 'pilot', 'judge'].forEach((n) => {
    const sh = sheetFor_(n), head = header_(sh);
    sh.setFrozenRows(1);
    head.forEach((h, i) => { if (h in NOTES) sh.getRange(1, i + 1).setNote(NOTES[h][0] + '\n' + NOTES[h][1]); });
  });
  guideSheet_();
  summarySheet_();
}

// 列名ごとの説明：[意味, 値の読み方]
const LIK5 = '1まったく思わない・2あまり思わない・3どちらともいえない・4ややそう思う・5そう思う（空欄＝未回答）';
const KAKU3 = '1現在、取り組んでいる・2今は取り組んでいないが、今後取り組んでみたい・3どちらでもない（空欄＝未回答）';
const NOTES = {
  ts: ['送信した日時', 'サーバーが受け取った日時。pilot で同じ人・同じ群が回答し直したときは、最新の日時に更新'],
  group: ['群（どの形で体験したか）', '空欄＝通常のデモ、A＝実証のA群（3D・AR、?g=A）、B＝実証のB群（文章のみ、?mode=text&g=B）、J＝審査員版'],
  ageBand: ['年代', '10歳きざみ（例：20＝20〜29歳）'],
  region: ['住んでいる地域（任意）', '空欄＝選ばなかった。hokkaido 北海道・tohoku 東北・kanto 関東甲信・hokuriku 北陸・tokai 東海・kinki 近畿・chugoku 中国・shikoku 四国・kyushu_n 九州北部・kyushu_s 九州南部・amami 奄美・okinawa 沖縄'],
  pre: ['体験の前「日々の生活で、自分もCO₂の排出に関わっていると思う」', LIK5],
  post: ['体験のあと「自分も関わっていると思う」（pre と同じ質問）', LIK5],
  ipre: ['（v1.23まで）体験の前：IPCCの断定を知っているか', '1知っている・2知らない。v1.24で質問を外したので、これからは空欄'],
  ipost: ['（v1.23まで）体験のあと：IPCCの断定を知っているか', '1知っている・2知らない。v1.24で質問を外したので、これからは空欄'],
  choices: ['体験のあとで「やってみたい」と選んだ行動（いくつでも）', '番号をカンマ区切り：0企業の商品やサービスを選ぶ・1電気を再エネのプランに・2公共交通や自転車・3長く使える物を選ぶ'],
  chosen: ['その中から「まず1つ」決めた行動', '0〜3（番号は choices と同じ。空欄＝決めていない）'],
  sec: ['かかった秒数', 'ページを開いてから「宣言カードをつくる（アンケートの回答を送信）」を押すまでの秒数'],
  cpre: ['体験の前：企業の商品選択（地球温暖化への対策に取り組む企業の商品の購入やサービスの利用）', KAKU3 + '。v1.23までは問6・問7の選択肢9から計算した値'],
  cpost: ['体験のあと：企業の商品選択（cpre と同じ質問）', KAKU3 + '。v1.23までは問6・問7の選択肢9から計算した値'],
  quiz: ['理解度クイズの正答数', '0〜3（空欄＝1問も答えていない）'],
  idh: ['メールアドレスを変換した文字列', 'SHA-256 で変換した64文字。元のアドレスには戻せない。同じ人の回答を見分けるためだけに使う（実証の pilot のみ）'],
  dup: ['両群に回答した印', '両群＝同じ idh で A群とB群の両方に回答した（その idh の行すべてに付く）。分析では除く'],
};

// 「見方」シート：列名・意味・値の読み方の表と、各シートの役割
function guideSheet_() {
  const sh = sheetOf_('見方');
  const rows = [['列', '列名', '意味', '値の読み方']];
  COLS.forEach((c, i) => rows.push([colA_(i + 1), c, NOTES[c][0], NOTES[c][1]]));
  rows.push(['', '', '', '']);
  rows.push(['シート', '役割', '', '']);
  [['responses', '通常のデモ（URLに ?g= を付けないとき）。「みんなの結果」はこのシートだけを集計する'],
   ['pilot', '実証（11/13〜15）のA群（?g=A）とB群（?mode=text&g=B）。同じ idh・同じ群は最新の回答で上書き'],
   ['judge', '審査員版（?mode=judge・?start=ar）'],
   ['集計', 'pilot から数式で自動集計（A群・B群）。setupSheets を実行すると作り直す'],
   ['見方', 'この表']].forEach((r) => rows.push([r[0], r[1], '', '']));
  sh.getRange(1, 1, rows.length, 4).setValues(rows);
  sh.getRange(1, 1, 1, 4).setFontWeight('bold');
  sh.getRange(COLS.length + 3, 1, 1, 2).setFontWeight('bold');
  sh.setFrozenRows(1);
  sh.setColumnWidth(3, 320); sh.setColumnWidth(4, 520);
  sh.getRange(1, 1, rows.length, 4).setWrap(true).setVerticalAlignment('top');
}

// 「集計」シート：pilot から数式で自動集計（行が増えても、そのまま再計算される）
function summarySheet_() {
  const p = header_(sheetFor_('pilot'));
  const c = (name) => { const L = colA_(p.indexOf(name) + 1); return 'pilot!$' + L + '$2:$' + L; };
  const G = c('group'), g = (x) => G + ',"' + x + '"';
  const ratio = (col, cond) => (x) => '=IFERROR((' + cond.map((k) => 'COUNTIFS(' + g(x) + ',' + c(col) + ',"' + k + '")').join('+') + ')/COUNTIFS(' + g(x) + ',' + c(col) + ',"<>"),"")';
  const ROWS = [
    ['人数', (x) => '=COUNTIF(' + G + ',"' + x + '")', '0', 'その群の行の数'],
    ['かかった時間の平均（分）', (x) => '=IFERROR(AVERAGEIFS(' + c('sec') + ',' + g(x) + ')/60,"")', '0.0', 'sec の平均÷60'],
    ['「関わっていると思う」の割合（体験の前）', ratio('pre', ['>=4']), '0.0%', 'pre が4以上の人÷pre に答えた人'],
    ['「関わっていると思う」の割合（体験のあと）', ratio('post', ['>=4']), '0.0%', 'post が4以上の人÷post に答えた人'],
    ['企業の商品選択「取り組んでいる・今後取り組みたい」の割合（体験の前）', ratio('cpre', ['1', '2']), '0.0%', 'cpre が1か2の人÷cpre に答えた人'],
    ['企業の商品選択「取り組んでいる・今後取り組みたい」の割合（体験のあと）', ratio('cpost', ['1', '2']), '0.0%', 'cpost が1か2の人÷cpost に答えた人'],
    ['クイズの平均点（3点満点）', (x) => '=IFERROR(AVERAGEIFS(' + c('quiz') + ',' + g(x) + ',' + c('quiz') + ',"<>"),"")', '0.00', 'quiz に答えた人の平均'],
    ['dup（両群）が付いた行の数', (x) => '=COUNTIFS(' + g(x) + ',' + c('dup') + ',"' + BOTH + '")', '0', '同じ人が両群に回答した行。分析では除く'],
  ];
  const sh = sheetOf_('集計');
  sh.getRange(1, 1, 1, 4).setValues([['項目', 'A群', 'B群', '計算のしかた']]).setFontWeight('bold');
  ROWS.forEach((r, i) => {
    sh.getRange(i + 2, 1).setValue(r[0]);
    sh.getRange(i + 2, 2, 1, 2).setFormulas([[r[1]('A'), r[1]('B')]]).setNumberFormat(r[2]);
    sh.getRange(i + 2, 4).setValue(r[3]);
  });
  sh.getRange(ROWS.length + 3, 1).setValue('pilot シートから自動で計算しています（回答が増えると更新）。割合の分母は、その質問に答えた人です。');
  sh.setFrozenRows(1);
  sh.setColumnWidth(1, 420); sh.setColumnWidth(4, 320);
}

// 名前のシートを（無ければ作って）中身を消して返す。「見方」「集計」用
function sheetOf_(name) {
  const ss = SpreadsheetApp.getActive();
  const sh = ss.getSheetByName(name) || ss.insertSheet(name);
  sh.clear();
  return sh;
}

// 列番号 → 列の文字（1→A、27→AA）
function colA_(n) {
  let s = '';
  for (; n > 0; n = Math.floor((n - 1) / 26)) s = String.fromCharCode(65 + ((n - 1) % 26)) + s;
  return s;
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
