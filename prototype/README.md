# camagru prototype

最低限の課題要件を満たす、動く完成版。Python 標準ライブラリだけ・SQLite・Mailpit。

## 起動

```
cp .env.example .env     # 初回だけ
make up
```

- サイト: http://localhost:8001
- 受信メール(Mailpit): http://localhost:8026
- 止める: `make down` / ログ: `make logs` / テスト: `make test`

## 設計の割り切り(本編 SPEC との違い)

- **画像は PNG のみ。** JPEG のデコーダーは書かない。
  ブラウザ側で canvas に描いて PNG に変換してから送る(カメラもアップロードも同じ経路)。
  サーバーは PNG を自作デコーダー(`app/png.py`)で読み、検査・合成・再エンコードする。
- 合成はサーバー側(`png.composite`)。ブラウザは重ね合わせのプレビューだけ。
- セッションは DB に保存(Cookie にはランダムな ID だけ)。
- 本番用サーバーは使わない(`wsgiref` のマルチスレッド版)。

## 構成

```
app/main.py      サーバー起動(ログ出力を消した wsgiref)
app/web.py       Request/Response、ルーター、セッション、CSRF、ヘッダー、静的ファイル
app/handlers.py  各画面の処理
app/views.py     HTML 生成(すべて html.escape)
app/png.py       PNG の読み書きと合成
app/db.py        スキーマと接続(SQL は全部プリペアドステートメント)
app/security.py  scrypt、トークン、入力チェック
app/mailer.py    smtplib
public/          CSS・JS・飾り画像(tools/make_overlays.py で生成)
```

## 課題要件との対応

| 要件 | 場所 |
|---|---|
| 登録・メール確認・ログイン/ログアウト・再設定・設定変更 | handlers.py |
| ギャラリー(公開・ページ分け 6 件)・いいね・コメント・通知メール | handlers.py |
| 編集ページ(カメラ・飾り選択・撮影・サムネイル・削除・アップロード) | handlers.py, public/editor.js |
| パスワード: scrypt + 塩 | security.py |
| XSS: 全出力をエスケープ + CSP | views.py, web.py |
| CSRF: セッション紐づけトークンを全 POST で検証 | web.py |
| SQL インジェクション: プレースホルダのみ | 全体 |
| 不要なファイル: PNG として完全に読めたものだけ受理し、再エンコードして保存。名前はランダム | handlers.py, png.py |
| メールのトークン: ハッシュだけ保存・期限・1 回限り | handlers.py |
| ログイン連続失敗で 5 分ロック | handlers.py |
| コンソールに出力なし | main.py(アクセスログ無効) |
