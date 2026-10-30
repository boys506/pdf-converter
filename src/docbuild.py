"""PDF 排版公共构件：样式表、文档模板、页脚页码。"""
from __future__ import annotations

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import BaseDocTemplate, Frame, PageTemplate

from fonts import Fonts
from utils import Options, page_dimensions

INK = colors.HexColor("#1F2328")
MUTED = colors.HexColor("#6B7280")
LINE = colors.HexColor("#E4E7EC")
SOFT = colors.HexColor("#F5F6F8")
ACCENT = colors.HexColor("#2F6BFF")


def make_styles(fonts: Fonts, base_size: float = 10.5) -> dict[str, ParagraphStyle]:
    """生成一套中文友好的段落样式。"""
    s: dict[str, ParagraphStyle] = {}
    s["body"] = ParagraphStyle(
        "body",
        fontName=fonts.cjk,
        fontSize=base_size,
        leading=base_size * 1.75,
        textColor=INK,
        alignment=TA_JUSTIFY,
        wordWrap="CJK",
        spaceAfter=5,
        bulletFontName=fonts.cjk,
        bulletFontSize=base_size,
        leftIndent=14,
        bulletIndent=2,
    )
    s["title"] = ParagraphStyle(
        "title",
        parent=s["body"],
        fontName=fonts.bold,
        fontSize=base_size * 2.2,
        leading=base_size * 2.9,
        alignment=TA_CENTER,
        spaceAfter=14,
    )
    for lvl, size, before, after in (
        (1, 2.0, 16, 8),
        (2, 1.6, 14, 6),
        (3, 1.32, 12, 5),
        (4, 1.15, 10, 4),
        (5, 1.05, 8, 3),
        (6, 1.0, 8, 3),
    ):
        s[f"h{lvl}"] = ParagraphStyle(
            f"h{lvl}",
            parent=s["body"],
            fontName=fonts.bold,
            fontSize=base_size * size,
            leading=base_size * size * 1.45,
            spaceBefore=before,
            spaceAfter=after,
            alignment=TA_LEFT,
            textColor=colors.HexColor("#111827"),
        )
    s["quote"] = ParagraphStyle(
        "quote",
        parent=s["body"],
        textColor=MUTED,
        leftIndent=14,
        borderPadding=(4, 8, 4, 10),
        backColor=SOFT,
        spaceBefore=4,
        spaceAfter=8,
    )
    s["code"] = ParagraphStyle(
        "code",
        parent=s["body"],
        fontName=fonts.mono,
        fontSize=base_size * 0.86,
        leading=base_size * 1.4,
        alignment=TA_LEFT,
        wordWrap=None,
        textColor=colors.HexColor("#24292F"),
        leftIndent=0,
        bulletIndent=0,
    )
    # 含中文的代码块/行内代码改用中文字体，避免字形缺失
    s["code_cjk"] = ParagraphStyle(
        "code_cjk",
        parent=s["code"],
        fontName=fonts.cjk,
        wordWrap="CJK",
    )
    s["cell"] = ParagraphStyle(
        "cell",
        parent=s["body"],
        fontSize=base_size * 0.88,
        leading=base_size * 1.35,
        alignment=TA_LEFT,
        spaceAfter=0,
    )
    s["cellhead"] = ParagraphStyle(
        "cellhead",
        parent=s["cell"],
        fontName=fonts.bold,
        textColor=colors.HexColor("#111827"),
    )
    s["caption"] = ParagraphStyle(
        "caption",
        parent=s["body"],
        fontSize=base_size * 0.82,
        textColor=MUTED,
        alignment=TA_CENTER,
        spaceBefore=2,
        spaceAfter=10,
    )
    return s


def build_doc(out_path: str, story: list, opts: Options, title: str, fonts: Fonts,
              page_size: tuple[float, float] | None = None) -> str:
    """用 BaseDocTemplate 输出 PDF，可选页脚页码。"""
    pw, ph = page_size or page_dimensions(opts)
    margin = max(0.0, opts.margin_mm) * mm
    footer_h = 9 * mm if opts.page_numbers else 0.0
    bottom = margin + footer_h

    doc = BaseDocTemplate(
        out_path,
        pagesize=(pw, ph),
        leftMargin=margin,
        rightMargin=margin,
        topMargin=margin,
        bottomMargin=bottom,
        title=title,
        creator="PDF 转换工坊",
        author="PDF 转换工坊",
    )
    frame = Frame(
        margin,
        bottom,
        max(pw - 2 * margin, 40),
        max(ph - bottom - margin, 40),
        leftPadding=0,
        rightPadding=0,
        topPadding=0,
        bottomPadding=0,
        id="body",
    )

    def _footer(canv, doc_):
        canv.saveState()
        canv.setFont(fonts.cjk, 8)
        canv.setFillColor(colors.HexColor("#9AA1AC"))
        canv.drawCentredString(pw / 2.0, margin * 0.45 + 2, f"— {doc_.page} —")
        canv.restoreState()

    doc.addPageTemplates([PageTemplate(id="main", frames=[frame], onPage=_footer if opts.page_numbers else None)])
    doc.build(story)
    return out_path
