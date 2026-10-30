"""字体注册：优先嵌入系统中文字体，确保 PDF 中文不乱码。"""
from __future__ import annotations

import os
from dataclasses import dataclass

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

FONT_DIR = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts")

# key -> (注册名, [(文件名, ttc 子字体序号), ...])
_CANDIDATES = {
    "cjk": (
        "CJK",
        [
            ("msyh.ttc", 0),
            ("msyh.ttf", 0),
            ("Deng.ttf", 0),
            ("simsun.ttc", 0),
            ("simhei.ttf", 0),
        ],
    ),
    "bold": (
        "CJKBold",
        [
            ("msyhbd.ttc", 0),
            ("msyhbd.ttf", 0),
            ("simhei.ttf", 0),
            ("msyh.ttc", 0),
        ],
    ),
    "mono": (
        "Mono",
        [("consola.ttf", 0), ("cour.ttf", 0)],
    ),
}


@dataclass(frozen=True)
class Fonts:
    cjk: str
    bold: str
    mono: str


_cache: Fonts | None = None


def ensure_fonts() -> Fonts:
    """注册并返回可用字体名（进程内只执行一次）。"""
    global _cache
    if _cache is not None:
        return _cache

    resolved: dict[str, str | None] = {}
    for key, (name, candidates) in _CANDIDATES.items():
        chosen = None
        for fname, index in candidates:
            path = os.path.join(FONT_DIR, fname)
            if not os.path.exists(path):
                continue
            try:
                pdfmetrics.registerFont(TTFont(name, path, subfontIndex=index))
                chosen = name
                break
            except Exception:
                continue
        resolved[key] = chosen

    if resolved["cjk"] is None:
        # 兜底：reportlab 内置 CID 字体（无需字体文件）
        try:
            from reportlab.pdfbase.cidfonts import UnicodeCIDFont

            pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
            resolved["cjk"] = "STSong-Light"
        except Exception:
            resolved["cjk"] = "Helvetica"

    _cache = Fonts(
        cjk=resolved["cjk"] or "Helvetica",
        bold=resolved["bold"] or resolved["cjk"] or "Helvetica-Bold",
        mono=resolved["mono"] or "Courier",
    )
    return _cache
