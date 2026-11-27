# 设计改稿批注核对 · Design Proof Review

[English](README.en.md) · [核对规则](references/acceptance.md) · [查看中文示例报告](examples/report.zh.md)

给品牌、电商、包装及出版设计师的改稿验收 Skill。输入**带批注的旧 PDF** 和**修订后的新 PDF**，逐条追踪客户要求，列出漏改位置、已找到的修改证据，以及仍需设计师或客户确认的意见。

> 客户要求把全稿的 8 oz 改成 10 oz。新版封面和订购页改对了，第 6 页的注水图注仍写着 8 oz。图注在旧稿第 5 页，修订时插入了一页。

这是仓库自带样例的实际结果。可以直接打开[带批注的旧稿](examples/original.pdf)、[修订后的新稿](examples/revised.pdf)和[逐条验收单](examples/report.zh.md)对照。样例是虚构产品资料。

[看完整交付单：两处返工、两项待确认](examples/handoff.md)

## 快速开始

在支持 Agent Skills 的客户端选择安装目标：

~~~sh
npx skills add https://github.com/demonlee0727-glitch/design-proof-review --skill design-proof-review
~~~

也可下载仓库，将含 `SKILL.md` 的整个目录导入客户端。若要运行附带工具，请在该目录中用 Python 3.10+ 创建虚拟环境、激活后安装依赖。PDF 核对命令在本机运行，不需要 API 密钥。宿主 AI 客户端的文件处理方式取决于其配置。

~~~sh
python -m venv .venv
# macOS / Linux
source .venv/bin/activate
# Windows PowerShell 可使用 .\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python scripts/review.py examples/original.pdf examples/revised.pdf --out review-demo --lang zh
~~~

打开 `review-demo/review.md` 阅读，或用 `review-demo/review.json` 衔接内部审稿表。每次运行选择一个新的输出目录。需要双语交付时，再用 `--lang en --out review-demo-en` 运行一次，两份报告的批注编号一致。

## 如何向助手提问

- **交付前核对。** “用设计改稿批注核对逐条验收这两版。先给我要返工的页码，再列全部批注、证据和待确认项。”
- **客户发来多处修改。** “同一型号出现在封面、规格表和背面示意图。按位置分别说明，给每处新页码，用中英文各出一份。”
- **版式意见。** “客户要求品牌标志保持原比例、底部留白加大。我附了批准的 Logo，请渲染新旧 PDF 看实际版面。没有明确数值的地方写出观察和需要确认的问题。”
- **意见不在 PDF 中。** 将邮件或 Figma 评论转写为 UTF-8 CSV，可参照[补充意见](examples/feedback.csv)。页码对应旧稿；CSV 作为补充来源与原生批注一并保留。

~~~sh
python scripts/review.py old.pdf new.pdf --comments feedback.csv --lang zh --out review-with-comments
~~~

## 核对方法

1. **盘点批注。** 提取原生便签、高亮、删除线、图形标记等，保存页码、类型、原文、矩形及回复关系。无文字的高亮也占一条记录。压平到画面的手写意见需要查看页面或补充导出文件。
2. **拆分要求。** 文字、删除、图片、尺寸、版式、审美或审批要求分别验收。复合意见可在助手的交付单里拆成 A/B/C，保留父批注编号。
3. **跨页找证据。** 对明确的文字替换，工具用旧稿中的整行上下文在新稿重定位。重复行、只有一个孤立数值、断行、原稿已有相同目标行或同一目标的相互冲突指令，会触发复核。
4. **核对可见版面。** 脚本先产生文字证据。助手可结合宿主支持的渲染能力检查图片中的文案、遮挡、裁切、印刷页码和位置。纯视觉意见及客户偏好保留确认人。
5. **交接结果。** 汇总文字证据相符、部分落实、原文仍在、需复核四类，在每条下标注旧页、新页、原文与改后文字。详细方法见[判定手册](references/acceptance.md)。

## 样例包含什么

| 批注 | 预期结果 | 可验证的位置 |
| --- | --- | --- |
| 全稿容量改为 10 oz | 部分落实 | 旧稿第 1、3、5 页；新版第 1、3 页已改，第 6 页仍为 8 oz |
| 型号 M-02 改为 M-03 | 文字证据相符 | 旧第 2 页 → 新第 4 页 |
| 零售价 USD 45 改为 USD 49 | 原文仍在 | 新第 3 页订购区仍为 USD 45 |
| 标题更有高级感 | 需复核 | 旧第 4 页的便签；需看实际效果并确认审美要求 |
| 只有高亮，没有文字 | 需复核 | 旧第 5 页；原始矩形保存在 JSON 中 |
| 服务截止日改为 31 July | 文字证据相符 | 旧第 6 页 → 新第 7 页 |

## 文字指令与范围

普通自然语言批注可以直接保留给助手审阅。以下格式还可用脚本重复核算。引号内保留原有数字、标点、大小写与单位。

~~~text
全稿：“8 oz”改为“10 oz”
本页：“M-02”改为“M-03”
将所有“USD 45”改为“USD 49”
ALL: "8 oz" -> "10 oz"
PAGE: "M-02" -> "M-03"
Replace all "USD 45" with "USD 49"
请把所有 8 oz 改成 10 oz
~~~

`本页` 指批注所在旧页上的唯一上下文，允许其移到新页。全稿指令覆盖所有可提取的匹配行；照片内文字和转曲文字需另看渲染。两种语言都保留原始客户引文。

## 运行条件与测试

缺少文字层、已压平的批注、无密码无法打开的稿件、图中字符或无法唯一配对的片段，会影响核验。无可读批注时，报告会明确给出补充材料提示。工具处理的是 PDF 和可选 CSV；Figma、InDesign 或 Illustrator 稿件请导出对应 PDF 后使用。客户批准与否仍由交付方记录。

~~~sh
python -m unittest discover -s tests -v
~~~

[技能入口](SKILL.md) · [英文说明](README.en.md) · [英文样例报告](examples/report.en.md)
