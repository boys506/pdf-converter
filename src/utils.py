"""公共工具：页面尺寸、路径处理、选项定义。"""
from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime

A4 = (595.276, 841.890)
PAGE_SIZES = {
    "A4": A4,
    "A3": (841.890, 1190.551),
    "A5": (419.528, 595.276),
    "Letter": (612.0, 792.0),
}

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".gif", ".webp", ".tif", ".tiff"}
DOC_EXTS = {".docx"}
SHEET_EXTS = {".xlsx", ".xlsm", ".csv"}
TEXT_EXTS = {".txt", ".md", ".markdown", ".html", ".htm", ".log", ".ini", ".json"}
SUPPORTED_EXTS = IMAGE_EXTS | DOC_EXTS | SHEET_EXTS | TEXT_EXTS | {".pdf"}

EXT_LABEL = {
    **{e: "图片" for e in IMAGE_EXTS},
    ".docx": "Word",
    ".doc": "Word(旧版)",
    ".xlsx": "Excel",
    ".xlsm": "Excel",
    ".xls": "Excel(旧版)",
    ".csv": "CSV 表格",
    ".txt": "文本",
    ".md": "Markdown",
    ".markdown": "Markdown",
    ".html": "网页",
    ".htm": "网页",
    ".log": "文本",
    ".ini": "文本",
    ".json": "文本",
    ".pdf": "PDF",
}


@dataclass
class Options:
    """转换参数。"""

    merge: bool = False                 # True: 合并为一个 PDF
    page_size: str = "A4"               # A4 / A3 / A5 / Letter / 原始尺寸
    orientation: str = "portrait"       # portrait / landscape / auto
    margin_mm: float = 15.0
    out_dir: str = ""
    page_numbers: bool = True
    img_quality: int = 92


def page_dimensions(opts: Options, aspect: float | None = None) -> tuple[float, float]:
    """按选项计算页面宽高（单位：点）。aspect = 宽/高，用于“跟随内容”。"""
    w, h = PAGE_SIZES.get(opts.page_size, A4)
    portrait = (min(w, h), max(w, h))
    landscape = (max(w, h), min(w, h))
    o = opts.orientation
    if o == "auto":
        if aspect:
            return landscape if aspect > 1.0 else portrait
        return portrait
    return landscape if o == "landscape" else portrait


def human_size(num: float) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if num < 1024 or unit == "GB":
            return f"{num:.0f} {unit}" if unit == "B" else f"{num:.1f} {unit}"
        num /= 1024.0
    return f"{num:.1f} GB"


def unique_path(path: str) -> str:
    """若文件已存在，自动追加 _1 / _2 …"""
    if not os.path.exists(path):
        return path
    base, ext = os.path.splitext(path)
    i = 1
    while True:
        cand = f"{base}_{i}{ext}"
        if not os.path.exists(cand):
            return cand
        i += 1


def timestamp_name(prefix: str = "合并文档") -> str:
    return f"{prefix}_{datetime.now():%Y%m%d_%H%M%S}.pdf"


def esc(text: str) -> str:
    """转义为 reportlab Paragraph 可用的 XML。"""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def detect_encoding(raw: bytes) -> str:
    for enc in ("utf-8-sig", "utf-8", "gb18030", "big5", "utf-16"):
        try:
            raw.decode(enc)
            return enc
        except (UnicodeDecodeError, UnicodeError):
            continue
    return "utf-8"


def read_text_file(path: str) -> str:
    with open(path, "rb") as f:
        raw = f.read()
    enc = detect_encoding(raw)
    try:
        return raw.decode(enc, errors="replace")
    except Exception:
        return raw.decode("utf-8", errors="replace")


def display_width(text: str) -> int:
    """估算显示宽度：中文按 2 个字符算。"""
    n = 0
    for ch in text:
        n += 2 if ord(ch) > 0x2E80 else 1
    return n
