# イナズマイレブン 動画ランキング（GitHub Pages版）

毎日自動でYouTubeから動画を集めて、ランキングサイトを更新します。

## ファイル
- `index.html` … ランキングのページ
- `fetch_videos.py` … YouTubeから動画を集めるプログラム
- `.github/workflows/update.yml` … 毎日の自動実行の設定

## 設置の手順
1. **APIキーを作る**
   Google Cloud（console.cloud.google.com）でプロジェクトを作り、「YouTube Data API v3」を有効にして、APIキーを作成します。
2. **GitHubにリポジトリを作る**
   「Public」で作成します（無料でPagesを使うため）。
3. **ファイルを置く**
   `index.html`、`fetch_videos.py`、`README.md` をアップロードします。
   自動実行の設定は、「Add file」→「Create new file」で、名前の欄に `.github/workflows/update.yml` と入力し、中身を貼り付けます。
4. **APIキーを登録する**
   Settings → Secrets and variables → Actions → New repository secret
   名前は `YOUTUBE_API_KEY`、値はAPIキーです。
5. **Pagesを有効にする**
   Settings → Pages → Source を「GitHub Actions」にします。
6. **今すぐ動かす**
   Actionsタブ → 「毎日更新」 → Run workflow
   数分でサイトが公開されます。URLは `https://ユーザー名.github.io/リポジトリ名/` です。

## 設定を変えたいとき
`fetch_videos.py` の上のほうにある `KEYWORDS`（検索ワード）と `THRESHOLD`（再生数の基準）を書き換えます。

## 注意
- APIキーはSecretsにだけ入れ、ファイルに書かないでください。
- サイトはだれでも見られる公開です。
- 公開リポジトリは、60日間なにも更新がないと、定期実行が止まることがあります。止まったらActionsタブで再開してください。
- 1日のAPI使用量は約600ポイントで、無料枠（1日1万）に収まります。
