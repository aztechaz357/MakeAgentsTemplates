"""分野の定義 (`domains/<名前>/domain.toml`) から、エージェントとスキルの一式を書き出す。

    python tools/generate.py domains/solve --out ../my-project   書き出す (既にあるファイルは残す)
    python tools/generate.py domains/solve --out ../my-project --force   既にあるファイルも上書きする
    python tools/generate.py domains/solve --check               定義だけを検査し、書き出すファイルを一覧する

定義フォルダの中身:
    domain.toml        分野の定義 (書き方は domains/_template/domain.toml)
    skills/<名前>.md   役割のスキルの本文 (任意。なければ骨組みを書き出す)
    files/             そのまま重ねて書き出すファイル (任意。references、issue テンプレートなど)

書き出したあと、出力先で tools/sync_agents.py と tools/check_links.py を実行する。
Python 3.11 以上 (標準ライブラリだけを使う)。
"""
import argparse
import pathlib
import re
import subprocess
import sys
import tomllib

HERE = pathlib.Path(__file__).resolve().parent
TEMPLATE = HERE.parent / "template"
TRACKERS = ["github", "redmine", "manual", "none"]
SUPPORT = ["reconciler", "improver", "librarian", "auditor"]
RESERVED = {"orchestrator", "init", "help", "reconcile", "audit", "improve", "library", "lite", "standard"}
DEFAULT_NEVER = "自分の担当の外の成果物を直さない。利用者の決定がない選択は `仮` の案にとどめる。"
NAME = re.compile(r"[a-z][a-z0-9-]*$")


class DefinitionError(Exception):
    pass


# ---------- 定義の読込みと検査 ----------

def load(domain_dir):
    path = pathlib.Path(domain_dir) / "domain.toml"
    if not path.exists():
        raise DefinitionError(f"{path} がない")
    with open(path, "rb") as f:
        d = tomllib.load(f)
    errors = []
    dom = d.setdefault("domain", {})
    for key in ("name", "title", "summary", "triggers"):
        if not dom.get(key):
            errors.append(f"[domain] の {key} が要る")
    name = dom.get("name", "")
    dom.setdefault("prefix", name)
    dom.setdefault("config_dir", "." + name)
    dom.setdefault("user", "利用者")
    dom.setdefault("tracker", "github")
    dom.setdefault("default_mode", "lite")
    dom.setdefault("records_dir", "docs/" + name)
    dom.setdefault("trace_columns", ["ID", "上流", "確認", "状態", "チケット"])
    dom.setdefault("trace_note", "")
    dom.setdefault("principles", [])
    dom.setdefault("flow_note", "")
    dom.setdefault("escalate", "")
    support = {k: False for k in SUPPORT} | {"reconciler": True, "improver": True, "redmine": False}
    support |= d.get("support", {})
    d["support"] = support
    roles, stages, arts = d.get("roles", []), d.get("stages", []), d.get("artifacts", [])
    for key in ("name", "prefix"):
        if dom.get(key) and not NAME.match(dom[key]):
            errors.append(f"[domain] の {key} は半角の小文字、数字、ハイフンで書く: {dom[key]}")
    if dom["tracker"] not in TRACKERS:
        errors.append(f"tracker は {TRACKERS} のどれか: {dom['tracker']}")
    if dom["tracker"] == "redmine" and not support["redmine"]:
        errors.append("tracker = \"redmine\" なら [support] に redmine = true が要る")
    if dom["default_mode"] not in ("lite", "standard"):
        errors.append("default_mode は lite か standard")
    for col in ("ID", "上流", "状態"):
        if col not in dom["trace_columns"]:
            errors.append(f"trace_columns に {col} が要る")
    if not roles:
        errors.append("[[roles]] が 1 つは要る")
    if not stages:
        errors.append("[[stages]] が 1 つは要る")
    if not arts:
        errors.append("[[artifacts]] が 1 つは要る")
    names = []
    for r in roles:
        for key in ("name", "label", "task"):
            if not r.get(key):
                errors.append(f"[[roles]] の {key} が要る: {r}")
        r.setdefault("skill", r.get("name", ""))
        r.setdefault("does", r.get("task", ""))
        r.setdefault("never", DEFAULT_NEVER)
        r.setdefault("tools", ["read", "search", "edit"])
        r.setdefault("ask", r.get("task", ""))
        r.setdefault("edits", "担当の成果物、トレース表、台帳")
        r.setdefault("reviewer", "")
        if r["reviewer"]:
            r.setdefault("reviewer_label", r.get("label", "") + "のレビュー担当")
            r.setdefault("reviewer_view", "")
            names.append(r["reviewer"])
        names.append(r.get("name", ""))
    for n in names:
        if not NAME.match(n or ""):
            errors.append(f"エージェント名は半角の小文字、数字、ハイフンで書く: {n}")
        if n in RESERVED or n in SUPPORT:
            errors.append(f"エージェント名が予約語と重なる: {n}")
    for n in {n for n in names if names.count(n) > 1}:
        errors.append(f"エージェント名が重なっている: {n}")
    callable_roles = {r.get("name") for r in roles} | {k for k in SUPPORT if support[k]}
    keys = []
    for s in stages:
        for key in ("key", "label", "flow"):
            if not s.get(key):
                errors.append(f"[[stages]] の {key} が要る: {s}")
        keys.append(s.get("key", ""))
        if s.get("key") in RESERVED or s.get("key") in names:
            errors.append(f"工程の key が予約語かエージェント名と重なる: {s.get('key')}")
        for step in s.get("flow", []):
            if step.split(":")[0] not in callable_roles:
                errors.append(f"工程 {s.get('key')} の flow に、定義のない役割がある: {step}")
        s.setdefault("makes", "")
        s.setdefault("arg", "")
        s.setdefault("ask", s.get("label", ""))
    dom.setdefault("default_stage", keys[0] if keys else "")
    if dom["default_stage"] not in keys:
        errors.append(f"default_stage が [[stages]] にない: {dom['default_stage']}")
    for a in arts:
        for key in ("id", "name", "path"):
            if not a.get(key):
                errors.append(f"[[artifacts]] の {key} が要る: {a}")
    # frontmatter の 1 行に入る文字列。YAML として読めなくなる書き方を避ける
    one_line = [dom.get("summary", ""), dom.get("triggers", ""), dom.get("title", "")]
    one_line += [r.get("task", "") + r.get("reviewer_view", "") for r in roles]
    for text in one_line:
        if ": " in text or " #" in text or "\n" in text:
            errors.append(f"1 行の説明に「: 」「 #」改行は使えない: {text[:30]}…")
    if errors:
        raise DefinitionError("\n".join(errors))
    return d


