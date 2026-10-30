"""文本类文件 → PDF：TXT / Markdown / HTML。"""
from __future__ import annotations

import os
import re
from html.parser import HTMLParser

from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable,
    Image,
    KeepTogether,
    Paragraph,
    Preformatted,
    Spacer,
    Table,
    TableStyle,
)

from docbuild import LINE, MUTED, SOFT, build_doc, make_styles
from fonts import Fonts, ensure_fonts
from images_pdf import image_flowable
from utils import Options, display_width, esc, page_dimensions, read_text_file


# ---------------------------------------------------------------- 公共排版构件
def _has_cjk(text: str) -> bool:
    return any(ord(ch) > 0x2E80 for ch in text)


def _code_block(code: str, styles, avail_w: float) -> Table:
    style = styles["code_cjk"] if _has_cjk(code) else styles["code"]
    inner = Preformatted(code, style)
    t = Table([[inner]], colWidths=[avail_w])
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), SOFT),
                ("BOX", (0, 0), (-1, -1), 0.4, LINE),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return t


def _col_widths(rows: list[list[str]], avail_w: float) -> list[float]:
    ncol = max(len(r) for r in rows)
    weights = []
    for c in range(ncol):
        w = max((display_width(r[c]) if c < len(r) else 1) for r in rows)
        weights.append(min(max(w, 4), 44))
    total = float(sum(weights)) or 1.0
    return [avail_w * w / total for w in weights]


def _grid_table(rows: list[list[str]], styles, fonts: Fonts, avail_w: float,
                raw_markup: bool = False) -> Table:
    """rows[0] 作为表头。raw_markup=True 表示单元格内容已是 reportlab 标记。"""
    ncol = max(len(r) for r in rows)
    data = []
    for ri, row in enumerate(rows):
        cells = []
        for c in range(ncol):
            raw = row[c] if c < len(row) else ""
            style = styles["cellhead"] if ri == 0 else styles["cell"]
            txt = raw if raw_markup else _inline_md(raw, fonts)
            txt = txt.replace("\n", "<br/>") or " "
            cells.append(Paragraph(txt, style))
        data.append(cells)

    t = Table(data, colWidths=_col_widths(rows, avail_w), repeatRows=1, hAlign="LEFT")
    t.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.4, LINE),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EEF2F9")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return t


def _inline_md(text: str, fonts: Fonts) -> str:
    """把 Markdown 行内语法转成 reportlab 标记。"""
    s = esc(text)

    def _code(m):
        font = fonts.cjk if _has_cjk(m.group(1)) else fonts.mono
        return f'<font name="{font}">{m.group(1)}</font>'

    s = re.sub(r"`([^`]+)`", _code, s)
    s = re.sub(r"\*\*(.+?)\*\*", lambda m: f'<font name="{fonts.bold}">{m.group(1)}</font>', s)
    s = re.sub(r"(?<!\*)\*([^*\n]+)\*(?!\*)", r"<i>\1</i>", s)
    s = re.sub(r"~~(.+?)~~", r"<strike>\1</strike>", s)
    s = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"<u>\1</u>", s)
    return s


# ------------------------------------------------------------------- Markdown
_RE_HEAD = re.compile(r"^(#{1,6})\s+(.*)$")
_RE_UL = re.compile(r"^(\s*)[-*+]\s+(.*)$")
_RE_OL = re.compile(r"^(\s*)(\d+)[.)]\s+(.*)$")
_RE_HR = re.compile(r"^\s*([-*_])\s*(\1\s*){2,}$")
_RE_IMG = re.compile(r"^\s*!\[([^\]]*)\]\(([^)]+)\)\s*$")
_RE_TABLE_SEP = re.compile(r"^\s*\|?[\s:|-]+\|[\s:|-]*$")


