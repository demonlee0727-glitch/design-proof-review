import csv
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from pypdf import PdfWriter
from pypdf.generic import DictionaryObject, NameObject, TextStringObject, ArrayObject, FloatObject

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import review

EX = ROOT / "examples"


def evaluate(old, revised, body='ALL: "8 oz" -> "10 oz"', page=1, sparse=False):
    def lines(pages):
        return [{"page": pg, "line": ix, "text": value}
                for pg, part in enumerate(pages, 1) for ix, value in enumerate(part, 1)]
    data = {"id": "probe", "page": page, "comment": body, "related": []}
    before, after = lines(old), lines(revised)
    return review.decide(data, review.rule_for(data), before, review.index_lines(before),
                         review.index_lines(after), sparse, False)


class MatchingTests(unittest.TestCase):
    def test_cross_page(self):
        row = evaluate([["Cup: 8 oz"]], [["A new page"], ["Cup: 10 oz"]])
        self.assertEqual(row["status"], "text_match")
        self.assertEqual(row["evidence"][0]["new"][0]["page"], 2)

    def test_partial(self):
        row = evaluate([["Cup: 8 oz", "Fill: 8 oz"]], [["Cup: 10 oz", "Fill: 8 oz"]])
        self.assertEqual(row["status"], "partial")

    def test_existing_correct_text_cannot_prove_edit(self):
        row = evaluate([["Cup: 8 oz", "Cup: 10 oz"]], [["Cup: 10 oz"]])
        self.assertEqual(row["status"], "review")

    def test_duplicate_context(self):
        row = evaluate([["Cup: 8 oz"], ["Cup: 8 oz"]], [["Cup: 10 oz"], ["Cup: 10 oz"]])
        self.assertEqual(row["status"], "review")

    def test_unexpected_remaining_old_text(self):
        row = evaluate([["Cup: 8 oz"]], [["Cup: 10 oz", "New sticker: 8 oz"]])
        self.assertEqual(row["status"], "review")
        self.assertEqual(row["residual"][0]["line"], 2)

    def test_reflow_and_missing_module(self):
        for revised in [[["Cup:", "10 oz"]], [["Some other page"]]]:
            with self.subTest(revised=revised):
                self.assertEqual(evaluate([["Cup: 8 oz"]], revised)["status"], "review")

    def test_bare_replaced_token(self):
        self.assertEqual(evaluate([["8 oz"]], [["10 oz"]])["status"], "review")

    def test_ocr_gap(self):
        self.assertEqual(evaluate([["Cup: 8 oz"]], [["Cup: 10 oz"]], sparse=True)["reason"], "sparse")

    def test_local_scope(self):
        row = evaluate([["Cup: 8 oz"], ["Fill: 8 oz"]], [["Fill: 8 oz"], ["Cup: 10 oz"]],
                       body='本页：“8 oz”改为“10 oz”')
        self.assertEqual(row["status"], "text_match")
        row = evaluate([["Cup: 8 oz", "Fill: 8 oz"]], [["Cup: 10 oz", "Fill: 10 oz"]],
                       body='PAGE: "8 oz" -> "10 oz"')
        self.assertEqual(row["reason"], "scope")

    def test_number_boundaries(self):
        for text in ["Size: 18 oz", "Size: 1.8 oz", "Size: 1,8 oz", "Size: 8 ozx"]:
            self.assertEqual(evaluate([[text]], [[text]])["reason"], "scope")

    def test_languages_and_natural_instructions(self):
        for txt in ['请把所有 8 oz 改成 10 oz', 'Replace all 8 oz with 10 oz.', '将所有“8 oz”改为“10 oz”', 'Replace all instances of "8 oz" with "10 oz".',
                    '全稿：“8 oz”改成“10 oz”。']:
            self.assertEqual(evaluate([["Cup: 8 oz"]], [["Cup: 10 oz"]], txt)["status"], "text_match")
        for txt in ['改高级一点', 'ALL: "8 oz" -> "10 oz" except the back cover']:
            self.assertEqual(evaluate([["Cup: 8 oz"]], [["Cup: 10 oz"]], txt)["reason"], "manual")


class PDFTests(unittest.TestCase):
    def test_real_fixtures_and_both_reports(self):
        result = review.analyze(EX / "original.pdf", EX / "revised.pdf")
        self.assertEqual(result["counts"], {"partial": 1, "text_match": 2, "unchanged": 1, "review": 2})
        for language in ["zh", "en"]:
            self.assertEqual(review.report(result, language), (EX / f"report.{language}.md").read_text(encoding="utf-8"))
        self.assertEqual(result["items"][4]["type"], "Highlight")
        self.assertEqual(len(result["items"][4]["rect"]), 4)

    def test_thread_evidence(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "reply.pdf"
            writer = PdfWriter(clone_from=EX / "original.pdf")
            refs = writer.pages[0]["/Annots"]
            rect = ArrayObject([FloatObject(v) for v in [35, 40, 51, 56]])
            reply = DictionaryObject({NameObject("/Subtype"): NameObject("/Text"),
                                      NameObject("/Rect"): rect, NameObject("/IRT"): refs[0],
                                      NameObject("/Contents"): TextStringObject("Hold this change.")})
            writer.add_annotation(0, reply)
            writer.write(source)
            out = review.analyze(source, EX / "revised.pdf")
            self.assertEqual(out["items"][0]["reason"], "thread")
            self.assertEqual(out["items"][1]["related"], [out["items"][0]["id"]])

    def test_append_csv_conflict_and_invalid_page(self):
        with tempfile.TemporaryDirectory() as folder:
            sidecar = Path(folder) / "comments.csv"
            with sidecar.open("w", encoding="utf-8-sig", newline="") as f:
                w = csv.writer(f)
                w.writerows([["page","comment"],[1,'ALL: "8 oz" -> "12 oz"']])
            out = review.analyze(EX / "original.pdf", EX / "revised.pdf", sidecar)
            self.assertEqual((out["items"][0]["reason"], out["items"][-1]["reason"]), ("conflict", "conflict"))
            sidecar.write_text("page,comment\n99,hello", encoding="utf-8")
            with self.assertRaises(ValueError):
                review.read_comments(sidecar, 6)

    def test_no_annotations(self):
        result = review.analyze(EX / "revised.pdf", EX / "revised.pdf")
        self.assertEqual(result["items"], [])
        self.assertIn("No review comments found", review.report(result, "en"))

    def test_protected_pdf_reports_error(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "locked.pdf"
            w = PdfWriter()
            w.add_blank_page(110, 200)
            w.encrypt("example-password")
            w.write(target)
            with self.assertRaises(ValueError):
                review.analyze(target, EX / "revised.pdf")

    def test_cli_writes_pair_and_preserves_existing_report(self):
        with tempfile.TemporaryDirectory() as folder:
            dest = Path(folder) / "review"
            cmd = [sys.executable, str(ROOT / "scripts/review.py"), str(EX / "original.pdf"),
                   str(EX / "revised.pdf"), "--comments", str(EX / "feedback.csv"), "--out", str(dest), "--lang", "en"]
            first = subprocess.run(cmd, capture_output=True, text=True)
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertEqual(len(json.loads((dest / "review.json").read_text())["items"]), 7)
            self.assertEqual(subprocess.run(cmd, capture_output=True).returncode, 2)


if __name__ == "__main__":
    unittest.main()
