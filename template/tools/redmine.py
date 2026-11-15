"""Redmine のチケットを読み書きする (標準ライブラリだけで動く)。

接続先は `{{config_dir}}/project.yml` の `redmine_url` と `redmine_project`、
API キーは `redmine_api_key_env` で指定した環境変数 (既定 REDMINE_API_KEY) から読む。
キーは引数にも出力にも出さない。

    python tools/redmine.py view 123 [--notes 5]
    python tools/redmine.py list [--status open] [--limit 25]
    python tools/redmine.py comment 123 --file note.md      (または --text "…")
    python tools/redmine.py create --subject "件名" --file body.md [--tracker 機能]
    python tools/redmine.py status 123 "解決"
"""
import argparse
import json
import os
import pathlib
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
CONFIG = ROOT / "{{config_dir}}" / "project.yml"


def config():
    """project.yml の `redmine_*: 値` の行を読む (YAML ライブラリを使わない)。"""
    conf = {}
    if CONFIG.exists():
        for m in re.finditer(r"^(redmine_\w+):\s*(.*?)\s*(?:#.*)?$", CONFIG.read_text(encoding="utf-8"), re.M):
            conf[m.group(1)] = m.group(2).strip("\"'")
    conf["redmine_url"] = os.environ.get("REDMINE_URL", conf.get("redmine_url", "")).rstrip("/")
    conf.setdefault("redmine_project", "")
    conf.setdefault("redmine_api_key_env", "REDMINE_API_KEY")
    return conf


class Redmine:
    def __init__(self, conf):
        self.url = conf["redmine_url"]
        self.project = conf["redmine_project"]
        self.key = os.environ.get(conf["redmine_api_key_env"] or "REDMINE_API_KEY", "")
        if not self.url:
            sys.exit("redmine_url が未設定。{{config_dir}}/project.yml に書く")
        if not self.key:
            sys.exit(f"環境変数 {conf['redmine_api_key_env']} に API キーがない。利用者が自分で設定する")

    def call(self, method, path, body=None, query=None):
        url = self.url + path + ("?" + urllib.parse.urlencode(query) if query else "")
        data = json.dumps(body).encode("utf-8") if body is not None else None
        req = urllib.request.Request(url, data=data, method=method)
        req.add_header("X-Redmine-API-Key", self.key)
        req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=30) as res:
                raw = res.read()
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "replace")[:300]
            hint = {
                401: "API キーが違うか、REST API が無効",
                403: "権限がない、または REST API が無効 (管理 > 設定 > API)",
                404: "チケットかプロジェクトが見つからない",
                422: "入力が受け付けられなかった",
            }.get(e.code, "")
            sys.exit(f"Redmine がエラーを返した: {e.code} {hint} {detail}")
        except urllib.error.URLError as e:
            sys.exit(f"Redmine に接続できない: {e.reason}")
        return json.loads(raw) if raw.strip() else {}

    def view(self, num, notes):
        i = self.call("GET", f"/issues/{num}.json", query={"include": "journals"})["issue"]
        out = [
            f"#{i['id']} {i.get('subject', '')}",
            f"状態: {i.get('status', {}).get('name', '')} / トラッカー: {i.get('tracker', {}).get('name', '')}"
            f" / 担当: {i.get('assigned_to', {}).get('name', 'なし')}",
            "",
            i.get("description") or "(説明なし)",
        ]
        journals = [j for j in i.get("journals", []) if j.get("notes")]
        for j in journals[-notes:] if notes else []:
            out += ["", f"--- {j.get('user', {}).get('name', '')} {j.get('created_on', '')}", j["notes"]]
        if notes and len(journals) > notes:
            out.append(f"\n(コメントは全 {len(journals)} 件。古いものは --notes で件数を増やすと読める)")
        return "\n".join(out)

    def list(self, status, limit):
        q = {"status_id": status, "limit": limit, "sort": "updated_on:desc"}
        if self.project:
            q["project_id"] = self.project
        issues = self.call("GET", "/issues.json", query=q).get("issues", [])
        return "\n".join(
            f"#{i['id']} [{i.get('status', {}).get('name', '')}] {i.get('subject', '')}" for i in issues
        ) or "(該当なし)"

    def comment(self, num, text):
        self.call("PUT", f"/issues/{num}.json", {"issue": {"notes": text}})
        return f"#{num} にコメントした"

    def create(self, subject, text, tracker):
        if not self.project:
            sys.exit("redmine_project が未設定")
        issue = {"project_id": self.project, "subject": subject, "description": text}
        if tracker:
            issue["tracker_id"] = self._id("/trackers.json", "trackers", tracker)
        made = self.call("POST", "/issues.json", {"issue": issue})["issue"]
        return f"#{made['id']} を作成した: {self.url}/issues/{made['id']}"

    def status(self, num, name):
        sid = self._id("/issue_statuses.json", "issue_statuses", name)
        self.call("PUT", f"/issues/{num}.json", {"issue": {"status_id": sid}})
        return f"#{num} の状態を {name} にした"

    def _id(self, path, key, name):
        items = self.call("GET", path).get(key, [])
        for item in items:
            if item["name"] == name:
                return item["id"]
        sys.exit(f"「{name}」がない。使えるもの: " + "、".join(i["name"] for i in items))


def body(args):
    if args.file:
        return pathlib.Path(args.file).read_text(encoding="utf-8")
    if args.text:
        return args.text
    sys.exit("--file か --text が必要")


def main(argv=None):
    sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description="Redmine のチケットを読み書きする")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("view"); s.add_argument("id", type=int); s.add_argument("--notes", type=int, default=5)
    s = sub.add_parser("list"); s.add_argument("--status", default="open"); s.add_argument("--limit", type=int, default=25)
    s = sub.add_parser("comment"); s.add_argument("id", type=int); s.add_argument("--file"); s.add_argument("--text")
    s = sub.add_parser("create"); s.add_argument("--subject", required=True); s.add_argument("--file"); s.add_argument("--text"); s.add_argument("--tracker")
    s = sub.add_parser("status"); s.add_argument("id", type=int); s.add_argument("name")
    a = p.parse_args(argv)
    r = Redmine(config())
    if a.cmd == "view":
        print(r.view(a.id, a.notes))
    elif a.cmd == "list":
        print(r.list(a.status, a.limit))
    elif a.cmd == "comment":
        print(r.comment(a.id, body(a)))
    elif a.cmd == "create":
        print(r.create(a.subject, body(a), a.tracker))
    elif a.cmd == "status":
        print(r.status(a.id, a.name))


if __name__ == "__main__":
    main()
