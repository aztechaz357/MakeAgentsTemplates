# {{title}}

{{summary}}Claude Code と GitHub Copilot の両方で使える。

## まず使う

```
/{{name}} init          最初に 1 回。設定を作る
/{{name}} ○○したい      やりたいことを文章で書くと、実行するコマンドを案内する
/{{name}} {{default_stage}} {{case_ex}}   {{default_stage_label}}
```

## やりたいことから引く

| やりたいこと | 入力 |
|---|---|
{{readme_rows}}
| 成果物どうしのつじつまを合わせる | `/{{name}} reconcile` |
| 使ってみた学びをルールとスキルに反映する | `/{{name}} improve` |

全部の一覧: **[逆引き辞典](.github/skills/{{name}}/references/howto.md)**

## 誰に任せるか

| 名前 | 日本語名 | 任せること |
|---|---|---|
| orchestrator | 統括 | 窓口。迷ったらここ。担当に割り振ってまとめる |
{{readme_roles}}

## 詳しく

- [組織とスキルの割当て](docs/organization.md)
- 定義の元は `.github/` にある。`.claude/` は `python tools/sync_agents.py` で生成するので直接は編集しない。
- 中身がまだ骨組みのスキルは `python tools/check_links.py` で一覧できる。