def markdown_to_pdf(src: str, out_path: str, opts: Options) -> str:
    text = read_text_file(src)
    fonts = ensure_fonts()
    styles = make_styles(fonts)
    pw, ph = page_dimensions(opts)
    margin = max(0.0, opts.margin_mm) * mm
    avail_w = max(pw - 2 * margin, 80)
    avail_h = max(ph - 2 * margin - 9 * mm, 80)

    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    story: list = []
    i = 0
    base_dir = os.path.dirname(os.path.abspath(src))

    while i < len(lines):
        raw = lines[i]
        line = raw.rstrip()
        stripped = line.strip()

        if not stripped:
            story.append(Spacer(1, 3))
            i += 1
            continue

        # 代码块
        if stripped.startswith("```"):
            i += 1
            buf = []
            while i < len(lines) and not lines[i].strip().startswith("```"):
                buf.append(lines[i])
                i += 1
            i += 1
            story.append(_code_block("\n".join(buf), styles, avail_w))
            story.append(Spacer(1, 6))
            continue

        # 表格
        if stripped.startswith("|") and i + 1 < len(lines) and _RE_TABLE_SEP.match(lines[i + 1]):
            rows: list[list[str]] = []
            header = [c.strip() for c in stripped.strip("|").split("|")]
            rows.append(header)
            i += 2
            while i < len(lines) and lines[i].strip().startswith("|"):
                rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")])
                i += 1
            story.append(_grid_table(rows, styles, fonts, avail_w))
            story.append(Spacer(1, 8))
            continue

        # 标题
        m = _RE_HEAD.match(stripped)
        if m:
            lvl = len(m.group(1))
            story.append(Paragraph(_inline_md(m.group(2).strip(), fonts), styles[f"h{lvl}"]))
            i += 1
            continue

        # 分隔线
        if _RE_HR.match(stripped):
            story.append(Spacer(1, 4))
            story.append(HRFlowable(width="100%", thickness=0.6, color=LINE))
            story.append(Spacer(1, 6))
            i += 1
            continue

        # 独立图片
        m = _RE_IMG.match(stripped)
        if m:
            alt, target = m.group(1), m.group(2)
            path = target if os.path.isabs(target) else os.path.join(base_dir, target)
            flow = None
            if os.path.exists(path):
                try:
                    flow = image_flowable(path, avail_w, avail_h * 0.75)
                except Exception:
                    flow = None
            if flow is not None:
                story.append(flow)
                if alt:
                    story.append(Paragraph(esc(alt), styles["caption"]))
            else:
                story.append(Paragraph(f"[图片] {esc(alt or target)}", styles["body"]))
            i += 1
            continue

        # 引用
        if stripped.startswith(">"):
            buf = []
            while i < len(lines) and lines[i].strip().startswith(">"):
                buf.append(lines[i].strip().lstrip(">").strip())
                i += 1
            story.append(Paragraph(_inline_md(" ".join(buf), fonts), styles["quote"]))
            continue

        # 无序列表
        m = _RE_UL.match(line)
        if m:
            indent = len(m.group(1).expandtabs(4))
            style = styles["body"]
            story.append(
                Paragraph(
                    _inline_md(m.group(2).strip(), fonts),
                    style,
                    bulletText="•",
                )
            )
            i += 1
            continue

        # 有序列表
        m = _RE_OL.match(line)
        if m:
            story.append(
                Paragraph(
                    _inline_md(m.group(3).strip(), fonts),
                    styles["body"],
                    bulletText=f"{m.group(2)}.",
                )
            )
            i += 1
            continue

        # 普通段落：合并连续行
        buf = [stripped]
        i += 1
        while i < len(lines):
            nxt = lines[i].strip()
            if (
                not nxt
                or nxt.startswith(("#", ">", "```", "|"))
                or _RE_UL.match(lines[i])
                or _RE_OL.match(lines[i])
                or _RE_HR.match(nxt)
                or _RE_IMG.match(nxt)
            ):
                break
            buf.append(nxt)
            i += 1
        story.append(Paragraph(_inline_md(" ".join(buf), fonts), styles["body"]))

    if not story:
        story.append(Paragraph("（空文件）", styles["body"]))

    return build_doc(out_path, story, opts, os.path.basename(src), fonts)


# ------------------------------------------------------------------------ TXT
def text_to_pdf(src: str, out_path: str, opts: Options) -> str:
    text = read_text_file(src)
    fonts = ensure_fonts()
    styles = make_styles(fonts)
    story: list = []
    for block in re.split(r"\n\s*\n", text.replace("\r\n", "\n")):
        block = block.rstrip()
        if not block.strip():
            continue
        body = "<br/>".join(esc(l) for l in block.split("\n"))
        story.append(Paragraph(body, styles["body"]))
        story.append(Spacer(1, 4))
    if not story:
        story.append(Paragraph("（空文件）", styles["body"]))
    return build_doc(out_path, story, opts, os.path.basename(src), fonts)


