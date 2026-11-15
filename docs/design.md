# 仕組みと設計の判断

MakeAgent_001 (IEC 62443 用の一式) から、分野に依らない仕組みだけを取り出したもの。

## 構成

```
domains/<名前>/domain.toml   分野の定義 (入口の名前、成果物、担当、工程)
domains/<名前>/skills/       役割のスキルの本文 (任意)
domains/<名前>/files/        そのまま重ねて書き出すファイル (任意)
template/                    全分野に共通の雛形。{{名前}} が定義の値に置き換わる
template/_parts/             担当ごとに繰り返し使う雛形 (エージェント定義、役割のスキルの骨組み)
tools/generate.py            定義 + 雛形 → 一式
tools/sync_agents.py         .github/ → .claude/ (書き出した先でも使う)
tools/check_links.py         参照先の抜けと未記入のスキルの検査 (書き出した先でも使う)
.github/skills/make-agents/  質問に答えて定義を作るスキル
```

## 残した仕組みと、置き場所

| 仕組み | 書き出される場所 |
|---|---|
| 入口のスキルが統括として担当に割り振る | `.github/skills/<名前>/SKILL.md` の「割り振り」(定義の `[[stages]]` から作る) |
| 作成の担当と独立レビュー担当の対 | `[[roles]]` の `reviewer`。同じ役割のスキルを、レビュー担当は「レビューで見ること」として読む |
| 担当ごとに読むスキルを割り当てて文脈を小さく保つ | エージェント定義 (`.github/agents/<名前>.agent.md`) の「スキル」の行。統括は成果物の中身を読まない |
| 共通の決まり (設定、項目、トレース表、未整合台帳、報告) | `<接頭辞>-base` |
| モード | `lite` は作成だけ、`standard` はレビュー担当を追加、`audit` は棚卸し |
| どの工程からでも始め、ずれを台帳に残して後で合わせる | `<接頭辞>-base` の未整合台帳と `<接頭辞>-reconcile` |
| 索引を通して資料を必要な分だけ読む | `<接頭辞>-library` (`[support] librarian = true` のとき) |
| 学びを固有ルールとスキルに戻す | `<接頭辞>-improve`、`<設定フォルダ>/lessons.md` と `rules.md` |
| 文章で頼むとコマンドを案内する | 入口の「文章で頼まれたとき」と `references/howto.md` (定義から作る) |
| 作業の単位の置き場所の切替 | `references/tracker.md` (`github` / `redmine` / `manual` / `none`) |
| 定義の元を `.github/` に置き `.claude/` を生成する | `tools/sync_agents.py` |

## ツールごとの読込み先

| | Claude Code | Copilot (VS Code) | Copilot (GitHub 上) |
|---|---|---|---|
| 常時指示 | `CLAUDE.md` → `AGENTS.md` | `AGENTS.md` | `AGENTS.md` |
| 入口のスキル | `.claude/skills/<名前>/` (本体を指すだけ) | `.github/skills/<名前>/` | 両方 |
| 役割のスキル | `.github/skills/` をパスで読む | 同じ | 同じ |
| エージェント | `.claude/agents/` (生成) | `.github/agents/<名前>.agent.md` | 同じ |

Claude Code では、サブエージェントは別のサブエージェントを呼べない。入口のスキルは通常の会話で使うか、`claude --agent orchestrator` で起動する。

## トークンの消費を小さく保つ工夫

- 常に読まれるのは `AGENTS.md` だけ (テストで 14 行以内を確かめている)。分野の決まり (`principles`) は 3 つまでを目安にする。
- 文章で頼まれたときに読むのは逆引き辞典だけ。作業は始めない。
- 統括は ID、場所、12 行以内の報告だけを扱う。成果物の中身は担当がファイルで受け渡す。
- 作業の単位の切替、初期設定、資料の索引は、使うときだけ読む別ファイルにしてある。

## MakeAgent_001 から変えた点

| MakeAgent_001 | このテンプレート | 理由 |
|---|---|---|
| チケットが必須 | `tracker: none` を追加。案件名で進め、依頼文を `brief.md` に置く | チケットを切らない仕事 (説得、見直し、改善) で使うため |
| 文書の場所は 1 か所 | `records_dir` と成果物の場所に `{case}` を使える | 案件ごとにフォルダを分けられるようにするため |
| 状態 `逆生成` | `後追い` | コード以外でも使える呼び方にするため |
| 確認の結果 `検証済` / `未検証` | `確認済` / `未確認` | 同上 |
| 社内規定 (`sec-org-rules`) と過去資産 (`sec-prior`) が別のスキル | `<接頭辞>-library` の 1 つ。索引の「種別」で分ける | 読むファイルを減らすため |
| `audit` は監査担当 | 監査担当が無効なら整合担当が棚卸しする | 分野のチェック表がなくても使えるようにするため |
| 入口のスキルの名前が `sync_agents.py` に固定 | `user-invocable: false` でないスキルを入口として扱う | 分野に依らず同じ道具を使うため |
| issue テンプレート | 書き出さない。要るなら `domains/<名前>/files/` に置く | 分野ごとに項目が違うため |

## MakeAgent_001 の再現

`domains/iec62443/domain.toml` で、担当 (作成 5、レビュー 5、整合、監査、資料管理、改善)、8 工程の割り振り、トレース表の列、設定フォルダ、Redmine の道具までが書き出される。エージェントの名前とスキルの割当ては MakeAgent_001 と同じになる (テストで名前の一致を確かめている)。

中身まで再現するには、MakeAgent_001 から次を持ってくる。

1. `sec-requirements` `sec-docs` `sec-test-design` `sec-coding` `sec-test-exec` の本文 (frontmatter を除く) を `domains/iec62443/skills/requirements.md` などに置く。
2. それぞれの `references/` (要件マップ、脅威分析、コーディング規約の観点など) と `sec-audit` のチェック表を、`domains/iec62443/files/.github/skills/sec-<名前>/` に同じパスで置く。
3. issue テンプレートを `domains/iec62443/files/.github/ISSUE_TEMPLATE/` に置く。
4. 上の「変えた点」に合わせて語を直す (`逆生成` → `後追い`、`検証済` → `確認済`、`sec-org-rules` と `sec-prior` → `sec-library`、`org_rules_dir` と `prior_dir` → `library_dir`)。

再現できないもの、再現していないもの:

- 規定と過去資産の索引が 1 つにまとまる (上の表のとおり)。規定の階層 (社、部、課) の足し合わせは索引の「出どころと前提」に書く形になる。
- 規格本文をローカルに置いて参照する仕組み (`standard_docs`) は雛形にない。役割のスキルの本文と `[[settings]]` で足す。
- 実際の持込みは行っていない。見通しであり、持ち込んだ結果を動かして確かめてはいない。

## 定義を変えたあとの再生成

`generate.py` は既にあるファイルを残す。担当や工程を足したときは、次のどちらかにする。

- 新しいフォルダに書き出して、差分を見ながら取り込む。
- `--force` で上書きし、git の差分で、手で育てた部分 (役割のスキル、固有ルール) を戻す。`<設定フォルダ>/` は雛形に含まれないので上書きされない。

手で育てたスキルの中身を次の再生成でも使うには、`domains/<名前>/skills/` に戻しておく。
