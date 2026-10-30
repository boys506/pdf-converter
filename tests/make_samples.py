"""生成测试样本并跑一遍转换，验证各类文件。"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import shutil

from PIL import Image, ImageDraw

BASE = os.path.dirname(os.path.abspath(__file__))
SAMPLES = os.path.join(BASE, "samples")
OUT = os.path.join(BASE, "out")
shutil.rmtree(SAMPLES, ignore_errors=True)
shutil.rmtree(OUT, ignore_errors=True)
os.makedirs(SAMPLES, exist_ok=True)
os.makedirs(OUT, exist_ok=True)

# 1. 图片
img = Image.new("RGB", (1200, 800), (255, 255, 255))
d = ImageDraw.Draw(img)
for i in range(0, 1200, 40):
    d.line([(i, 0), (i, 800)], fill=(235, 240, 250), width=1)
d.rectangle([80, 80, 1120, 720], outline=(47, 107, 255), width=6)
d.ellipse([400, 250, 800, 550], fill=(47, 107, 255))
img.save(os.path.join(SAMPLES, "sample.png"))
img.convert("RGBA").save(os.path.join(SAMPLES, "sample_transparent.png"))

# 2. Word
from docx import Document
from docx.shared import Pt

doc = Document()
doc.add_heading("项目结题报告", 0)
doc.add_heading("一、项目概述", level=1)
doc.add_paragraph("本项目围绕“多格式文档一键转 PDF”展开，目标是让非技术同事也能在三步内完成批量转换。")
p = doc.add_paragraph()
p.add_run("核心指标：").bold = True
p.add_run("转换成功率 ≥ 99%，中文零乱码，单文件耗时 < 2 秒。")
doc.add_heading("二、功能清单", level=2)
for item in ["图片批量转 PDF", "Word 排版还原", "Excel 表格横版输出", "多文件合并"]:
    doc.add_paragraph(item, style="List Bullet")
doc.add_heading("三、数据对比", level=2)
t = doc.add_table(rows=4, cols=3)
t.style = "Table Grid"
data = [["格式", "样本数", "成功率"], ["DOCX", "120", "100%"], ["XLSX", "86", "99.2%"], ["图片", "340", "100%"]]
for r, row in enumerate(data):
    for c, val in enumerate(row):
        t.cell(r, c).text = val
doc.add_paragraph("结论：整体表现达到预期，后续可增加 PPT 支持。")
doc.save(os.path.join(SAMPLES, "sample.docx"))

# 3. Excel
from openpyxl import Workbook

wb = Workbook()
ws = wb.active
ws.title = "销售明细"
ws.append(["月份", "区域", "销售额（元）", "同比增长", "负责人"])
rows = [
    ["1月", "华东", 128900.5, "12.4%", "张伟"],
    ["2月", "华南", 98750, "-3.1%", "李娜"],
    ["3月", "华北", 154300.75, "18.9%", "王强"],
    ["4月", "西南", 76210, "5.2%", "赵敏"],
]
for r in rows:
    ws.append(r)
ws2 = wb.create_sheet("汇总")
ws2.append(["区域", "合计"])
ws2.append(["华东", 128900.5])
ws2.append(["华南", 98750])
wb.save(os.path.join(SAMPLES, "sample.xlsx"))

# 4. Markdown
md = """# 使用说明

这是一个 **Markdown** 测试文档，用来验证中文排版、`行内代码` 与表格。

## 支持的能力

- 标题层级（1~6 级）
- **加粗**、*斜体*、~~删除线~~
- 有序列表
1. 第一步：添加文件
2. 第二步：选择输出目录
3. 第三步：点击开始转换

> 引用块：转换全程在本地完成，不上传任何文件。

### 代码示例

```python
def convert(src, dst):
    return engine.convert_one(src, dst, opts)
```

### 表格

| 格式 | 扩展名 | 说明 |
| --- | --- | --- |
| 图片 | jpg/png/webp | 每张一页，等比缩放 |
| Word | docx | 保留标题与表格 |
| Excel | xlsx | 自动横版 |

---

结尾段落，用于验证分隔线与页脚页码。
"""
open(os.path.join(SAMPLES, "sample.md"), "w", encoding="utf-8").write(md)

# 5. HTML
html = """<!DOCTYPE html><html><head><meta charset="utf-8"><title>网页测试</title>
<style>body{font-family:sans-serif}</style></head><body>
<h1>网页转 PDF 测试</h1>
<p>这段文字来自 <b>HTML</b> 文件，包含 <i>斜体</i> 与 <u>下划线</u>。</p>
<h2>列表</h2>
<ul><li>第一项内容</li><li>第二项内容</li></ul>
<ol><li>编号一</li><li>编号二</li></ol>
<h2>表格</h2>
<table border="1"><tr><th>名称</th><th>数量</th></tr>
<tr><td>键盘</td><td>12</td></tr><tr><td>鼠标</td><td>30</td></tr></table>
<h2>代码</h2><pre>npm install reportlab
python main.py</pre>
<p><img src="sample.png" alt="示意图" width="400"></p>
</body></html>"""
open(os.path.join(SAMPLES, "sample.html"), "w", encoding="utf-8").write(html)

# 6. TXT（GBK 编码，测试编码识别）
txt = "纯文本测试\n\n这是一段用 GBK 编码保存的中文文本，用于验证编码自动识别。\n第二行内容：转换后应当正常显示，不出现乱码。\n\n结尾段落。\n"
open(os.path.join(SAMPLES, "sample_gbk.txt"), "wb").write(txt.encode("gbk"))

# ---- 跑转换
import engine
from utils import Options, SUPPORTED_EXTS

files = [os.path.join(SAMPLES, f) for f in sorted(os.listdir(SAMPLES)) if os.path.splitext(f)[1] in SUPPORTED_EXTS]
print("待转换：", [os.path.basename(f) for f in files])

ok, fail = 0, 0
for f in files:
    opts = Options(page_size="A4", orientation="auto", margin_mm=15, out_dir=OUT)
    dst = os.path.join(OUT, os.path.basename(f) + ".pdf")
    try:
        engine.convert_one(f, dst, opts)
        size = os.path.getsize(dst)
        print(f"  OK   {os.path.basename(f):28s} -> {os.path.basename(dst):28s} {size/1024:8.1f} KB")
        ok += 1
    except Exception as e:
        import traceback
        print(f"  FAIL {os.path.basename(f)}: {type(e).__name__}: {e}")
        traceback.print_exc()
        fail += 1

# ---- 合并
try:
    opts = Options(merge=True, page_size="A4", orientation="auto", margin_mm=15, out_dir=OUT)
    res = engine.run(files, opts)
    print("合并结果：", res, os.path.getsize(res[0]) / 1024, "KB")
except Exception as e:
    import traceback
    print("合并失败:", e)
    traceback.print_exc()

# ---- 校验文字
try:
    from pypdf import PdfReader

    for name in ("sample.docx.pdf", "sample.md.pdf", "sample.html.pdf", "sample_gbk.pdf", "sample.xlsx.pdf"):
        p = os.path.join(OUT, name)
        if not os.path.exists(p):
            continue
        r = PdfReader(p)
        text = (r.pages[0].extract_text() or "").replace("\n", " ")
        print(f"[{name}] 页数={len(r.pages)} 文本片段={text[:90]!r}")
except Exception as e:
    print("校验失败:", e)

print(f"\n成功 {ok} / 失败 {fail}")
