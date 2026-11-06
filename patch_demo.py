"""デモ（demo_original.html）に、作業書 第6章の S1〜S8 の変更を当てて index.html を作る。"""
import re
h = open('demo_original.html', encoding='utf-8').read()
def rep(old, new, count=1):
    global h
    assert h.count(old) == count, (old[:60], h.count(old))
    h = h.replace(old, new)

# S1：ARモデルをファイルから読む＋Scene Viewerを有効にする
rep('ar-modes="webxr quick-look"', 'ar-modes="webxr scene-viewer quick-look"')
h, n = re.subn(r'const B64="[A-Za-z0-9+/=]+";', '', h); assert n == 1
rep("try{ const bin=Uint8Array.from(atob(B64),c=>c.charCodeAt(0)); const url=URL.createObjectURL(new Blob([bin],{type:'model/gltf-binary'})); mv.src=url; }catch(e){ msg.textContent='3Dモデルを用意できませんでした。'; return; }",
    "mv.setAttribute('src','models/cube_day.glb');")

# S3：期間ボタンに合わせてARのモデルも切り替える
rep("document.querySelectorAll('[data-span]').forEach(b=>b.addEventListener('click',()=>setSpan(b.dataset.span)));",
    "document.querySelectorAll('[data-span]').forEach(b=>b.addEventListener('click',()=>setSpan(b.dataset.span)));\n"
    "document.querySelectorAll('[data-span]').forEach(b=>b.addEventListener('click',()=>{ const sp=b.dataset.span, mvx=document.getElementById('mv'); if(!mvx) return;\n"
    "  const a=Math.min(99,Math.max(10,age)); mvx.setAttribute('src', sp==='life' ? `models/cube_life_${a}.glb` : `models/cube_${sp}.glb`);\n"
    "  const note=document.getElementById('arSpanNote'); if(note) note.textContent = sp==='day' ? '' : 'とても大きいので、ARは屋外の広い場所で試してください。室内では1日分がおすすめです。'; }));")
rep('<p id="arMsg"', '<p id="arSpanNote" style="font-size:.85rem;color:var(--sub);margin-top:8px"></p>\n    <p id="arMsg"')

# S4：体験3-2（生まれ年で変わる夏）を体験3のあとに足す
rep('<aside class="field" role="note" style="margin-top:40px"><b>この先について</b>',
    '''<section class="ch fade" id="s3b">
  <p class="kicker">体験3-2　生まれ年で変わる夏</p>
  <h2>生まれた年で、夏に外で遊べる日が変わる</h2>
  <p id="oppText">データを読み込み中です…</p>
  <div id="oppBars" class="oppbars" aria-hidden="true"></div>
  <p style="font-size:.8rem;color:var(--sub)">猛暑日＝最高気温35℃以上。日本スポーツ協会の熱中症予防運動指針では、気温35℃以上（暑さ指数31以上）は運動を原則中止とする目安です。データ：気象庁「大都市における猛暑日日数の長期変化傾向」（<span id="oppSt">大阪</span>の年別値。観測場所の移転前の年は使っていません）。</p>
</section>

<aside class="field" role="note" style="margin-top:40px"><b>この先について</b>''')

# S5：体験4の浸水AR
rep('<p id="wdText" style="margin-top:12px"></p>',
    '''<p id="wdText" style="margin-top:12px"></p>
  <div class="arbox">
    <model-viewer id="mvFlood" src="models/flood_050.glb" alt="床から0.5mまで水が来た部屋（実寸）" ar ar-modes="webxr scene-viewer quick-look" ar-scale="fixed" ar-placement="floor" camera-controls touch-action="pan-y" loading="lazy" shadow-intensity="0.4" style="width:100%;height:220px;background:var(--soft);border-radius:16px">
      <button slot="ar-button" class="btn" style="position:absolute;left:12px;bottom:12px">ARで、自分の部屋に水を入れる</button>
    </model-viewer>
    <p style="font-size:.85rem;color:var(--sub);margin-top:8px">床にカメラを向けると、選んだ高さまで水が来た状態が実寸で重なります。机やベッドの高さと比べてください。0.5mごとに色を変えた柱が目盛りです。</p>
  </div>''')
