"""Office 文档 → PDF：Word(.docx) / Excel(.xlsx,.csv)。"""
from __future__ import annotations

import csv
import io
import os
import re
from datetime import date, datetime

from reportlab.lib.units import mm
from reportlab.platypus import (
    KeepTogether,
    PageBreak,
    Paragraph,
    Spacer,
)

from docbuild import build_doc, make_styles
from fonts import Fonts, ensure_fonts
from images_pdf import image_flowable
from text_pdf import _grid_table
from utils import Options, esc, page_dimensions

MAX_SHEET_ROWS = 5000
MAX_SHEET_COLS = 60


# ------------------------------------------------------------------------ Word
def _heading_level(style_name: str) -> int | None:
    name = (style_name or "").strip()
    low = name.lower()
    if low in ("title", "标题"):
        return 0
    m = re.match(r"(?:heading|标题)\s*(\d)", low if low.startswith("heading") else name)
    if m:
        return int(m.group(1))
    return None


def _runs_markup(para, fonts: Fonts) -> str:
    parts: list[str] = []
    for run in para.runs:
        text = run.text
        if not text:
            continue
        s = esc(text).replace("\n", "<br/>")
        try:
            if run.font.strike:
                s = f"<strike>{s}</strike>"
            if run.underline:
                s = f"<u>{s}</u>"
        except Exception:
            pass
        if run.italic:
            s = f"<i>{s}</i>"
        try:
            bold = run.bold
        except Exception:
            bold = None
        if bold:
            s = f'<font name="{fonts.bold}">{s}</font>'
        try:
            if run.font.color is not None and run.font.color.rgb is not None:
                s = f'<font color="#{run.font.color.rgb}">{s}</font>'
        except Exception:
            pass
        parts.append(s)
    return "".join(parts)


def _para_images(para, avail_w: float, avail_h: float) -> list:
    from docx.oxml.ns import qn

    flows = []
    for blip in para._p.findall(".//" + qn("a:blip")):
        rid = blip.get(qn("r:embed"))
        if not rid:
            continue
        try:
            part = para.part.related_parts[rid]
            flow = image_flowable(part.blob, avail_w, avail_h)
            if flow is not None:
                flows.append(flow)
        except Exception:
            continue
    return flows


def _docx_table_flow(table, styles, fonts: Fonts, avail_w: float):
    rows: list[list[str]] = []
    for row in table.rows:
        cells = []
        for cell in row.cells:
            text = "\n".join(p.text for p in cell.paragraphs).strip()
            cells.append(text)
        rows.append(cells)
    if not rows:
        return None
    return _grid_table(rows, styles, fonts, avail_w)


def docx_to_pdf(src: str, out_path: str, opts: Options) -> str:
    from docx import Document
    from docx.oxml.ns import qn
    from docx.table import Table as DocxTable
    from docx.text.paragraph import Paragraph as DocxParagraph

    fonts = ensure_fonts()
    styles = make_styles(fonts)
    document = Document(src)

    pw, ph = page_dimensions(opts)
    margin = max(0.0, opts.margin_mm) * mm
    avail_w = max(pw - 2 * margin, 80)
    avail_h = max(ph - 2 * margin - 9 * mm, 80)

    story: list = []
    for child in document.element.body.iterchildren():
        if child.tag == qn("w:p"):
            para = DocxParagraph(child, document)

            # 分页符
            has_break = any(
                br.get(qn("w:type")) == "page" for br in child.findall(".//" + qn("w:br"))
            )

            level = _heading_level(para.style.name if para.style is not None else "")
            markup = _runs_markup(para, fonts)
            text = para.text.strip()

            if level == 0:
                story.append(Paragraph(markup or esc(text), styles["title"]))
            elif level is not None:
                key = f"h{min(level, 6)}"
                story.append(Paragraph(markup or esc(text), styles[key]))
            elif text:
                style = styles["body"]
                # 列表样式
                sname = (para.style.name or "").lower() if para.style is not None else ""
                bullet = None
                if "list" in sname or "列表" in sname:
                    bullet = "•"
                story.append(Paragraph(markup, style, bulletText=bullet))
            elif not text:
                story.append(Spacer(1, 6))

            imgs = _para_images(para, avail_w, avail_h * 0.8)
            if imgs:
                story.extend(imgs)
                story.append(Spacer(1, 6))
            if has_break:
                story.append(PageBreak())

        elif child.tag == qn("w:tbl"):
            table = DocxTable(child, document)
            flow = _docx_table_flow(table, styles, fonts, avail_w)
            if flow is not None:
                story.append(flow)
                story.append(Spacer(1, 8))

    if not story:
        story.append(Paragraph("（文档为空）", styles["body"]))

    return build_doc(out_path, story, opts, os.path.basename(src), fonts)


