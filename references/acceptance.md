# 判定手册 · Acceptance guide

## 一次交付怎么核对 · Review procedure

| 检查对象 / Item | 可复查依据 / Evidence to collect |
| --- | --- |
| 数字、价格、单位 / Numbers and units | 核对数值、单位、币种、适用 SKU 与市场。旧稿已有一个正确值时也要定位本次目标行。 / Check the number together with its unit, currency, SKU and locale. A correct value elsewhere may predate the revision. |
| 全文替换 / Replace everywhere | 列出每个旧位置，逐处映射新页。单独列未能配对处和新增模块内的旧词。 / Map every original context and inspect new modules for unexpected remnants. |
| 局部修改 / One placement | 使用页面、表头、段落标题或图注确认对象。全局搜索只用于找候选。 / Match the requested placement with its label or caption; global search locates candidates. |
| 删除 / Removal | 原稿记录目标及相邻内容，新稿定位同一模块，渲染核实删除后间距及阅读顺序。有新空白页时标记。 / Locate the equivalent surviving module and inspect spacing and reading order; flag new blank pages. |
| 版式、图片与品牌 / Layout, photos and logos | 给出旧/新页及区域、可观察差异。若要求替换为指定 Logo 或产品图，取得批准的参考资产，核对形状、方向、裁切及是否还有旧标。 / Use an approved reference when specified. Compare shape, orientation, crop and residual occurrences. |
| 颜色与尺寸 / Colour and dimensions | 先确认参照与单位。图像预览只能支持视觉观察；检测印刷专色、精确尺寸或字体需能读取对象数据的工具。 / When a precise specification matters, inspect the object's units, font or colour data; a screen preview supports visual observations only. |
| 意见冲突 / Conflicting feedback | 并列编号、作者或来源（如有）、时间和原话；有明确撤回/取代关系才关闭旧项。 / Report both instructions and their provenance. Require explicit supersession or a decision. |
| 被压平的批注 / Flattened markup | 无原生批注时视觉检查旧稿，或取得原批注导出。扫描手写意见识别后保留原图位置；转写不清处请复核。 / Inspect visible markup or obtain an export, retain physical page and region, and flag uncertain transcription. |
| 图像中的文字 / Text in images | 文字层只覆盖可提取部分。一页有页脚文字并不证明照片、条码旁或嵌入图内的文字可提取。 / A selectable footer does not establish coverage of text embedded in an image. |

## 自动判定 · What each script status means

| JSON 值 | 中文 / English | 何时采用 / Decision rule |
| --- | --- | --- |
| `text_match` | 文字证据相符 / Text evidence matches | 匹配的旧行有唯一上下文，旧稿中没有该预期新行，新稿能逐一定位替换后的行。需另看渲染。 / All original contexts uniquely match expected revised lines. Render checks remain separate. |
| `partial` | 部分落实 / Partially applied | 同一请求的目标行中既有已替换行，也有完整保留的旧行。 / Some original contexts were changed and others remain. |
| `unchanged` | 原文仍在 / Original text remains | 在对应上下文中仍找到所有原行。 / Original text remains in every matchable target context. |
| `review` | 需复核 / Review needed | 证据不足、非规则化指令、重复上下文、额外旧词、空标记或视觉意见等。 / Evidence is incomplete, ambiguous, visual, or requires interpreting the instruction. |

综合报告可再使用“已落实（已看渲染）”“未落实”“待客户确认”“已撤回（附依据）”。原始机器结果保留在 JSON 中。复合项含未完成子项时，父项不能整条通过。

A reviewer may additionally record visually verified, outstanding, client decision required, or withdrawn with evidence. Preserve the machine report as evidence. A compound request with an outstanding child remains open.

## 报告交接 · Evidence handoff

每一行引用物理页、对象或区域及短引；提取文本的“行号”是脚本内部的定位线索，不是印刷品上的行号。JSON 保存源文件 SHA-256、批注矩形（PDF 原始坐标）、关联 ID、新旧上下文及候选行。矩形用于回查旧稿，跨版旋转、裁切和重排时不能将原坐标直接搬到新页。仅给客户需要的证据，避免外发内部批注和私密文件。

Cite physical page, region or label and a short excerpt. Extracted line numbers are navigation hints. JSON stores the two PDF fingerprints, original markup rectangles in PDF coordinates, thread IDs and candidate text contexts. Re-anchor on rotated, cropped or reflowed pages. Share only the evidence intended for the recipient.

**示例 / Example**

| ID | 原意 / Request | 旧页 → 新页 / Pages | 证据 / Evidence | 下一步 / Next action |
| --- | --- | --- | --- | --- |
| P1-A1 | 全稿 8 oz → 10 oz | 1→1、3→3、5→6 | 封面及订购页均为 10 oz；新第 6 页 Fill mark 仍为 8 oz。 / Cover and order page fixed; fill caption still says 8 oz. | 修正第 6 页图注后再导出。 / Correct the caption and re-export. |