rep("document.querySelectorAll('[data-wd]').forEach(b=>b.addEventListener('click',()=>{wd=+b.dataset.wd;press('data-wd',b.dataset.wd);drawFuture();}));",
    "document.querySelectorAll('[data-wd]').forEach(b=>b.addEventListener('click',()=>{wd=+b.dataset.wd;press('data-wd',b.dataset.wd);drawFuture();}));\n"
    "document.querySelectorAll('[data-wd]').forEach(b=>b.addEventListener('click',()=>{ const cm=String(Math.round(Number(b.dataset.wd)*100)).padStart(3,'0'); const f=document.getElementById('mvFlood'); if(f) f.setAttribute('src',`models/flood_${cm}.glb`); }));")

# S6：保存と集計を Google Apps Script に置き換える
rep("let DB=null; (async()=>{ try{ if(window.claude&&claude.use) DB=await claude.use('db'); }catch(e){ DB=null; } })();",
    "const API=''; // ← Google Apps Script のウェブアプリURLを入れる（gas/Code.gs）。空のときは保存しない\nconst GROUP=(new URLSearchParams(location.search).get('g')||'').slice(0,2);")
i = h.index('async function saveAndAggregate'); j = h.index('// ---------- 地域 ----------')
h = h[:i] + r'''async function saveAndAggregate(chosenIdxs, chosenOne){
  const box=$('agg'); box.hidden=false; const sub='style="margin:6px 0 0;font-size:.88rem;color:var(--sub)"';
  if(!API){ box.innerHTML=`<b>みんなの結果</b><p ${sub}>このページでは、回答は保存されません。</p>`; return; }
  box.innerHTML=`<b>みんなの結果</b><p ${sub}>集計しています…</p>`;
  const doc={region:region||'', ageBand:Math.floor(age/10)*10, pre:ans.pre, post:ans.post, ipre:ans.ipre, ipost:ans.ipost, choices:chosenIdxs, chosen:chosenOne, sec:Math.round((performance.now()-t0)/1000), group:GROUP};
  let saved=true; try{ await fetch(API,{method:'POST',mode:'no-cors',body:JSON.stringify(doc)}); }catch(e){ saved=false; }   // 失敗しても体験は止めない
  let a=null; try{ a=await (await fetch(API)).json(); }catch(e){}
  if(!a){ box.innerHTML=`<b>みんなの結果</b><p ${sub}>集計を読み込めませんでした。</p>`; return; }
  box.innerHTML=`<b>みんなの結果（${a.n}人）</b>${saved?'':'<p style="font-size:.8rem;color:var(--sub);margin:4px 0">※あなたの回答は保存できませんでした</p>'}
   <div class="aggrow" style="margin-top:10px"><span></span><span style="font-size:.78rem;color:var(--sub)">体験前</span><span style="font-size:.78rem;color:var(--sub)">体験後</span>
   <span>自分も関わっていると思う</span><b>${pct(a.preInv,a.bothN)}</b><b>${pct(a.postInv,a.bothN)}</b>
   <span>IPCCの断定を知っている<br><small style="color:var(--sub)">全国 34.5%</small></span><b>${pct(a.preKnow,a.ibN)}</b><b>${pct(a.postKnow,a.ibN)}</b></div>
   <p style="margin:10px 0 0;font-size:.9rem">「対策に取り組む企業の商品やサービスを選びたい」を選んだ人：<b>${pct(a.sel0,a.n)}</b>　<span style="font-size:.8rem;color:var(--sub)">全国 36.8%（実践中＋今後）</span></p>
   <p style="margin:8px 0 0;font-size:.78rem;color:var(--sub)">「関わっていると思う」は「ややそう思う」「そう思う」の合計。前後の両方に答えた人で集計。</p>`;
}


''' + h[j:]

# 見た目の追加（体験3-2の棒、審査員向けの一言、B群用の表示）
rep('</style></head>', '''.oppbars{display:grid;gap:10px;margin:14px 0}
.oppbars .row{display:grid;grid-template-columns:7.5em 1fr;align-items:center;gap:10px;font-size:.9rem}
.oppbars .bar{height:22px;border-radius:6px;background:var(--line)}
.oppbars .bar.me{background:#1f5fbf}.oppbars .bar.young{background:#e8702a}
.judge-note{background:var(--soft);border-left:4px solid #e8702a;padding:10px 12px;border-radius:8px;font-size:.92rem}
body.text-mode .scene, body.text-mode model-viewer, body.text-mode .arbox{display:none!important}
</style></head>''')