# ----------------------------------------------------------------------- HTML
class _HtmlToBlocks(HTMLParser):
    """把 HTML 拆成结构化块（标题/段落/列表/代码/表格/图片）。"""

    SKIP = {"script", "style", "head", "noscript"}
    HEADINGS = {"h1": 1, "h2": 2, "h3": 3, "h4": 4, "h5": 5, "h6": 6}

    def __init__(self, fonts: Fonts, base_dir: str):
        super().__init__(convert_charrefs=True)
        self.fonts = fonts
        self.base_dir = base_dir
        self.blocks: list[tuple] = []
        self.buf: list[str] = []
        self.kind = "p"
        self.level = 0
        self.bold = 0
        self.italic = 0
        self.pre = 0
        self.pre_buf: list[str] = []
        self.skip = 0
        self.table: list[list[tuple[str, str]]] | None = None
        self.row: list[tuple[str, str]] | None = None
        self.cell: list[str] | None = None
        self.cell_head = False
        self.lists: list[str] = []
        self.li_no = 0

    # -- helpers
    def _flush(self):
        text = "".join(self.buf).strip()
        self.buf = []
        if not text:
            return
        if self.kind == "h":
            self.blocks.append(("h", self.level, text))
        elif self.kind == "li":
            ordered = bool(self.lists and self.lists[-1] == "ol")
            self.blocks.append(("li", text, self.li_no if ordered else 0))
        else:
            self.blocks.append(("p", text))

    def _styled(self, data: str) -> str:
        s = esc(data)
        if self.bold:
            s = f'<font name="{self.fonts.bold}">{s}</font>'
        if self.italic:
            s = f"<i>{s}</i>"
        return s

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "body":
            self.skip = 0
        if tag in self.SKIP:
            self.skip += 1
            return
        if self.skip:
            return
        if tag in self.HEADINGS:
            self._flush()
            self.kind, self.level = "h", self.HEADINGS[tag]
        elif tag in ("p", "div", "section", "article", "header", "footer", "main", "figure"):
            self._flush()
            self.kind = "p"
        elif tag == "li":
            self._flush()
            self.kind = "li"
            if self.lists and self.lists[-1] == "ol":
                self.li_no += 1
            else:
                self.li_no = 0
        elif tag in ("ul", "ol"):
            self._flush()
            self.lists.append(tag)
            if tag == "ol":
                self.li_no = 0
        elif tag == "pre":
            self._flush()
            self.pre = 1
            self.pre_buf = []
        elif tag in ("b", "strong"):
            self.bold += 1
        elif tag in ("i", "em"):
            self.italic += 1
        elif tag == "br":
            self.buf.append("\n")
        elif tag == "hr":
            self._flush()
            self.blocks.append(("hr",))
        elif tag == "img":
            src = a.get("src", "")
            if src:
                path = src if os.path.isabs(src) else os.path.join(self.base_dir, src)
                self.blocks.append(("img", path, a.get("alt", "")))
        elif tag == "table":
            self._flush()
            self.table = []
        elif tag == "tr":
            self.row = []
        elif tag in ("td", "th"):
            self.cell = []
            self.cell_head = tag == "th"

    def handle_endtag(self, tag):
        if tag in self.SKIP:
            self.skip = max(0, self.skip - 1)
            return
        if self.skip:
            return
        if tag in self.HEADINGS:
            self._flush()
            self.kind = "p"
        elif tag in ("p", "div", "section", "article", "header", "footer", "main", "figure"):
            self._flush()
        elif tag == "li":
            self._flush()
            self.kind = "p"
        elif tag in ("ul", "ol"):
            self._flush()
            if self.lists:
                self.lists.pop()
        elif tag == "pre":
            self.blocks.append(("pre", "".join(self.pre_buf).rstrip("\n")))
            self.pre = 0
            self.pre_buf = []
        elif tag in ("b", "strong"):
            self.bold = max(0, self.bold - 1)
        elif tag in ("i", "em"):
            self.italic = max(0, self.italic - 1)
        elif tag in ("td", "th"):
            if self.cell is not None and self.row is not None:
                self.row.append(("head" if self.cell_head else "body", "".join(self.cell).strip()))
            self.cell = None
        elif tag == "tr":
            if self.row is not None and self.table is not None:
                self.table.append(self.row)
            self.row = None
        elif tag == "table":
            if self.table:
                self.blocks.append(("table", self.table))
            self.table = None

    def handle_data(self, data):
        if self.skip:
            return
        if self.pre:
            self.pre_buf.append(data)
            return
        if self.cell is not None:
            self.cell.append(self._styled(data))
        else:
            self.buf.append(self._styled(data))


def html_to_pdf(src: str, out_path: str, opts: Options) -> str:
    fonts = ensure_fonts()
    styles = make_styles(fonts)
    html = read_text_file(src)
    parser = _HtmlToBlocks(fonts, os.path.dirname(os.path.abspath(src)))
    parser.feed(html)
    parser.close()
    parser._flush()

    pw, ph = page_dimensions(opts)
    margin = max(0.0, opts.margin_mm) * mm
    avail_w = max(pw - 2 * margin, 80)
    avail_h = max(ph - 2 * margin - 9 * mm, 80)

    story: list = []
    for block in parser.blocks:
        kind = block[0]
        if kind == "h":
            _, level, text = block
            story.append(Paragraph(text, styles[f"h{level}"]))
        elif kind == "p":
            story.append(Paragraph(block[1], styles["body"]))
        elif kind == "li":
            _, text, num = block
            story.append(Paragraph(text, styles["body"], bulletText=f"{num}." if num else "•"))
        elif kind == "pre":
            story.append(_code_block(block[1], styles, avail_w))
            story.append(Spacer(1, 6))
        elif kind == "hr":
            story.append(Spacer(1, 4))
            story.append(HRFlowable(width="100%", thickness=0.6, color=LINE))
            story.append(Spacer(1, 6))
        elif kind == "img":
            _, path, alt = block
            flow = None
            if os.path.exists(path):
                try:
                    flow = image_flowable(path, avail_w, avail_h * 0.75)
                except Exception:
                    flow = None
            if flow is not None:
                story.append(flow)
            elif alt:
                story.append(Paragraph(f"[图片] {esc(alt)}", styles["caption"]))
        elif kind == "table":
            rows = [[c[1] for c in r] for r in block[1] if r]
            if rows:
                story.append(_grid_table(rows, styles, fonts, avail_w, raw_markup=True))
                story.append(Spacer(1, 8))

    if not story:
        story.append(Paragraph("（页面无可提取的文字内容）", styles["body"]))
    return build_doc(out_path, story, opts, os.path.basename(src), fonts)
