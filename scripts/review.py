#!/usr/bin/env python3
"""Local PDF proof review. Run with --help for usage."""
import argparse
import csv
import hashlib
import json
import re
import sys
import tempfile
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

from pypdf import PdfReader
from pypdf.errors import PdfReadError


LABELS = {
    "zh": {"title": "设计改稿批注核对", "text_match": "文字证据相符", "partial": "部分落实",
           "unchanged": "原文仍在", "review": "需复核", "baseline": "旧稿", "revision": "新稿",
           "position": "位置", "thread": "关联批注", "coverage": "覆盖范围", "empty": "无可提取文字的页",
           "none": "无", "no_notes": "未读到可核对的批注；请补充批注导出或带标记的原稿。",
           "scope": "以下结论限于可提取文字；交付前请核对实际渲染。", "other": "其他仍含旧文的位置",
           "found": "改后文字", "kept": "原文保留", "unclear": "不能唯一配对",
           "extract": "提取文本行", "source": "材料", "notes": "条批注"},
    "en": {"title": "Design proof review", "text_match": "Text evidence matches", "partial": "Partially applied",
           "unchanged": "Original text remains", "review": "Review needed", "baseline": "Original", "revision": "Revision",
           "position": "Location", "thread": "Related annotation", "coverage": "Coverage", "empty": "Pages with no extractable text",
           "none": "none", "no_notes": "No review comments found. Supply an annotation export or a marked-up original.",
           "scope": "Results cover extractable text. Inspect the rendered pages before sign-off.", "other": "Other remaining source text",
           "found": "Requested text", "kept": "Original retained", "unclear": "No unique match",
           "extract": "extracted line", "source": "Input", "notes": "comments"},
}
REASONS = {
    "manual": ("自然语言、空标记或视觉意见需要逐项解释。", "Interpret this free-form, empty, or visual markup."),
    "thread": ("关联批注可能补充或撤销原要求；请合并阅读。", "Read the entire thread for amendments or withdrawals."),
    "scope": ("旧稿未找到源文字，或单页请求指向多个位置。", "Source text is absent or a page-scoped instruction is ambiguous."),
    "sparse": ("文件有无文字层的页面，覆盖范围不完整。", "One or more pages lack extractable text; coverage is incomplete."),
    "ambiguous": ("上下文重复、换行、拆页、同时出现新旧行或存在未定位旧词；请复核。", "Repeated, reflowed, missing, or conflicting context needs review."),
    "all": ("旧稿中的每个唯一上下文都在新版找到相应替换。", "Each unique original context has a matching replacement."),
    "some": ("新版同时保留可定位的旧行与改后行。", "The revision contains both verified replacements and retained original lines."),
    "old": ("原位置的文字仍可定位，且未找到相应改后行。", "All matched original contexts remain without matching replacements."),
    "conflict": ("多个指令对同一源文字提出不同目标；先核实适用范围和最终意见。", "Overlapping instructions request different replacements; reconcile their scope first."),
}
# Unquoted requests are deliberately limited to compact numeric specifications.
SPEC = r"[0-9]+(?:[.,][0-9]+)?(?:\s*(?:ml|mL|L|oz|mm|cm|kg|g|%))?"
RULES = [
    re.compile(rf"(?:请)?(?:把|将)(?P<scope>全部|所有)(?:的)?\s*(?P<old>{SPEC})\s*(?:都)?(?:改为|改成|替换为)\s*(?P<new>{SPEC})[。.]?"),
    re.compile(rf"(?P<scope>Replace all)(?: instances of| occurrences of)?\s+(?P<old>{SPEC})\s+with\s+(?P<new>{SPEC})[.]?", re.I),
    re.compile(r'(?:请)?(?:把|将)(?P<scope>全部|所有)(?:的)?[“"](?P<old>[^“”"\n]+)[”"](?:都)?(?:改为|改成|替换为)[“"](?P<new>[^“”"\n]+)[”"][。.]?'),
    re.compile(r'(?P<scope>Replace all)(?: instances of| occurrences of)? ["“](?P<old>[^”"\n]+)["”] with ["“](?P<new>[^”"\n]+)["”][.]?', re.I),
    re.compile(r'(?P<scope>全稿|本页)\s*[：:]\s*[“"](?P<old>[^“”"\n]+)[”"]\s*(?:改为|改成|替换为)\s*[“"](?P<new>[^“”"\n]+)[”"][。.]?'),
    re.compile(r'(?P<scope>ALL|PAGE)\s*:\s*[“"](?P<old>[^“”"\n]+)[”"]\s*(?:->|→)\s*[“"](?P<new>[^“”"\n]+)[”"][.]?', re.I),
]
IGNORED = {"/Popup", "/Link", "/Widget", "/Movie", "/Sound", "/Screen", "/FileAttachment",
           "/3D", "/RichMedia", "/PrinterMark", "/TrapNet", "/Watermark"}