# S2・S4・S7：データの読み込み、体験3-2の描画、実証用の切り替え、審査員用の近道
rep('</body>', r'''<script>
(function(){
  const qs=new URLSearchParams(location.search);
  if(qs.get('mode')==='text') document.body.classList.add('text-mode');            // 実証のB群用：3DとARを隠す
  let D=null;
  const nine=(by,series)=>{ let days=0,years=0; for(let y=by+6;y<=by+14;y++) if(series[y]!=null){days+=series[y];years++;} return {days,years}; };
  function drawOpportunity(){
    if(!D) return;
    const st=D.stationOfRegion[region]||D.defaultStation, series=D.hotDays[st], by=2026-age;
    const me=nine(by,series), young=nine(2011,series);
    const note=me.years<9?`（データのある${me.years}年分）`:'';
    const extra=[(D.regionNote||{})[region], (D.relocationNote||{})[st]?`${D.stationName[st]}は${D.relocationNote[st]}しており、前後の値は単純に比べられません。`:''].filter(Boolean).join('');
    document.getElementById('oppSt').textContent=D.stationName[st];
    const mine = me.years===0 ? `あなた（${by}年生まれ）が小中学生だったころの${D.stationName[st]}のデータは、観測場所の移転のため比べられません。` : `あなた（${by}年生まれ）が小中学生だった9年間に、${D.stationName[st]}で最高気温35℃以上だった日は<b>${me.days}日</b>${note}。`;
    document.getElementById('oppText').innerHTML=`${mine}今の15歳（2011年生まれ）は<b>${young.days}日</b>でした。外での運動が原則中止になる暑さの日数が、生まれた年でこれだけ違います。${extra?`<br><small style="color:var(--sub)">${extra}</small>`:''}`;
    const mx=Math.max(me.days,young.days,1);
    document.getElementById('oppBars').innerHTML=`<div class="row"><span>あなた（${by}年生まれ）</span><div class="bar me" style="width:${me.days/mx*100}%"></div></div><div class="row"><span>今の15歳</span><div class="bar young" style="width:${young.days/mx*100}%"></div></div>`;
  }
  fetch('data/data.json').then(r=>r.json()).then(d=>{D=d;drawOpportunity();}).catch(()=>{document.getElementById('oppText').textContent='データを読み込めませんでした。';});
  document.getElementById('age').addEventListener('input',drawOpportunity);
  document.getElementById('reg').addEventListener('change',drawOpportunity);
  document.getElementById('reg').addEventListener('change',()=>{ try{ drawFuture(); }catch(e){} });
  // 内閣府調査 問6・問7の選択肢（調査票の表記。12番だけ問6と問7で異なる）
  const OPT=['軽装や重ね着などにより、冷暖房の設定温度を適切に管理','こまめな消灯、家電のコンセントを抜くなどによる電気消費量の削減','冷蔵庫、エアコン、照明器具などの家電製品を購入する際に、省エネルギー効果の高い製品を購入','宅配便の1回での受取り、又は宅配ボックスでの受取りなどによる再配達の防止','部屋の温度を快適に保つ高断熱などの省エネ住宅への居住、又はリフォームの施工','太陽光発電のパネル設置による自家発電、又は自宅の電気プランを再生可能エネルギー利用のものに切替え','移動時に徒歩・自転車・公共交通機関の利用','電気自動車などのエコカーの選択や、ゆっくり加速・減速などのエコドライブの実践','地球温暖化への対策に取り組む企業の商品の購入やサービスの利用','地球温暖化への対策に取り組む団体・個人への応援・支援','その他'];
  const LIST={q6:[...OPT,'現在は取り組んでいない'], q7pre:[...OPT,'取り組みたいとは思わない'], q7post:[...OPT,'取り組みたいとは思わない']};
  document.querySelectorAll('[data-cq]').forEach(box=>{ const key=box.dataset.cq;
    box.innerHTML=LIST[key].map((t,i)=>`<label><input type="checkbox" value="${i+1}" data-k="${key}"><span>${i+1}．${t}</span></label>`).join(''); });
  const picked=k=>[...document.querySelectorAll(`input[data-k="${k}"]:checked`)].map(x=>+x.value);
  const sync=()=>{ const now=picked('q6').filter(v=>v<=10); ['q7pre','q7post'].forEach(k=>document.querySelectorAll(`input[data-k="${k}"]`).forEach(x=>{ const off=now.includes(+x.value); x.disabled=off; if(off) x.checked=false; x.parentElement.classList.toggle('off',off); })); };
  document.querySelectorAll('input[data-k="q6"]').forEach(x=>x.addEventListener('change',sync));
  // 企業の商品選択（選択肢9）：1＝現在実践、2＝今後取り組みたい、3＝どちらでもない（分析⑤の主な指標）
  window.KAKU=()=>{ const q6=picked('q6'); if(!q6.length && !picked('q7pre').length && !picked('q7post').length) return {};
    return { cpre: q6.includes(9)?1:(picked('q7pre').includes(9)?2:3), cpost: q6.includes(9)?1:(picked('q7post').includes(9)?2:3) }; };
  const CONTACT='', DELETE_DATE='';   // ← 問い合わせ先（メールアドレス）とデータ削除日が決まったら入れる
  document.getElementById('consent').textContent='この体験は、関西大学の学生チームがコンテストのために、アプリの効果を調べるものです。回答は匿名で、保存するのは年代・地域・質問への回答・選んだ選択肢・かかった時間だけです。名前やメールアドレスは保存しません。途中でやめても問題ありません。'+(DELETE_DATE?`データは${DELETE_DATE}に削除します。`:'')+(CONTACT?`問い合わせ：${CONTACT}`:'');
  if(qs.get('start')==='ar'){                                                        // 審査員用の近道
    const s1=document.getElementById('s1'), note=document.createElement('p');
    note.className='judge-note';
    note.textContent='審査員の方へ：下の「ARで自分の部屋に置く」で、日本人1人の1日分のCO₂（21.3kg、一辺約2.26m）を床に実物大で置けます。全体の体験は上から約10分です。';
    s1.prepend(note); s1.classList.add('in'); setTimeout(()=>s1.scrollIntoView(),300);
  }
})();
</script>
</body>''')

