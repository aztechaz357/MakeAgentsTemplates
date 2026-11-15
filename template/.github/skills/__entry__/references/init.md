# init: 最初の設定

既にあるファイルは上書きしない。足りないものだけ作る。

1. 作業フォルダを軽く調べ (構成、既にある成果物)、分からない項目だけ利用者に質問する。
2. `{{config_dir}}/project.yml` を作る。

```yaml
default_mode: {{default_mode}}       # lite | standard
tracker: {{tracker}}          # {{unit}}の置き場所。{{tracker_choices}}
{{#if redmine}}
redmine_url: ""          # 例: https://redmine.example.co.jp (tracker: redmine のとき)
redmine_project: ""      # Redmine のプロジェクト識別子
redmine_api_key_env: REDMINE_API_KEY   # API キーを入れておく環境変数の名前 (キーそのものは書かない)
redmine_format: markdown # Redmine の書式。markdown | textile
{{/if}}
{{settings_yaml}}
{{#if librarian}}
library_dir: ""          # 参考資料の索引。使うなら {{config_dir}}/library
{{/if}}
docs:                    # 成果物の名称と場所。呼び方と置き場所に合わせて変える
{{docs_yaml}}
agent_skills: {}         # エージェントに追加で読ませるスキル。例: {<エージェント名>: [.github/skills/<名前>/SKILL.md]}
```

3. 利用者に尋ねて設定する。
   - {{unit}}をどこで管理するか ({{tracker_choices}})。`manual` の場合は `{{config_dir}}/outbox/` を `.gitignore` に追加する。
{{#if redmine}}
   - Redmine の場合は URL とプロジェクト識別子を設定し、API キーは利用者が自分で環境変数に入れるよう案内する (キーを尋ねない)。`python tools/redmine.py list` が通るかを確かめ、通らなければ原因を伝えて `manual` にするかを尋ねる。
{{/if}}
{{#if librarian}}
   - 規定、過去の成果物、参考資料を参照させるか。使う場合は `library_dir` を設定し、見出し行だけの `index.md` を作る。git で管理するかどうかを尋ね、しない場合は `.gitignore` に追加する。登録は `library add` で行うと案内する。
{{/if}}
   - 既にある成果物があれば `docs` の場所をそれに合わせる。Markdown 以外 (Word、Excel、PowerPoint) の場合は、エージェントが読み書きできる形にする方法を相談する。
4. 見出しだけのファイルを作る: `{{config_dir}}/rules.md` (「固有ルール」)、`{{config_dir}}/lessons.md` (「学びの記録」)。

トレース表、未整合台帳、成果物のファイルは init では作らない。最初にその工程を実行したときに担当エージェントが作る。