def norm(value):
    return " ".join(unicodedata.normalize("NFC", str(value)).split())


def read_pdf(path, include_notes=False):
    reader = PdfReader(path)
    if reader.is_encrypted and not reader.decrypt(""):
        raise ValueError(f"Password-protected PDF / 受密码保护：{path.name}")
    lines, notes, empty = [], [], []
    for page_num, page in enumerate(reader.pages, 1):
        page_lines = [norm(s) for s in (page.extract_text() or "").splitlines() if norm(s)]
        if not page_lines:
            empty.append(page_num)
        for row, line in enumerate(page_lines, 1):
            lines.append({"page": page_num, "line": row, "text": line})
        if not include_notes:
            continue
        refs = page.get("/Annots")
        for index, ref in enumerate(refs.get_object() if refs else [], 1):
            annot = ref.get_object()
            kind = str(annot.get("/Subtype", ""))
            if kind in IGNORED:
                continue
            content = str(annot.get("/Contents", "") or "").strip()
            if not content and annot.get("/RC"):
                content = str(annot["/RC"])
            parent = annot.get("/IRT")
            notes.append({"id": f"P{page_num}-A{index}", "page": page_num, "type": kind.lstrip("/"),
                          "comment": content, "rect": [float(x) for x in annot.get("/Rect", [])],
                          "object": getattr(ref, "idnum", None), "parent_object": getattr(parent, "idnum", None),
                          "related": [], "source": "pdf"})
    by_obj = {n["object"]: n for n in notes if n["object"] is not None}
    for note in notes:
        parent = by_obj.get(note["parent_object"])
        if parent:
            note["related"].append(parent["id"])
            parent["related"].append(note["id"])
    return lines, notes, {"file": path.name, "pages": len(reader.pages), "empty_pages": empty,
                          "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def read_comments(path, page_count):
    notes = []
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream, strict=True)
        if not {"page", "comment"} <= set(reader.fieldnames or []):
            raise ValueError("CSV headers required / 必需表头：page,comment")
        for row in reader:
            page = int(row["page"] or "")
            body = (row["comment"] or "").strip()
            if not 1 <= page <= page_count or not body:
                raise ValueError(f"Invalid page/comment / 页码或意见无效：CSV line {reader.line_num}")
            notes.append({"id": f"CSV-{reader.line_num}", "page": page, "comment": body, "type": "CSV",
                          "related": [], "source": "csv", "rect": []})
    return notes


def rule_for(note):
    for regex in RULES:
        match = regex.fullmatch(note["comment"].strip())
        if match:
            old, new = norm(match["old"]), norm(match["new"])
            if old and new and old != new:
                return ("all" if match["scope"].upper() in {"ALL", "全稿", "所有", "全部", "REPLACE ALL"} else "page", old, new)
    return None


def token_pattern(value):
    # Reject an ASCII word/number embedded in another token (8 oz vs 18 oz).
    left = r"(?<![A-Za-z0-9_])" if re.match(r"[A-Za-z0-9_]", value[0]) else ""
    right = r"(?![A-Za-z0-9_])" if re.match(r"[A-Za-z0-9_]", value[-1]) else ""
    if value[0].isascii() and value[0].isdigit():
        left += r"(?<![0-9][.,])"
    if value[-1].isascii() and value[-1].isdigit():
        right += r"(?![.,][0-9])"
    return re.compile(left + re.escape(value) + right)


def index_lines(lines):
    lookup = defaultdict(list)
    for row in lines:
        lookup[row["text"]].append(row)
    return lookup


def decide(note, rule, old_lines, old_index, new_index, sparse, conflict):
    result = dict(note, status="review", reason="manual", evidence=[], residual=[])
    if note.get("parent_object") is not None or note["related"]:
        return dict(result, reason="thread")
    if not rule:
        return result
    if conflict:
        return dict(result, reason="conflict")
    scope, old, new = rule
    pattern = token_pattern(old)
    targets = [r for r in old_lines if (scope == "all" or r["page"] == note["page"]) and pattern.search(r["text"])]
    if not targets or (scope == "page" and len(targets) != 1):
        return dict(result, reason="scope")
    counts = Counter()
    for row in targets:
        text = row["text"]
        expect = pattern.sub(lambda _: new, text)
        original, changed = new_index.get(text, []), new_index.get(expect, [])
        strong = (len(old_index[text]) == 1 and not old_index.get(expect)
                  and bool(pattern.sub("", text).strip(" .,;:!?，。；：！？-–—()（）")))
        state = "unclear"
        if strong and len(original) + len(changed) == 1:
            state = "found" if changed else "kept"
        result["evidence"].append({"old": row, "expected": expect, "state": state,
                                   "new": original + changed})
        counts[state] += 1
    if scope == "all":
        originals = {r["text"] for r in targets}
        result["residual"] = [r for text, rows in new_index.items()
                              if text not in originals and pattern.search(text) for r in rows]
    if sparse:
        return dict(result, reason="sparse")
    if counts["unclear"] or result["residual"]:
        return dict(result, reason="ambiguous")
    if counts["found"] == len(targets):
        return dict(result, status="text_match", reason="all")
    if not counts["found"]:
        return dict(result, status="unchanged", reason="old")
    return dict(result, status="partial", reason="some")


