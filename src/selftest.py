"""打包后自检：在隔离环境中跑一遍真实转换，验证依赖是否齐全。"""
from __future__ import annotations

import os
import shutil
import tempfile
import traceback


def run() -> str:
    lines: list[str] = []
    import sys

    base = (
        os.path.dirname(sys.executable)
        if getattr(sys, "frozen", False)
        else os.path.dirname(os.path.abspath(__file__))
    )
    # 不依赖系统临时目录（受限环境可能不可写）
    tmp = tempfile.mkdtemp(prefix=".selftest_", dir=base)
    try:
        from docx import Document
        from openpyxl import Workbook
        from PIL import Image, ImageDraw

        # 造样本
        img = Image.new("RGB", (600, 400), (255, 255, 255))
        ImageDraw.Draw(img).ellipse([100, 100, 500, 300], fill=(47, 107, 255))
        png = os.path.join(tmp, "a.png")
        img.save(png)

        doc = Document()
        doc.add_heading("自检文档", 0)
        doc.add_paragraph("中文段落，用于验证字体嵌入是否正常。")
        t = doc.add_table(rows=2, cols=2)
        t.cell(0, 0).text = "项目"
        t.cell(0, 1).text = "结果"
        t.cell(1, 0).text = "转换"
        t.cell(1, 1).text = "成功"
        docx_path = os.path.join(tmp, "b.docx")
        doc.save(docx_path)

        wb = Workbook()
        ws = wb.active
        ws.append(["名称", "数值"])
        ws.append(["测试", 123.45])
        xlsx_path = os.path.join(tmp, "c.xlsx")
        wb.save(xlsx_path)

        md_path = os.path.join(tmp, "d.md")
        with open(md_path, "w", encoding="utf-8") as f:
            f.write("# 标题\n\n- 列表项\n\n| A | B |\n| --- | --- |\n| 1 | 2 |\n")

        html_path = os.path.join(tmp, "e.html")
        with open(html_path, "w", encoding="utf-8") as f:
            f.write("<html><body><h1>网页</h1><p>中文段落</p></body></html>")

        txt_path = os.path.join(tmp, "f.txt")
        with open(txt_path, "wb") as f:
            f.write("纯文本中文测试".encode("gbk"))

        import engine
        from utils import Options

        opts = Options(page_size="A4", orientation="auto", margin_mm=15, out_dir=tmp)
        for src in (png, docx_path, xlsx_path, md_path, html_path, txt_path):
            dst = os.path.join(tmp, os.path.basename(src) + ".pdf")
            try:
                engine.convert_one(src, dst, opts)
                size = os.path.getsize(dst)
                lines.append(f"OK   {os.path.basename(src):12s} {size / 1024:8.1f} KB")
            except Exception:
                lines.append(f"FAIL {os.path.basename(src)}\n{traceback.format_exc()}")

        try:
            merged = engine.run([png, docx_path, md_path], Options(merge=True, out_dir=tmp))
            lines.append(f"OK   合并 {os.path.basename(merged[0])} {os.path.getsize(merged[0]) / 1024:.1f} KB")
        except Exception:
            lines.append(f"FAIL 合并\n{traceback.format_exc()}")

        try:
            from fonts import ensure_fonts

            fo = ensure_fonts()
            lines.append(f"字体：正文={fo.cjk} 粗体={fo.bold} 等宽={fo.mono}")
        except Exception:
            lines.append(f"FAIL 字体\n{traceback.format_exc()}")

        lines.append("自检结束")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return "\n".join(lines)
