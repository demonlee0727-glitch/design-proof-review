# Design Proof Review · 设计改稿批注核对

[中文](README.md) · [Acceptance guide](references/acceptance.md) · [Worked report](examples/report.en.md)

An Agent Skill for brand, packaging, editorial and e-commerce designers. Give it the **marked-up original PDF** and the **revised PDF**. It builds an evidence list for each client comment, including missed edits, moved content and decisions that still need a reviewer.

> The client asked for every 8 oz label to become 10 oz. The cover and order form were updated. The fill-mark caption still says 8 oz on revised page 6. It used to be on page 5.

You can verify that result yourself using the [marked-up original](examples/original.pdf), [revision](examples/revised.pdf) and [English report](examples/report.en.md). The product and comments are fictional.

[Read the full handoff: two fixes and two reviewer decisions](examples/handoff.md)

## Install and run

Choose a supported client using the Agent Skills installer:

~~~sh
npx skills add https://github.com/demonlee0727-glitch/design-proof-review --skill design-proof-review
~~~

Alternatively, download the repository and import the directory containing `SKILL.md`. To run the included tool, open a terminal in that directory and use Python 3.10 or later. The CLI processes both PDFs locally and requires no API key. Check the host AI client's configuration if you also provide it with private client files.

~~~sh
python -m venv .venv
# macOS / Linux
source .venv/bin/activate
# Windows PowerShell: .\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python scripts/review.py examples/original.pdf examples/revised.pdf --lang en --out review-demo
~~~

Open `review-demo/review.md` or use `review-demo/review.json` for downstream processing. Choose a fresh directory per run. For a parallel Chinese report, run the same command with `--lang zh --out review-demo-zh`. IDs remain stable for the same original PDF.

## Useful requests

- “Review these proofs. Show the pages that still need edits first, then list every comment and its evidence.”
- “The model number appears on the cover, specifications table and back panel. Verify each placement and return Chinese and English reports using identical IDs.”
- “The client asked for a proportionate logo and more bottom margin. Use the approved logo I attached, inspect both renders and flag anything that needs an acceptance threshold.”
- “The client also sent feedback in email.” Transcribe it into a UTF-8 CSV with `page,comment` headers and physical, one-based original page numbers. See [example CSV](examples/feedback.csv).

~~~sh
python scripts/review.py old.pdf new.pdf --comments feedback.csv --lang en --out review-with-comments
~~~

## How the review works

1. **Collect the markups.** Keep native notes, highlights, strikeouts and drawing annotations with their original page, type, text, rectangle and thread links. Empty highlights remain visible in the inventory. Flattened drawings require visual inspection or an external comment export.
2. **Split each instruction.** Turn compound feedback into checkable child items. Preserve the parent ID, scope, original wording and any explicit withdrawal.
3. **Match evidence across pages.** For scoped replacements the CLI uses the full original line to locate revised text. Repeated or reflowed lines, a bare value, a target line that already existed, and conflicting instructions are marked for review.
4. **Inspect the design.** Use the host's rendering tools for image text, cropping, logos and layout. Describe subjective differences and identify who needs to approve them. The CLI supplies a text-layer pass; the [acceptance guide](references/acceptance.md) covers visual checks.
5. **Hand off the results.** Group text matches, partial applications, retained source text and items requiring review. Include old and new physical page numbers and short excerpts.

## Worked example

| Client request | Outcome | Where to check |
| --- | --- | --- |
| Replace 8 oz everywhere | Partially applied | Original pp. 1, 3, 5. Revised pp. 1 and 3 are fixed; p. 6 retains 8 oz. |
| Change M-02 to M-03 | Text evidence matches | Original p. 2 → revised p. 4 |
| Change USD 45 to USD 49 | Original text remains | The price line on revised p. 3 still reads USD 45. |
| Make the heading feel more premium | Review needed | Note on original p. 4; inspect the render and confirm the aesthetic criterion. |
| Unlabelled highlight | Review needed | Original p. 5; use the rectangle in the JSON to locate the mark. |
| Change service cutoff to 31 July | Text evidence matches | Original p. 6 → revised p. 7 |

## Repeatable text instructions

Free-form feedback is retained for an agent or human to interpret. The deterministic checker also recognizes these complete, scoped instructions:

~~~text
ALL: "8 oz" -> "10 oz"
PAGE: "M-02" -> "M-03"
Replace all "USD 45" with "USD 49"
请把所有 8 oz 改成 10 oz
全稿：“8 oz”改为“10 oz”
本页：“M-02”改为“M-03”
将所有“USD 45”改为“USD 49”
~~~

PAGE targets a uniquely matchable original-page context and follows it when moved. A whole-document match covers extractable text. Image text, outlines, clipped text and overlaid artwork require render inspection. All quoted client comments stay in their original language.

## Coverage and testing

The inputs are PDFs and optional CSV feedback. Export Figma, Illustrator or InDesign source artwork first. Password-protected documents require an accessible copy. No native annotations triggers a coverage notice. A revised file may contain a text layer even if captions embedded inside images remain invisible to text extraction. Record final client approval separately.

~~~sh
python -m unittest discover -s tests -v
~~~

[Skill entry point](SKILL.md) · [中文版](README.md) · [Chinese report](examples/report.zh.md)