def analyze(original, revised, comments=None):
    old_rows, notes, before = read_pdf(original, include_notes=True)
    new_rows, _, after = read_pdf(revised)
    if comments:
        notes.extend(read_comments(comments, before["pages"]))
    rules = [rule_for(n) for n in notes]
    old_index, new_index = index_lines(old_rows), index_lines(new_rows)
    sparse = bool(before["empty_pages"] or after["empty_pages"])
    checked = []
    for note, rule in zip(notes, rules):
        conflict = rule and any(other and other[1] == rule[1] and other[2] != rule[2]
                                and ("all" in (rule[0], other[0]) or n["page"] == note["page"])
                                for n, other in zip(notes, rules))
        checked.append(decide(note, rule, old_rows, old_index, new_index, sparse, conflict))
    return {"schema_version": 1, "original": before, "revision": after,
            "counts": dict(Counter(n["status"] for n in checked)), "items": checked}


def safe(value):
    # PDF comments and filenames may contain Markdown, links or HTML.
    return re.sub(r"([\\`*_\[\]{}()#|!<>~])", r"\\\1", " ".join(str(value).splitlines()))


def report(data, lang):
    labels = LABELS[lang]
    def location(row):
        return f"p.{row['page']} · {labels['extract']} {row['line']} — {safe(row['text'])}"
    out = [f"# {labels['title']}", "", labels["scope"], ""]
    for key, label in [("original", "baseline"), ("revision", "revision")]:
        meta = data[key]
        out.append(f"- {labels[label]}: {safe(meta['file'])} ({meta['pages']} pp.) · "
                   f"{labels['empty']}: {', '.join(map(str, meta['empty_pages'])) or labels['none']}")
    out += ["", f"**{len(data['items'])} {labels['notes']}**", ""]
    for key in ["text_match", "partial", "unchanged", "review"]:
        out.append(f"- {labels[key]}: {data['counts'].get(key, 0)}")
    if not data["items"]:
        out += ["", labels["no_notes"]]
    for n in data["items"]:
        out += ["", f"## {n['id']} · {labels[n['status']]}", "",
                f"{labels['baseline']} p.{n['page']} ({safe(n['type'])})", "",
                "> " + (safe(n["comment"]) or "∅"), "", REASONS[n["reason"]][lang == "en"]]
        if n["related"]:
            out += ["", labels["thread"] + ": " + ", ".join(n["related"])]
        for ev in n["evidence"]:
            out += ["", f"- {labels['baseline']}: {location(ev['old'])}", f"  - {labels[ev['state']]}"]
            for row in ev["new"]:
                out.append(f"  - {labels['revision']}: {location(row)}")
        for row in n["residual"]:
            out.append(f"- {labels['other']}: {location(row)}")
    return "\n".join(out) + "\n"


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("original", type=Path, help="Marked-up original PDF / 带批注旧稿")
    p.add_argument("revised", type=Path, help="Revised PDF / 新稿")
    p.add_argument("--comments", type=Path, help="Additional UTF-8 CSV (page,comment) / 补充意见")
    p.add_argument("--out", required=True, type=Path, help="New output folder / 新报告目录")
    p.add_argument("--lang", choices=LABELS, default="zh", help="Markdown language / 报告语言")
    args = p.parse_args()
    try:
        if args.out.exists():
            raise ValueError("Use a new output directory / 请使用新的报告目录")
        data = analyze(args.original, args.revised, args.comments)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=args.out.parent) as tmp:
            stage = Path(tmp) / "report"
            stage.mkdir()
            (stage / "review.md").write_text(report(data, args.lang), encoding="utf-8")
            (stage / "review.json").write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            stage.rename(args.out)
    except (OSError, ValueError, csv.Error, PdfReadError) as exc:
        p.exit(2, f"Error / 错误: {exc}\n")
    print(args.out / "review.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