# ---------------------------------------------------------------------- Excel
def _cell_text(value) -> str:
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M") if (value.hour or value.minute) else value.strftime("%Y-%m-%d")
    if isinstance(value, date):
        return value.strftime("%Y-%m-%d")
    if isinstance(value, float):
        if value.is_integer():
            return str(int(value))
        return f"{value:.10g}"
    return str(value)


def _sheet_rows(ws) -> list[list[str]]:
    rows: list[list[str]] = []
    max_col = 0
    for row in ws.iter_rows(min_row=1, max_row=min(ws.max_row, MAX_SHEET_ROWS),
                            max_col=min(ws.max_column, MAX_SHEET_COLS)):
        vals = [_cell_text(c.value) for c in row]
        while vals and not vals[-1]:
            vals.pop()
        rows.append(vals)
        max_col = max(max_col, len(vals))
    while rows and not any(rows[-1]):
        rows.pop()
    while rows and not any(rows[0]):
        rows.pop(0)
    if max_col == 0:
        return []
    return [r + [""] * (max_col - len(r)) for r in rows]


def xlsx_to_pdf(src: str, out_path: str, opts: Options) -> str:
    from openpyxl import load_workbook

    fonts = ensure_fonts()
    styles = make_styles(fonts)

    wb = load_workbook(src, data_only=True)
    sheets = [ws for ws in wb.worksheets if (ws.max_row or 1) > 1 or (ws.max_column or 1) > 1]
    if not sheets:
        sheets = list(wb.worksheets)

    # 多列时自动切横版
    auto_land = opts.orientation == "auto"
    wide = any((ws.max_column or 0) > 5 for ws in sheets)
    local = Options(**{**opts.__dict__})
    if auto_land:
        local.orientation = "landscape" if wide else "portrait"

    pw, ph = page_dimensions(local)
    margin = max(0.0, local.margin_mm) * mm
    avail_w = max(pw - 2 * margin, 80)

    story: list = []
    for idx, ws in enumerate(sheets):
        rows = _sheet_rows(ws)
        if idx > 0:
            story.append(PageBreak())
        title = Paragraph(esc(ws.title), styles["h2"])
        if not rows:
            story.append(KeepTogether([title, Paragraph("（空工作表）", styles["body"])]))
            continue
        # 表头行加粗显示
        table = _grid_table(rows, styles, fonts, avail_w)
        story.append(KeepTogether([title, Spacer(1, 2)]))
        story.append(table)
        story.append(Spacer(1, 10))

    if not story:
        story.append(Paragraph("（工作簿为空）", styles["body"]))

    return build_doc(out_path, story, local, os.path.basename(src), fonts)


# ------------------------------------------------------------------------ CSV
def csv_to_pdf(src: str, out_path: str, opts: Options) -> str:
    from utils import read_text_file

    fonts = ensure_fonts()
    styles = make_styles(fonts)
    text = read_text_file(src)
    sample = text[:4096]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
    except Exception:
        dialect = csv.excel
    rows = [[c.strip() for c in r] for r in csv.reader(io.StringIO(text), dialect)]
    rows = [r for r in rows if any(x for x in r)]
    rows = rows[:MAX_SHEET_ROWS]
    if not rows:
        rows = [["（空文件）"]]

    local = Options(**{**opts.__dict__})
    if opts.orientation == "auto":
        local.orientation = "landscape" if max(len(r) for r in rows) > 5 else "portrait"

    pw, ph = page_dimensions(local)
    margin = max(0.0, local.margin_mm) * mm
    avail_w = max(pw - 2 * margin, 80)

    story = [_grid_table(rows, styles, fonts, avail_w)]
    return build_doc(out_path, story, local, os.path.basename(src), fonts)
