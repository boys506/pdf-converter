"""转换调度：单个文件 → PDF，多文件 → 合并 PDF。"""
from __future__ import annotations

import os
import shutil
import tempfile
from typing import Callable

from utils import (
    DOC_EXTS,
    IMAGE_EXTS,
    Options,
    SHEET_EXTS,
    SUPPORTED_EXTS,
    TEXT_EXTS,
    timestamp_name,
    unique_path,
)

ProgressCb = Callable[[int, int, str], None]


def is_supported(path: str) -> bool:
    return os.path.splitext(path)[1].lower() in SUPPORTED_EXTS


def convert_one(src: str, dst: str, opts: Options) -> str:
    """把单个文件转成 PDF，返回实际输出路径。"""
    ext = os.path.splitext(src)[1].lower()
    os.makedirs(os.path.dirname(os.path.abspath(dst)) or ".", exist_ok=True)

    if ext == ".pdf":
        shutil.copy2(src, dst)
        return dst
    if ext in IMAGE_EXTS:
        from images_pdf import images_to_pdf

        return images_to_pdf([src], dst, opts)
    if ext == ".docx":
        from office_pdf import docx_to_pdf

        return docx_to_pdf(src, dst, opts)
    if ext in (".xlsx", ".xlsm"):
        from office_pdf import xlsx_to_pdf

        return xlsx_to_pdf(src, dst, opts)
    if ext == ".csv":
        from office_pdf import csv_to_pdf

        return csv_to_pdf(src, dst, opts)
    if ext in (".md", ".markdown"):
        from text_pdf import markdown_to_pdf

        return markdown_to_pdf(src, dst, opts)
    if ext in (".html", ".htm"):
        from text_pdf import html_to_pdf

        return html_to_pdf(src, dst, opts)
    if ext in TEXT_EXTS:
        from text_pdf import text_to_pdf

        return text_to_pdf(src, dst, opts)

    if ext in (".doc", ".xls", ".ppt", ".pptx"):
        raise ValueError(f"暂不支持 {ext}，请先另存为 .docx / .xlsx 再转换")

    raise ValueError(f"不支持的文件类型：{ext or '未知'}")


def merge_pdfs(paths: list[str], out_path: str) -> str:
    from pypdf import PdfReader, PdfWriter

    writer = PdfWriter()
    for p in paths:
        reader = PdfReader(p)
        if reader.is_encrypted:
            try:
                reader.decrypt("")
            except Exception:
                raise ValueError(f"PDF 已加密，无法合并：{os.path.basename(p)}")
        writer.append(reader)
    with open(out_path, "wb") as f:
        writer.write(f)
    return out_path


def run(paths: list[str], opts: Options, progress: ProgressCb | None = None) -> list[str]:
    """执行转换。progress(已完成数, 总数, 当前文件名)。"""
    paths = [p for p in paths if os.path.exists(p)]
    if not paths:
        raise ValueError("请先添加要转换的文件")

    out_dir = opts.out_dir or os.path.join(os.path.expanduser("~"), "Desktop")
    os.makedirs(out_dir, exist_ok=True)
    total = len(paths)
    results: list[str] = []

    if opts.merge:
        # 中间文件放在输出目录内，避免依赖系统临时目录（某些环境 %TEMP% 不可写）
        tmp = tempfile.mkdtemp(prefix=".pdfmerge_", dir=out_dir)
        try:
            parts: list[str] = []
            for i, src in enumerate(paths):
                if progress:
                    progress(i, total, os.path.basename(src))
                if os.path.splitext(src)[1].lower() == ".pdf":
                    parts.append(src)
                    continue
                tmp_pdf = os.path.join(tmp, f"{i:04d}.pdf")
                convert_one(src, tmp_pdf, opts)
                parts.append(tmp_pdf)
            if progress:
                progress(total - 1, total, "正在合并…")
            out = unique_path(os.path.join(out_dir, timestamp_name("合并文档")))
            merge_pdfs(parts, out)
            results.append(out)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    else:
        for i, src in enumerate(paths):
            if progress:
                progress(i, total, os.path.basename(src))
            stem = os.path.splitext(os.path.basename(src))[0]
            out = unique_path(os.path.join(out_dir, f"{stem}.pdf"))
            convert_one(src, out, opts)
            results.append(out)
        if progress:
            progress(total, total, "完成")

    return results
