*This project has been created as part of the 42 curriculum by amakino*

# camagru

42 Tokyo の課題 camagru（写真共有サイト）。

## 構成
## python:3.12-slim
軽量版であるため、ビルド、起動、pullが早くなる。また、無駄なツールが入っていないため、攻撃対象が少なくなります。よってより脆弱性の少ないシステムを構築するためにこのイメージにしました。
## ディレクトリ構成

```
camagru/
├── Makefile, docker-compose.yml, Dockerfile, .env.example
├── README.md, SPEC.md
├── app/
│   ├── main.py        入口(wsgiref の WSGI アプリ)と URL の振り分け
│   ├── controllers/   リクエストを受けて、Model を呼び、View を選ぶ
│   ├── models/        DB(sqlite3)とのやり取り、ルール
│   ├── views/         HTML のテンプレート
│   └── lib/           認証・CSRF・メール・PNG/JPEG の読み書きと合成などの道具
├── public/            CSS・JS・飾り画像(外から直接見える唯一のフォルダ)
├── storage/           アップロード画像(git に入れない)
├── tests/             単体テスト(unittest)
└── docs/              個人メモ・補足資料
```
