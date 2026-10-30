"""图片 → PDF（支持 JPG/PNG/BMP/GIF/WEBP/TIFF，多页 TIFF 逐页输出）。"""
from __future__ import annotations

import io
import os

from PIL import Image, ImageOps
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

from utils import Options, page_dimensions


def _to_rgb(im: Image.Image) -> Image.Image:
    """统一转 RGB：透明底铺白，CMYK/调色板转真彩。"""
    if im.mode in ("RGBA", "LA", "PA") or (im.mode == "P" and "transparency" in im.info):
        rgba = im.convert("RGBA")
        bg = Image.new("RGB", rgba.size, (255, 255, 255))
        bg.paste(rgba, mask=rgba.split()[-1])
        return bg
    if im.mode != "RGB":
        return im.convert("RGB")
    return im


def _image_dpi(im: Image.Image) -> tuple[float, float]:
    dpi = im.info.get("dpi")
    try:
        dx, dy = float(dpi[0]), float(dpi[1])
    except Exception:
        dx, dy = 96.0, 96.0
    dx = min(max(dx, 48.0), 600.0) if dx else 96.0
    dy = min(max(dy, 48.0), 600.0) if dy else 96.0
    return dx, dy


def image_flowable(source, max_w: float, max_h: float):
    """把图片（路径或字节）转成 reportlab Image，按比例缩放到限制内。"""
    from reportlab.platypus import Image as RLImage

    if isinstance(source, (bytes, bytearray)):
        with Image.open(io.BytesIO(source)) as im:
            w, h = im.size
        target = io.BytesIO(source)
    else:
        with Image.open(source) as im:
            w, h = im.size
        target = source
    if w <= 0 or h <= 0:
        return None
    scale = min(max_w / w, max_h / h, 1.0)
    return RLImage(target, width=w * scale, height=h * scale)


def images_to_pdf(paths: list[str], out_path: str, opts: Options) -> str:
    """把若干图片依次写入一个 PDF，每张图片一页。"""
    margin = max(0.0, opts.margin_mm) * mm
    c = canvas.Canvas(out_path, pageCompression=1)
    c.setTitle(os.path.basename(out_path))
    c.setCreator("PDF 转换工坊")

    first = True
    for path in paths:
        with Image.open(path) as im:
            total = getattr(im, "n_frames", 1) if (im.format or "").upper() == "TIFF" else 1
            for idx in range(total):
                if total > 1:
                    im.seek(idx)
                frame = ImageOps.exif_transpose(im)
                frame = _to_rgb(frame)
                aspect = frame.width / frame.height if frame.height else 1.0

                if opts.page_size == "原始尺寸":
                    dx, dy = _image_dpi(im)
                    pw = frame.width * 72.0 / dx
                    ph = frame.height * 72.0 / dy
                    x, y = 0.0, 0.0
                    iw, ih = pw, ph
                else:
                    pw, ph = page_dimensions(opts, aspect)
                    avail_w = max(pw - 2 * margin, 10.0)
                    avail_h = max(ph - 2 * margin, 10.0)
                    scale = min(avail_w / frame.width, avail_h / frame.height)
                    iw, ih = frame.width * scale, frame.height * scale
                    x = (pw - iw) / 2.0
                    y = (ph - ih) / 2.0

                buf = io.BytesIO()
                frame.save(buf, format="JPEG", quality=int(opts.img_quality), subsampling=0, optimize=True)
                buf.seek(0)

                c.setPageSize((pw, ph))
                c.drawImage(ImageReader(buf), x, y, iw, ih, mask=None)
                c.showPage()
                first = False

    if first:
        raise ValueError("没有可转换的图片页面")
    c.save()
    return out_path
