更新サーバーの準備（この作業は配布者が行います）

1. 認証なしで取得できる公開HTTPS配布先を用意します。
   現在の所有者限定のサイトは、EXEからの更新確認にはそのまま使えません。
2. policy.example.jsonを編集し、policy.jsonとして公開します。
3. catalog.example.jsonをcharacters/catalog.jsonとして公開します。
4. update_config.jsonにpolicy_urlとallowed_hosts（ホスト名だけ）を記入します。
5. BUILD_RELEASE.batで一般配布版をビルドし、テスト後に配布します。
開発版はBUILD_EXE.batで作成し、更新URLなしで利用できます。

例:
{"policy_url":"https://your-domain.example/policy.json","allowed_hosts":["your-domain.example"]}

minimum_version: これより古いアプリは利用を止めるバージョン。
latest_version: 配布中の最新版。
download_url: 実際のWindowsインストーラー、またはそのダウンロードページ。
catalog_url: キャラ一覧のURL。
公開JSONはキャッシュされない設定にしてください。minimum_versionを上げる前に、
必ずその版のWindows実行ファイルを公開・確認してください。

一般配布版のみ起動時と15分ごとに確認。通信に失敗した場合も利用を止め、再試行を表示します。
更新プログラムの自動実行・上書きは行いません。ユーザーが更新ページを開きます。
0.3.3以前の配布済みEXEにはこの仕組みがないため、遠隔停止できません。
端末側のプログラム改造まで完全に防ぐことはできません。

無料キャラの追加:
cat_0.png〜cat_3.pngとcat_sleep.png（すべて128×96）の5枚だけをZIP直下に入れます。
catalog.jsonのcharactersに以下の項目を登録します:
id / name / free:true / minimum_app_version / url / sha256
sha256は素材ZIP全体のSHA-256。urlはallowed_hosts内のHTTPSに限定します。
画像だけの追加ならEXEの再配布は不要です。特殊動作を追加する場合は本体更新が必要です。
全コンテンツ無料。キャラのfreeはtrueにしてください。購入確認は不要です。
任意の寄付はupdate_config.jsonのdonate_urlにHTTPSの外部寄付ページを設定します。
寄付の有無による制限・特典・キャラ解放はありません。

注意: この実装はHTTPS配布元を信頼する方式です。配布用サーバーとアカウントを保護し、
本体のコード署名も配布前に整えてください。秘密鍵をアプリに含めないでください。
