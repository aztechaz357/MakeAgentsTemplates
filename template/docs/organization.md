# エージェントの組織とスキルの割当て

役割ごとにエージェントを分け、それぞれが自分の役割に要るスキルだけを読む。オーケストレーターは成果物の中身を読まず、ID と報告だけを扱う。これでどのエージェントの文脈も小さく保つ。

## 組織図

```mermaid
{{org_mermaid}}
```

- エージェントどうしは直接やり取りしない。依頼と報告はすべて orchestrator を通る。
- 成果物はファイルで受け渡す。orchestrator が渡すのは ID とファイルの場所だけ。

## 割当て

| エージェント | 日本語名 | 読むスキル | 編集 |
|---|---|---|---|
{{assign_rows}}

## 工程

| 工程 | すること | 作るもの | 順に動く担当 |
|---|---|---|---|
{{stage_rows}}

## 割当てを変える

| 範囲 | 方法 |
|---|---|
| ある場所だけ、スキルを足す | `{{config_dir}}/project.yml` の `agent_skills` に書く |
| 全体で変える | `.github/agents/<名前>.agent.md` の「スキル」の行を直し、`python tools/sync_agents.py` で Claude Code 用を作り直す |
| エージェントを足す | `.github/agents/` に定義を足して同じく生成し、`.github/skills/{{name}}/SKILL.md` の割り振りの表と逆引き辞典に加える |
| スキルを足す | `.github/skills/<名前>/SKILL.md` を作り、使わせたいエージェントに割り当てる |

直したあとは `python tools/check_links.py` で、参照先の抜けと未記入のスキルを確かめる。
