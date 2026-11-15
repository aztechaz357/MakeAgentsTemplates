---
name: make-agents
description: 分野や困りごとを聞き取り、その仕事のためのエージェントとスキルの一式 (入口のスキル、作成とレビューの担当、共通の決まり、逆引き辞典) を定義ファイルから書き出す。新しい分野の一式を作りたい、既にある定義を直したいときに使う。
argument-hint: "<作りたい一式の説明> | check <定義の名前> | out <定義の名前> <書き出す先>"
---
<!-- tools/sync_agents.py が生成。直接編集せず .github/ 側を直す -->

本体は GitHub Copilot と共用するため `.github/skills/make-agents/` にある。`.github/skills/make-agents/SKILL.md` を読み、渡された引数でその手順どおりに実行する。