# 数値の照合（2026-11-05）：熱中症の数値を出典で確認できたものに置き換える
rep('<span>いま、熱中症で亡くなった人のうち65歳以上</span><b>87%</b><span>2020年</span>',
    '<span>熱中症で亡くなった人のうち65歳以上</span><b>85%</b><span>2024年（人口動態統計）</span>')
rep('<span>亡くなった場所が住居（家の中）</span><b>56.5%</b><span>2018年</span>',
    '<span>東京23区で熱中症で亡くなった人のうち屋内</span><b>約9割</b><span>2020年夏（東京都監察医務院）</span>')
rep('亡くなった場所の半数以上は家の中です。', '東京23区では、亡くなった人の約9割が屋内でした。')

# v0.9.2：熱帯夜・大雨は気象庁が公表する「20世紀末からの増加量」で表示（地域別。地域未選択は近畿）
rep("function drawFuture(){ const tn=sc===2?26.4:56.2, rain=sc===2?2.8:5.3; $('tnN').textContent=tn; $('rainN').textContent=rain;\n  [...cal.children].forEach((c,i)=>c.classList.toggle('on',i>=180&&i<180+Math.round(tn)));\n  $('rainLife').textContent=`同じ規模の大雨が、工業化以前の約${rain}倍起きやすくなります。あなたがこの先生きる年月（85歳までとして約${Math.max(0,85-age)}年）の間に、それだけ多く出会う可能性があります。`;",
    "function drawFuture(){ const RR=REG[region]||REG.kinki, rn=REG[region]?RR.n:'近畿地方', tn=sc===2?RR.tn[0]:RR.tn[1], rain=sc===2?RR.r30[0]:RR.r30[1];\n  $('tnN').textContent = tn==null ? '有意な変化なし' : `${tn}日増える`; $('rainN').textContent = rain==null ? '有意な変化なし' : `約${rain}倍になる`; $('futReg').textContent=`21世紀末・${rn}（気象庁）`;\n  [...cal.children].forEach((c,i)=>c.classList.toggle('on',i>=180&&i<180+Math.round(tn||0)));\n  $('rainLife').textContent = rain==null ? `${rn}では、この強さの雨の回数に有意な変化は予測されていません。` : `1時間に30mm以上の強い雨に出会う回数が、20世紀末の約${rain}倍になります。あなたがこの先生きる年月（85歳までとして約${Math.max(0,85-age)}年）の間に、それだけ多く出会う可能性があります。`;")
