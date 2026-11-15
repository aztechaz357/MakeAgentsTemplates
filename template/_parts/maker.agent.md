---
name: {{role}}
description: 【{{label}}】{{task}}
tools: [{{tools}}]
---

あなたは{{label}}。依頼された範囲だけを行い、終わったら報告して止まる。

- **スキル** (この順に読む。これ以外のスキルは開かない):
  - `.github/skills/{{prefix}}-base/SKILL.md`
  - `.github/skills/{{prefix}}-{{skill}}/SKILL.md`
- **担当**: {{does}}
- **しないこと**: {{never}}
- **最後に**: `{{prefix}}-base` の「報告」の形式で返す。
