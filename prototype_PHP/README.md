# camagru prototype (PHP)

最低限の課題要件を満たす、動く完成版。PHP 8.3(標準機能のみ)+ Apache + SQLite + Mailpit。
`../prototype`(Python 版)と同じ機能を、PHP の標準機能で書き直したもの。

## 起動

```
cp .env.example .env     # 初回だけ
make up
```

- サイト: http://localhost:8002
- 受信メール(Mailpit): http://localhost:8027
- 止める: `make down` / ログ: `make logs`

## 構成

```
public/          Apache の DocumentRoot(外から見えるのはここだけ)
  index.php        ギャラリー(ページ分け)
  register / verify / login / logout / forgot / reset / settings .php
  editor.php       編集ページ      create.php  写真の作成(JSON を返す)
  image.php        写真1枚・いいね・コメント・削除     img.php  画像の配信
  editor.js style.css overlays/
src/             外から直接見えない
  bootstrap.php    セッション・DB・CSRF・入力チェック・ヘッダー
  image.php        GD による検査・合成・再保存
  mail.php         smtplib 相当の最小 SMTP クライアント
  layout.php       共通の HTML 部品
docker/          php.ini と Apache の設定
```

## PHP の標準機能で済ませているもの

| やること | 使っているもの |
|---|---|
| セッション | `session_start()`, `session_regenerate_id(true)` |
| パスワード | `password_hash()` / `password_verify()` |
| DB | PDO(SQLite)+ プリペアドステートメント |
| 画像の検査・合成・保存 | GD(`getimagesizefromstring`, `imagecreatefromstring`, `imagecopyresampled`, `imagepng`) |
| エスケープ | `htmlspecialchars()` |
| 乱数 | `random_bytes()` / `hash_equals()` |
| ファイルのアップロード | `$_FILES`, `is_uploaded_file()` |

## 課題要件との対応(セキュリティ)

- パスワード: bcrypt(塩付き)。ログイン連続失敗で 5 分ロック。
- SQL インジェクション: すべて `q()` 経由のプリペアドステートメント。
- XSS: 出力は `e()`(`htmlspecialchars`)+ CSP(インラインのスクリプト・スタイルなし)。
- CSRF: セッション紐づけトークンを全 POST で `hash_equals` 検証。
- アップロード: PNG / JPEG のみ(中身を `getimagesizefromstring` で判定)。GD で読み直して PNG として保存し直す。ファイル名はランダム。保存先は DocumentRoot の外(`/var/www/data`)。
- メールのトークン: ハッシュだけ保存・期限付き・1 回限り。再設定メールは、登録の有無が分からない文面。
- セッション: ログイン時に ID 再生成、HttpOnly、SameSite=Lax。パスワード変更で他のセッションは無効。
- エラー: `display_errors=Off`。コンソールにアクセスログを出さない設定。

## 割り切り

- コンテナ内の Apache の親プロセスは root(ワーカーは www-data)。
- メール変更は現在のパスワードを要求するだけで、再確認メールは送らない。
- 本番用の HTTPS は未設定(`BASE_URL` が `https://` なら Cookie に Secure が付く)。
