# MakeAgentsTemplates

仕事の種類 (分野) ごとに、エージェントとスキルの一式を作るためのテンプレート。分野の定義を 1 つ書くと、入口のスキル、作成とレビューの担当、共通の決まり、逆引き辞典が書き出される。Claude Code と GitHub Copilot の両方で動く。

> 仕事を支援する道具で、結論や適合を保証するものではない。規格本文や社内の資料は含まない。

## やりたいことから引く

| やりたいこと | すること |
|---|---|
| 答えのない問題 (説得、計画の見直し、業務改善) にすぐ使いたい | `python tools/generate.py domains/solve --out <作業フォルダ>` を実行し、そのフォルダで `/solve init` |
| 新しい分野の一式を、質問に答えて作りたい | このリポジトリを開き、チャットで `/make-agents <作りたい一式の説明>` |
| 新しい分野の一式を、手で定義して作りたい | 下の「新しい分野の一式を作る」 |
| IEC 62443 の開発用の骨組みを書き出したい | `python tools/generate.py domains/iec62443 --out <作業フォルダ>` ([中身の再現](docs/design.md#makeagent_001-の再現)) |
| 全分野に共通の文章を直したい | `template/` を直して `python -m unittest discover tools` |
| 仕組みを知りたい | [docs/design.md](docs/design.md) |

## 新しい分野の一式を作る

Python 3.11 以上が要る (追加のライブラリは要らない)。

1. `domains/_template/` を `domains/<名前>/` にコピーし、`domain.toml` を書き換える。決めるのは、入口の名前、成果物、作成の担当とレビュー担当、工程。
2. 定義を検査する。

   ```bash
   python tools/generate.py domains/<名前> --check
   ```

3. 書き出す。既にあるファイルは残される (上書きは `--force`)。

   ```bash
   python tools/generate.py domains/<名前> --out <作業フォルダ>
   ```

4. 役割のスキルの中身を書く。書き出された `.github/skills/<接頭辞>-<役割>/SKILL.md` は骨組みで、「(ここに書く)」を分野の知識に置き換える。先に `domains/<名前>/skills/<役割>.md` に書いておけば、その本文で書き出される。未記入のスキルは、作業フォルダで `python tools/check_links.py` を実行すると一覧される。
5. 作業フォルダのチャットで `/<名前> init`、続けて `/<名前> ○○したい`。

## 書き出される一式

| もの | 役目 |
|---|---|
| `AGENTS.md` (10 行前後) | 常に読まれる指示。これ以外は必要なときだけ読まれる |
| 入口のスキル `/<名前>` | 統括として担当に割り振る。文章で頼むと、実行するコマンドを案内する (逆引き辞典) |
| 作成の担当と、その独立レビュー担当 | 担当ごとに「共通の決まり + 自分の役割のスキル」だけを読む |
| 共通の決まり | 設定の読み方、成果物の項目、トレース表、未整合台帳、報告の形式 |
| 整合担当、改善担当 (任意で資料管理、監査) | 順番どおりに進まなかった分のつじつま合わせ、学びを固有ルールとスキルに戻す |
| モード | `lite` (作成だけ)、`standard` (独立レビュー付き)、`audit` (棚卸し) |
| 作業の単位の切替 | GitHub の issue、Redmine、手動、チケットなし (案件名) |
| `tools/sync_agents.py` | `.github/` の定義から `.claude/` を生成する |

## 同梱の定義

| 定義 | 中身 |
|---|---|
| [domains/solve](domains/solve/domain.toml) | 答えのない問題の解決。問題整理、選択肢、資料作成、実行計画の 4 担当と、前提を疑う、反論する、読み手になりきる 3 つのレビュー担当。スキルの中身まで記入済み |
| [domains/iec62443](domains/iec62443/domain.toml) | MakeAgent_001 の構成 (作成 5、レビュー 5、支援 4、8 工程) の骨組み。分野の知識は含まない |
| [domains/_template](domains/_template/domain.toml) | 定義の書き方の見本 |

## 確認の状況

- 生成、`.claude/` の同期、リンクの検査は `python -m unittest discover tools` で確かめている。
- 書き出した一式を Claude Code や GitHub Copilot で実際に動かす確認は、まだしていない。

このリポジトリの開発は issue を起票し、`feature/<issue番号>-<要約>` ブランチで PR を出す。
