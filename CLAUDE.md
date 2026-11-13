# co2-ar（そのCO₂のつけは、誰が払う？）— Claude Code 用の引き継ぎメモ

3大学データサイエンス・アイデアコンテスト2026（関西大学 チームパチョ）の提案アプリ。
スマホのARで、自分のCO₂（実物大の立方体）と将来の浸水を自分の部屋に重ねて体験する、1ページのWebアプリ。

## 公開と構成
- 公開URL：https://ajiki17.github.io/co2-ar/ （GitHub Pages、main ブランチの一番上の階層）
- **ファイルはすべて一番上の階層に置く**（フォルダなし）。index.html は 3Dモデルを `cube_day.glb` のように直接参照し、`data.json` も同じ階層から読む。
- 3Dモデルの参照には `?v=3` のような版番号を付けている。**.glb を作り直したら、index.html 内の版番号を上げる**（iPhoneのキャッシュ対策）。
- **実証のA群・B群は pilot.html（v1.23 の画面）で回答を集める。** index.html を `?g=A`／`?mode=text&g=B` で開くと pilot.html に切り替わる。通常のデモと審査員版は index.html（v1.24〜）。実証が終わるまで pilot.html の中身は変えない。
- 主な部品：index.html（画面・文言・three.js r128 の3D場面・model-viewer 3.5.0 のAR）、data.json（数値と出典）、*.glb（ARモデル95個）、Code.gs（Google Apps Script の控え）
- AR：iPhone は AR Quick Look（glb から USDZ を自動生成。アニメーション不可）、Android は WebXR / Scene Viewer。ar-scale="fixed"（実寸）。

## 守ること
- **数値はすべて数値台帳（チームの Excel）と一致させる。** 主な値：1日分 21.3kg（OWID 日本2024年 7.772t÷365）、体積 11.6m³・一辺2.26m、今の20歳が生まれた時点の世界の累積 64%、大阪の小中学生9年間の猛暑日 60歳50日・20歳160日・15歳225日。新しい数値には出典と閲覧日を画面下の出典欄に書く。
- **回答の保存先**：index.html の `const API=` に Apps Script のURL。保存する項目は ts, group, ageBand, region, pre, post, ipre, ipost, choices, chosen, sec, cpre, cpost, quiz（匿名）。項目を増やすときは Code.gs とスプレッドシートの列も、**列の最後に**足す。
- **実証（11/13〜15）中は体験の中身を変えない。** 11/12 に版を固定し、実証が終わるまでは不具合の修正だけにする。URL の `?g=A`／`?mode=text&g=B`（実証の群）と `?start=ar`（審査員用の近道）は動作を保つ。
- 内閣府調査（令和7年9月）と同じ設問（問6・問7、問2）の文言は変えない。
- 端末の「視差効果を減らす」設定（RM）では動きを止める。文字は16px以上。
- モデル1つは2MB以下、ページの初回表示は4G回線で5秒以内を目安にする。

## 作業の進め方
- 変更したら、PCのブラウザ（開発者ツールのモバイル表示）で全場面を通して確認してから push する。ARの見た目は iPhone の実機で確認してもらう。
- 変更内容は README.md の更新履歴に1行で書く。
- 背景資料：作業指示書（第6章 AR体験の実装作業書、受入基準 A1〜A12）、数値台帳。
