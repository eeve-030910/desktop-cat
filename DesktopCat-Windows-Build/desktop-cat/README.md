# DesktopCat

Windows用の無料デスクトップペット。ネコ・犬・スズメをGUIから選べます。
ごはん・睡眠に対応。全コンテンツ無料、支援は任意です。

## 開発版の作成

WindowsでPython 3をインストールし、`BUILD_EXE.bat` を実行します。
`dist/DesktopCat-Dev-v0.4.5.exe` を開くとGUIが起動します。
利用者にはEXEを配布するため、Pythonのインストールは不要です。

## 設定と秘密情報

`.env.example` を `.env` にコピーし、必要な値を設定してください。
追加ライブラリ不要。対応形式は `KEY=value`、行頭 `#` のコメントです。
OS環境変数が `.env` より優先されます。

`.env` はGit・配布ZIP・EXEに含めません。更新URL、許可ホスト、寄付URLの
3項目だけをビルド時に公開設定としてEXEへコピーします。
これらのURLは利用者から見える情報です。
秘密のAPIキー・GitHubトークン・署名鍵はアプリへ埋め込まないでください。
GitHub Actionsで扱う秘密情報はリポジトリのSecretsを使用します。
すでに公開した秘密情報は `.gitignore` では消えません。失効・再発行が必要です。

## GitHub公開

1. GitHubで空の公開リポジトリを作成します。
2. このフォルダーで以下を実行します（OWNERは自分のユーザー名）。

```powershell
git init -b main
git add .
git status
git commit -m "Prepare DesktopCat for public release"
git remote add origin https://github.com/OWNER/desktop-cat.git
git push -u origin main
```

`git status` に `.env` や鍵が含まれていないことを確認してください。
公開用更新URLを用意して `BUILD_RELEASE.bat` を実行し、Windowsで動作確認後、
GitHub ReleasesからEXEまたはインストーラーを添付して公開します。
開発版は更新確認がなく、一般配布版は起動時と15分ごとの更新確認が必須です。
更新URLの準備と無料キャラの追加は `publisher/README.txt` を参照してください。

Windows実機でのビルド・動作確認は未実施です。