# ---------- 雛形に入れる値 ----------

def step_text(step, with_note=True):
    name, _, note = step.partition(":")
    return f"{name} ({note})" if note and with_note else name


def stage_reviewers(stage, by_name):
    if "review" in stage:
        return stage["review"]
    out = []
    for step in stage["flow"]:
        r = by_name.get(step.split(":")[0])
        if r and r["reviewer"] and r["reviewer"] not in out:
            out.append(r["reviewer"])
    return out


def context(d):
    dom, sup = d["domain"], d["support"]
    roles, stages, arts = d["roles"], d["stages"], d["artifacts"]
    by_name = {r["name"]: r for r in roles}
    name, prefix, tracker = dom["name"], dom["prefix"], dom["tracker"]
    none = tracker == "none"
    unit = dom.get("unit") or ("案件" if none else "チケット")
    case_ex = "<案件名>" if none else "12"
    records = dom["records_dir"]
    label = {r["name"]: r["label"] for r in roles} | {
        "reconciler": "整合担当", "improver": "改善担当", "librarian": "資料管理担当", "auditor": "監査担当"}

    def cmd(stage):
        return f"/{name} {stage['key']} {stage['arg'] or case_ex}"

    def flow_labels(stage):
        return " → ".join(label[s.split(":")[0]].removesuffix("担当") for s in stage["flow"])

    routing = []
    for s in stages:
        arg = f"`{s['key']}`" + (f" {s['arg']}" if s["arg"] else "")
        revs = "、".join(stage_reviewers(s, by_name)) or "—"
        routing.append(f"| {arg} | {' → '.join(step_text(x) for x in s['flow'])} | {revs} |")
    routing.append(f"| `reconcile [{unit}]` | reconciler → (承認された修正を各担当へ) → reconciler | — |")
    routing.append(f"| `audit` | {'auditor' if sup['auditor'] else 'reconciler (棚卸し。反映はしない)'} | — |")
    if sup["librarian"]:
        routing.append("| `library add <場所> [説明]`、`library find <キーワード>` | librarian | — |")
    routing.append("| `improve` | improver | — |")

    subs = ["init", "reconcile", "audit"] + (["library"] if sup["librarian"] else []) + ["improve", "help"]
    hint = " | ".join(["reconcile", "audit"] + (["library add <場所>"] if sup["librarian"] else []) + ["init", "improve"])

    if none:
        unit_rule = (f"作業は案件ごとにまとめ、番号の代わりに案件名を使う。チケットは要らない "
                     f"(`{dom['config_dir']}/project.yml` の `tracker` で GitHub や Redmine のチケットに切り替えられる)。")
        case_rule = "既にある案件の名前だけ"
        case_ex_note = "`<案件名>` には案件の名前 (半角英数字とハイフン) を入れる。新しい案件なら、名前のあとに状況を書く。"
        case_missing_rule = "案件名が文章にないときは、文章から短い案件名 (半角英数字とハイフン) を付けて埋め、利用者の文章を補足としてそのまま続ける。"
    else:
        unit_rule = (f"作業は必ずチケット (`{dom['config_dir']}/project.yml` の `tracker` が示す場所。既定は {tracker}) に紐付け、"
                     "`feature/<チケット番号>-<要約>` ブランチ (環境が作業ブランチを用意する場合はそのブランチ) で行う。main へ直接コミットしない。")
        case_rule = "番号だけ"
        case_ex_note = "`12` はチケットの番号の例。"
        case_missing_rule = "番号が要るコマンドで番号が分からないときは、番号の要らない形 (`<エージェント名> <依頼>`) を先に案内する。"
    choices = [t for t in TRACKERS if t != "redmine" or sup["redmine"]]

    howto_roles = [f"| {r['ask']} | {r['name']} | {r['label']} |" for r in roles]
    howto_roles += [f"| {r['label'].removesuffix('担当')}の成果物を見てほしい | {r['reviewer']} | {r['reviewer_label']} |"
                    for r in roles if r["reviewer"]]
    howto_roles.append("| 成果物どうしが食い違っている。合わせたい | reconciler | 整合担当 |")
    if sup["auditor"]:
        howto_roles.append("| 区切りの前に不足を洗い出したい | auditor | 監査担当 |")
    if sup["librarian"]:
        howto_roles.append("| 規定や過去の資料を登録したい、探したい | librarian | 資料管理担当 |")
    howto_roles.append("| スキルやルールを使いやすく直したい | improver | 改善担当 |")

    extra = d.get("howto", [])
    howto_extra = ""
    if extra:
        rows = "\n".join(f"| {h['want']} | {h['input']} |" for h in extra)
        howto_extra = f"\n## {dom['title']}でよくあること\n\n| やりたいこと | 入力 |\n|---|---|\n{rows}\n"

    first_art = arts[0]["id"]
    assign = [f"| orchestrator | 統括 | {name} | まとめ、初期設定 |"]
    for r in roles:
        assign.append(f"| {r['name']} | {r['label']} | {prefix}-base、{prefix}-{r['skill']} | {r['edits']} |")
    for r in roles:
        if r["reviewer"]:
            assign.append(f"| {r['reviewer']} | {r['reviewer_label']} | {prefix}-base、{prefix}-review、{prefix}-{r['skill']} | なし |")
    assign.append(f"| reconciler | 整合担当 | {prefix}-base、{prefix}-reconcile | トレース表、台帳 |")
    if sup["auditor"]:
        assign.append(f"| auditor | 監査担当 | {prefix}-base、{prefix}-audit、{prefix}-reconcile | 棚卸しの結果 |")
    if sup["librarian"]:
        assign.append(f"| librarian | 資料管理担当 | {prefix}-base、{prefix}-library | 資料の索引 |")
    assign.append(f"| improver | 改善担当 | {prefix}-base、{prefix}-improve | 固有ルール、学びの記録、スキル |")

    m = ["flowchart TD", f'    U(["{dom["user"]}"])', '    O["orchestrator<br>統括"]',
         '    U <-->|"依頼、決定、承認"| O', '    subgraph MAKE["作成"]']
    m += [f'        M{i}["{r["name"]}<br>{r["label"]}"]' for i, r in enumerate(roles)]
    m += ["    end", '    subgraph REVIEW["レビュー (作成者から独立)"]']
    m += [f'        R{i}["{r["reviewer"]}<br>{r["reviewer_label"]}"]' for i, r in enumerate(roles) if r["reviewer"]]
    m += ["    end", '    subgraph SUPPORT["支援"]']
    sup_names = [k for k in SUPPORT if sup[k]]
    m += [f'        S{i}["{k}<br>{label[k]}"]' for i, k in enumerate(sup_names)]
    m += ["    end", "    O --> " + " & ".join(f"M{i}" for i in range(len(roles)))]
    rev_ids = [f"R{i}" for i, r in enumerate(roles) if r["reviewer"]]
    if rev_ids:
        m.append("    O --> " + " & ".join(rev_ids))
    else:
        m = [line for line in m if "REVIEW" not in line]
        m.remove("    end")
    m.append("    O --> " + " & ".join(f"S{i}" for i in range(len(sup_names))))
    m += [f"    R{i} -.->|レビュー| M{i}" for i, r in enumerate(roles) if r["reviewer"]]

    empty = '""'
    settings = "\n".join(
        f"{s['key']}: {s.get('value', empty)}" + (f"   # {s['comment']}" if s.get("comment") else "")
        for s in d.get("settings", []))
    default_stage = next(s for s in stages if s["key"] == dom["default_stage"])
    principles = "\n".join(f"- {p}" for p in dom["principles"])
    brief_dir = records if "{case}" in records else f"{dom['config_dir']}/cases/{{case}}"
    return {
        **{k: v for k, v in dom.items() if isinstance(v, str)},
        "unit": unit, "case_word": "案件名" if none else "番号", "case_ex": case_ex,
        "case_none_ex": dom.get("case_example", "new-idea"), "case_rule": case_rule, "unit_rule": unit_rule,
        "case_ex_note": case_ex_note, "case_missing_rule": case_missing_rule,
        "principles_bullets": principles or "- 資料の本文を成果物に書き写さない。出どころと自分の言葉の要約だけを書く。",
        "stage_keys": "|".join(s["key"] for s in stages),
        "subcommands_code": " ".join(f"`{s}`" for s in subs), "subcommand_hint": hint,
        "routing_rows": "\n".join(routing),
        "flow_note": dom["flow_note"],
        "escalate_note": (f"lite で始めても、{dom['escalate']}と分かったら、standard を利用者に提案する。" if dom["escalate"] else ""),
        "guide_example": f"{default_stage['key']} {case_ex}" + (" <補足>" if none else ""),
        "trace_header": ",".join(dom["trace_columns"]),
        "id_examples": " ".join(f"`{a['id']}-001`" for a in arts[:6]), "id_first": first_art,
        "tracker_choices": " | ".join(choices),
        "settings_yaml": settings,
        "docs_yaml": "\n".join(f"  {a['id']}: {{name: {a['name']}, path: {a['path']}}}" for a in arts),
        "brief_path": brief_dir + "/brief.md",
        "howto_roles": "\n".join(howto_roles),
        "howto_stages": "\n".join(f"| {s['ask']} | `{cmd(s)}` | {flow_labels(s)} |" for s in stages),
        "howto_extra": howto_extra,
        "howto_reviews": "\n".join(
            f"| 既にある{r['label'].removesuffix('担当')}の成果物の問題を洗い出したい | `/{name} {r['reviewer']} <ファイル> の問題を洗い出して` |"
            for r in roles if r["reviewer"]) or "| (レビュー担当が定義されていない) | — |",
        "auditor_also": " と auditor" if sup["auditor"] else "",
        "org_mermaid": "\n".join(m), "assign_rows": "\n".join(assign),
        "stage_rows": "\n".join(
            f"| `{s['key']}` | {s['label']} | {s['makes'] or '—'} | {' → '.join(step_text(x, False) for x in s['flow'])} |"
            for s in stages),
        "default_stage_label": default_stage["label"],
        "readme_rows": "\n".join(f"| {s['ask']} | `{cmd(s)}` |" for s in stages),
        "readme_roles": "\n".join(
            [f"| {r['name']} | {r['label']} | {r['task']} |" for r in roles]
            + [f"| {r['reviewer']} | {r['reviewer_label']} | {r['label']}の成果物の独立レビュー |" for r in roles if r["reviewer"]]
            + [f"| {k} | {label[k]} | {t} |" for k, t in [
                ("reconciler", "成果物どうしのつじつま合わせ、棚卸し"), ("auditor", "区切りの前の棚卸し"),
                ("librarian", "規定と過去の資料の登録、検索"), ("improver", "使ってみた学びをルールとスキルに反映")] if sup[k]]),
        "librarian": sup["librarian"], "auditor": sup["auditor"], "redmine": sup["redmine"],
    }