rep('<p><b>1年のうち、寝苦しい夜（熱帯夜）が <span id="tnN">26.4</span>日</b>　<span style="font-size:.8rem;color:var(--sub)">21世紀末・全国平均</span></p>',
    '<p><b>寝苦しい夜（熱帯夜）が、20世紀末より <span id="tnN">12日増える</span></b>　<span id="futReg" style="font-size:.8rem;color:var(--sub)">21世紀末・近畿地方（気象庁）</span></p>')
rep('<p><b>100年に1回だった大雨が、100年に <span id="rainN">2.8</span>回</b></p>',
    '<p><b>1時間に30mm以上の強い雨が、20世紀末の <span id="rainN">約1.3倍になる</span></b></p>')
rep('熱帯夜が26日で済むか56日になるかの差を生むのは、一人ひとりの選択の積み重ねです。',
    '2℃と4℃では、熱帯夜の増え方が数倍ちがいます。その差を生むのは、一人ひとりの選択の積み重ねです。')

# v0.9.2：冒頭の説明文（問い合わせ先と削除日は未定のため空欄。決まったら CONTACT・DELETE_DATE に入れる）
rep('<p class="note">デモ版：3Dの場面は、実装ではスマホのカメラ越しに実際の部屋へ重ねるARで表示します。</p>',
    '<p class="note">3Dの場面のうち2つ（体験1の立方体、体験4の浸水）は、スマホのカメラ越しに自分の部屋へ重ねるARで見られます。</p>')
rep('<h2>はじめに、3つだけ教えてください</h2>',
    '<h2>はじめに、3つだけ教えてください</h2>\n  <p id="consent" style="font-size:.85rem;color:var(--sub)"></p>')

# v0.9.3：内閣府調査（令和7年9月）の問6・問7と同じ設問で、企業の商品選択の事前・事後を測る（cpre・cpost）
Q6Q7_PRE = """<div class="field"><span class="q">「脱炭素社会」の実現に向け、あなたが日常生活の中で、現在、取り組んでいることは何かありますか。（○はいくつでも）</span><div class="checks" data-cq="q6"></div></div>
  <div class="field"><span class="q">「脱炭素社会」の実現に向け、あなたが日常生活の中で、今後、新たに取り組んでみたいと思うことはありますか。（○はいくつでも。ただし、選択肢1～10のうち上の質問で回答したものと同じ取組は選択できません。）</span><div class="checks" data-cq="q7pre"></div></div>"""
rep('data-q="ipre"></div></div>', 'data-q="ipre"></div></div>\n  ' + Q6Q7_PRE)
rep('<p style="font-size:.8rem;color:var(--sub)">回答は、体験の効果を確かめるために匿名で集計します。',
    '<div class="field"><span class="q">体験を終えて、あらためて。「脱炭素社会」の実現に向け、あなたが日常生活の中で、今後、新たに取り組んでみたいと思うことはありますか。（○はいくつでも。ただし、選択肢1～10のうち最初の質問で「現在、取り組んでいる」と回答したものと同じ取組は選択できません。）</span><div class="checks" data-cq="q7post"></div></div>\n  <p style="font-size:.8rem;color:var(--sub)">回答は、体験の効果を確かめるために匿名で集計します。')
rep("const doc={region:region||'', ageBand:Math.floor(age/10)*10, pre:ans.pre, post:ans.post, ipre:ans.ipre, ipost:ans.ipost, choices:chosenIdxs, chosen:chosenOne, sec:Math.round((performance.now()-t0)/1000), group:GROUP};",
    "const K=window.KAKU?window.KAKU():{}; const doc={region:region||'', ageBand:Math.floor(age/10)*10, pre:ans.pre, post:ans.post, ipre:ans.ipre, ipost:ans.ipost, choices:chosenIdxs, chosen:chosenOne, sec:Math.round((performance.now()-t0)/1000), group:GROUP, cpre:K.cpre, cpost:K.cpost};")
rep('.judge-note{', '.checks{display:grid;gap:6px;margin-top:8px}.checks label{display:flex;gap:8px;align-items:flex-start;font-size:.9rem;line-height:1.5}.checks input{margin-top:5px}.checks label.off{opacity:.4}\n.judge-note{')
open('index.html', 'w', encoding='utf-8').write(h)
print('index.html', len(h))
