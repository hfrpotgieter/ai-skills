#!/usr/bin/env python3
"""Fill template.html from a review spec and a patch.

    python3 fill.py <review.json> <change.patch> [-o review.html]

The output defaults to review.html beside review.json. Standard library only.

review.json:

{
  "title": "Review: …",
  "repo": "repo name · base commit",
  "date": "YYYY-MM-DD",
  "summary": "Two to four sentences.",
  "decisions": [
    {"id": "Q1", "title": "…", "answer": "…", "why": "…"},
    {"id": "Q5", "title": "…", "answer": "…", "why": "…", "no_code": true}
  ],
  "diagrams": [
    {"caption": "…", "before": "flowchart TD\\n  A[\\"…\\"] --> B", "after": "…"}
  ],
  "files": [
    {"path": "path/in/the/patch.go", "notes": [{"ids": ["Q1", "Q2"], "text": "…"}]}
  ],
  "verification": [{"cmd": "go build ./...", "pass": true, "note": "optional"}],
  "out_of_scope": ["…"],
  "open_questions": ["…"],
  "apply": "shell commands, one per line"
}

Text fields are plain text: HTML is escaped, and `backticks` become <code>.
Mermaid sources are escaped as-is; write <br/> line breaks literally.

The trace is checked before anything is written; any failure exits 1:
- every file in the patch has a section, and every section's path is in the patch;
- every note names known decision ids;
- every decision is named by a note, or is marked no_code (and then by none).
"""

import argparse
import html
import json
import os
import re
import sys

TEMPLATE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "template.html")


def text(s):
    parts = re.split(r"`([^`]+)`", html.escape(s, quote=False))
    return "".join(f"<code>{p}</code>" if i % 2 else p for i, p in enumerate(parts))


def split_patch(patch):
    files = {}
    for chunk in re.split(r"(?m)^(?=diff --git )", patch):
        m = re.match(r"diff --git a/(\S+) b/(\S+)", chunk)
        if m:
            files[m.group(2)] = chunk
    return files


def check(spec, patched):
    errs = []
    ids = [d["id"] for d in spec["decisions"]]
    no_code = {d["id"] for d in spec["decisions"] if d.get("no_code")}
    named = set()
    sections = [f["path"] for f in spec["files"]]
    for path in patched:
        if path not in sections:
            errs.append(f"patch file has no section in files: {path}")
    for f in spec["files"]:
        if f["path"] not in patched:
            errs.append(f"files entry is not in the patch: {f['path']}")
        if not f.get("notes"):
            errs.append(f"file has no notes: {f['path']}")
        for n in f.get("notes", []):
            if not n.get("ids"):
                errs.append(f"note names no decision in {f['path']}: {n['text']!r}")
            for i in n.get("ids", []):
                if i not in ids:
                    errs.append(f"note names unknown decision {i} in {f['path']}")
                named.add(i)
    for i in ids:
        if i in no_code and i in named:
            errs.append(f"{i} is marked no_code but a note names it")
        if i not in no_code and i not in named:
            errs.append(f"{i} has no note: implement it, or mark it no_code")
    return errs


def build(spec, patched):
    anchors = {f["path"]: f"file-{n}" for n, f in enumerate(spec["files"], 1)}

    rows = []
    for d in spec["decisions"]:
        if d.get("no_code"):
            where = "<em>no code</em>"
        else:
            paths = [f["path"] for f in spec["files"] if any(d["id"] in n["ids"] for n in f["notes"])]
            where = ", ".join(f'<a href="#{anchors[p]}">{html.escape(os.path.basename(p))}</a>' for p in paths)
        rows.append(f"<tr><td>{html.escape(d['id'])}</td><td>{text(d['title'])}</td>"
                    f"<td>{text(d['answer'])}</td><td>{text(d['why'])}</td><td>{where}</td></tr>")

    def mermaid(src):
        return f'<pre class="mermaid">{html.escape(src.strip(), quote=False)}</pre>'

    diagrams = [f'<figure class="pair"><figcaption>{text(g["caption"])}</figcaption>'
                f'<div><h4>Before</h4>{mermaid(g["before"])}</div>'
                f'<div><h4>After</h4>{mermaid(g["after"])}</div></figure>'
                for g in spec.get("diagrams", [])]
    if not diagrams:
        diagrams = ["<p><em>No structural change to diagram.</em></p>"]

    sections = []
    for f in spec["files"]:
        notes = "".join(f'<li><span class="q">{html.escape(" ".join(n["ids"]))}</span> {text(n["text"])}</li>'
                        for n in f["notes"])
        body = patched[f["path"]].replace("</script", "<\\/script")
        sections.append(f'<section class="file" id="{anchors[f["path"]]}"><h3>{html.escape(f["path"])}</h3>'
                        f'<ul class="notes">{notes}</ul>'
                        f'<script type="text/x-diff">{body}</script><div class="diff"></div></section>')

    checks = []
    for v in spec.get("verification", []):
        note = f": {text(v['note'])}" if v.get("note") else ""
        state = "pass" if v["pass"] else "fail"
        checks.append(f'<li class="{state}"><code>{html.escape(v["cmd"])}</code> {state}{note}</li>')

    def items(xs):
        return "".join(f"<li>{text(x)}</li>" for x in xs) or "<li><em>None</em></li>"

    return {
        "TITLE": html.escape(spec["title"]),
        "REPO": text(spec.get("repo", "")),
        "DATE": html.escape(spec.get("date", "")),
        "SUMMARY": text(spec["summary"]),
        "DECISIONS": "\n".join(rows),
        "DIAGRAMS": "\n".join(diagrams),
        "CHANGES": "\n".join(sections),
        "VERIFICATION": "\n".join(checks) or "<li><em>Nothing run</em></li>",
        "OUT_OF_SCOPE": items(spec.get("out_of_scope", [])),
        "OPEN_QUESTIONS": items(spec.get("open_questions", [])),
        "APPLY": html.escape(spec.get("apply", "")),
    }


def main():
    ap = argparse.ArgumentParser(description="Fill the grill-review template.")
    ap.add_argument("spec")
    ap.add_argument("patch")
    ap.add_argument("-o", "--out")
    a = ap.parse_args()

    with open(a.spec) as fh:
        spec = json.load(fh)
    with open(a.patch) as fh:
        patched = split_patch(fh.read())

    errs = check(spec, patched)
    if errs:
        print("trace check failed:", *errs, sep="\n  ", file=sys.stderr)
        sys.exit(1)

    with open(TEMPLATE) as fh:
        doc = fh.read()
    for k, v in build(spec, patched).items():
        doc = doc.replace("{{" + k + "}}", v)
    left = re.findall(r"\{\{[A-Z_]+\}\}", doc)
    if left:
        sys.exit(f"unfilled slots: {left}")

    out = a.out or os.path.join(os.path.dirname(os.path.abspath(a.spec)), "review.html")
    with open(out, "w") as fh:
        fh.write(doc)
    print(out)


if __name__ == "__main__":
    main()