# ---------- 書き出し ----------

BLOCK = re.compile(r"^\{\{#if (\w+)\}\}\n(.*?)^\{\{/if\}\}\n", re.S | re.M)
VAR = re.compile(r"\{\{(\w+)\}\}")


def render(text, ctx):
    text = BLOCK.sub(lambda m: m.group(2) if ctx.get(m.group(1)) else "", text)

    def value(m):
        if m.group(1) not in ctx:
            raise DefinitionError(f"雛形の {{{{{m.group(1)}}}}} に入れる値がない")
        return str(ctx[m.group(1)])
    text = VAR.sub(value, text)
    return re.sub(r"\n{3,}", "\n\n", text)


def tools_text(aliases):
    return ", ".join(f'"{a}"' for a in aliases)


def build(d, domain_dir):
    """書き出すファイルを {相対パス: 内容 (str または bytes)} で返す。"""
    domain_dir = pathlib.Path(domain_dir)
    ctx, sup, dom = context(d), d["support"], d["domain"]
    out = {}
    optional = {"__prefix__-library": "librarian", "librarian.agent.md": "librarian",
                "__prefix__-audit": "auditor", "auditor.agent.md": "auditor",
                "redmine.py": "redmine", "test_redmine.py": "redmine"}
    for src in sorted(TEMPLATE.rglob("*")):
        rel = src.relative_to(TEMPLATE)
        if not src.is_file() or rel.parts[0] == "_parts":
            continue
        if any(not sup[flag] for part, flag in optional.items() if part in rel.parts):
            continue
        target = rel.as_posix().replace("__entry__", dom["name"]).replace("__prefix__", dom["prefix"])
        out[target] = render(src.read_text(encoding="utf-8"), ctx)
    for tool in ("sync_agents.py", "check_links.py"):
        out[f"tools/{tool}"] = (HERE / tool).read_text(encoding="utf-8")

    parts = {p.name: p.read_text(encoding="utf-8") for p in (TEMPLATE / "_parts").iterdir()}
    done = set()
    for r in d["roles"]:
        rctx = {**ctx, **{k: v for k, v in r.items() if isinstance(v, str)}, "role": r["name"],
                "tools": tools_text(r["tools"]),
                "reviewer_tools": tools_text([t for t in r["tools"] if t != "edit"]),
                "reviewer_or_human": r["reviewer"] or "人"}
        if rctx.get("reviewer_view") and not rctx["reviewer_view"].endswith("。"):
            rctx["reviewer_view"] += "。"
        out[f".github/agents/{r['name']}.agent.md"] = render(parts["maker.agent.md"], rctx)
        if r["reviewer"]:
            out[f".github/agents/{r['reviewer']}.agent.md"] = render(parts["reviewer.agent.md"], rctx)
        if r["skill"] in done:
            continue
        done.add(r["skill"])
        body_file = domain_dir / "skills" / f"{r['skill']}.md"
        body = body_file.read_text(encoding="utf-8") if body_file.exists() else render(parts["role_skill.md"], rctx)
        users = "、".join(x["name"] + (f" と {x['reviewer']}" if x["reviewer"] else "")
                         for x in d["roles"] if x["skill"] == r["skill"])
        front = (f"---\nname: {dom['prefix']}-{r['skill']}\n"
                 f"description: {r['task']}ときの手順と観点。{users} が使う。\nuser-invocable: false\n---\n\n")
        out[f".github/skills/{dom['prefix']}-{r['skill']}/SKILL.md"] = front + body
    overlay = domain_dir / "files"
    if overlay.exists():
        for src in sorted(overlay.rglob("*")):
            if src.is_file():
                out[src.relative_to(overlay).as_posix()] = src.read_bytes()
    return out


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="分野の定義からエージェントとスキルの一式を書き出す")
    ap.add_argument("domain_dir", help="domain.toml のあるフォルダ")
    ap.add_argument("--out", help="書き出す先のフォルダ")
    ap.add_argument("--force", action="store_true", help="既にあるファイルも上書きする")
    ap.add_argument("--check", action="store_true", help="定義を検査し、書き出すファイルを一覧するだけ")
    args = ap.parse_args()
    try:
        files = build(load(args.domain_dir), args.domain_dir)
    except DefinitionError as e:
        sys.exit(f"定義に誤りがある:\n{e}")
    if args.check or not args.out:
        for rel in sorted(files):
            print(rel)
        print(f"定義は読めた。書き出すファイルは {len(files)} 個 (--out <フォルダ> で書き出す)")
        return
    out = pathlib.Path(args.out).resolve()
    written, kept = 0, []
    for rel, content in files.items():
        path = out / rel
        if path.exists() and not args.force:
            kept.append(rel)
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, bytes):
            path.write_bytes(content)
        else:
            path.write_text(content, encoding="utf-8", newline="\n")
        written += 1
    print(f"{out} に {written} 個を書き出した", flush=True)
    if kept:
        print(f"既にあるので残した: {len(kept)} 個 (上書きするなら --force)")
        for rel in kept:
            print("  " + rel, flush=True)
    for tool in ("sync_agents.py", "check_links.py"):
        subprocess.run([sys.executable, str(out / "tools" / tool)], check=False)


if __name__ == "__main__":
    main()
