"""PDF 转换工坊 —— 桌面图形界面（tkinter）。"""
from __future__ import annotations

import os
import queue
import threading
import tkinter as tk
import tkinter.font as tkfont
from tkinter import filedialog, messagebox, ttk

import engine
from utils import EXT_LABEL, Options, SUPPORTED_EXTS, human_size

BG = "#F4F5F7"
CARD = "#FFFFFF"
BORDER = "#E3E6EB"
INK = "#1F2328"
MUTED = "#6B7280"
FAINT = "#9AA1AC"
ACCENT = "#2F6BFF"
ACCENT_DARK = "#1F55E0"
OK_GREEN = "#16A34A"
ERR_RED = "#DC2626"

PAGE_OPTIONS = ["A4", "A3", "A5", "Letter", "原始尺寸"]
ORIENT_LABEL = {"纵向": "portrait", "横向": "landscape", "跟随内容": "auto"}


def pick_font() -> str:
    families = set(tkfont.families())
    for name in ("Microsoft YaHei UI", "Microsoft YaHei", "微软雅黑", "SimHei", "SimSun"):
        if name in families:
            return name
    return "TkDefaultFont"


class FlatButton(tk.Label):
    """自绘扁平按钮：1px 描边 + 悬停变色，避免 ttk 主题外观差异。"""

    def __init__(self, master, text, command, font, *, accent=False, width=None, padx=14, pady=6):
        self.enabled = True
        self.command = command
        if accent:
            self._bg, self._hover, self._fg, self._bd = ACCENT, ACCENT_DARK, "#FFFFFF", ACCENT
            self._bg_off, self._fg_off = "#A9C0F5", "#F2F6FF"
        else:
            self._bg, self._hover, self._fg, self._bd = "#FFFFFF", "#F1F4FA", INK, BORDER
            self._bg_off, self._fg_off = "#F5F6F8", "#B6BCC5"
        super().__init__(
            master,
            text=text,
            font=font,
            bg=self._bg,
            fg=self._fg,
            padx=padx,
            pady=pady,
            bd=0,
            width=width or 0,
            highlightthickness=1,
            highlightbackground=self._bd,
            highlightcolor=self._bd,
            cursor="hand2",
        )
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", self._on_click)

    def _on_enter(self, _e=None):
        if self.enabled:
            self.configure(bg=self._hover)

    def _on_leave(self, _e=None):
        if self.enabled:
            self.configure(bg=self._bg)

    def _on_click(self, _e=None):
        if self.enabled and self.command:
            self.command()

    def set_enabled(self, flag: bool, text: str | None = None) -> None:
        self.enabled = flag
        if text is not None:
            self.configure(text=text)
        if flag:
            self.configure(bg=self._bg, fg=self._fg, cursor="hand2", highlightbackground=self._bd)
        else:
            self.configure(bg=self._bg_off, fg=self._fg_off, cursor="arrow", highlightbackground=self._bd)


class ProgressBar(tk.Canvas):
    """自绘圆角进度条，避免 ttk 主题的边框观感。"""

    def __init__(self, master, height=8, trough="#EDEFF3", fill=ACCENT):
        super().__init__(master, height=height, bg=CARD, highlightthickness=0, bd=0)
        self._trough = trough
        self._fill = fill
        self._v = 0.0
        self._m = 1.0
        self.bind("<Configure>", lambda _e: self._draw())

    def _round(self, x0, y0, x1, y1, r, **kw):
        r = max(min(r, (x1 - x0) / 2, (y1 - y0) / 2), 1)
        pts = [
            x0 + r, y0, x1 - r, y0, x1, y0, x1, y0 + r,
            x1, y1 - r, x1, y1, x1 - r, y1, x0 + r, y1,
            x0, y1, x0, y1 - r, x0, y0 + r, x0, y0,
        ]
        return self.create_polygon(pts, smooth=True, **kw)

    def _draw(self):
        self.delete("all")
        w, h = self.winfo_width(), self.winfo_height()
        if w <= 2:
            return
        self._round(0, 0, w, h, h / 2, fill=self._trough, outline="")
        if self._v > 0:
            fw = max(h, w * self._v / self._m)
            self._round(0, 0, min(fw, w), h, h / 2, fill=self._fill, outline="")

    def set_max(self, m: float) -> None:
        self._m = max(float(m), 1.0)
        self._draw()

    def set(self, v: float) -> None:
        self._v = max(0.0, min(float(v), self._m))
        self._draw()

    def reset(self) -> None:
        self._v = 0.0
        self._m = 1.0
        self._draw()

    def finish(self) -> None:
        self._v = self._m
        self._draw()


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("PDF 转换工坊")
        self.geometry("1010x730")
        self.minsize(900, 660)
        self.configure(bg=BG)
        self.font = pick_font()
        self.items: list[dict] = []
        self.q: queue.Queue = queue.Queue()
        self.busy = False
        self.last_out_dir = ""

        self._init_style()
        self._build()
        self._center()

    # ------------------------------------------------------------------ 样式
    def _init_style(self) -> None:
        f = self.font
        st = ttk.Style(self)
        try:
            st.theme_use("clam")
        except tk.TclError:
            pass
        st.configure(
            "Files.Treeview",
            background=CARD,
            fieldbackground=CARD,
            foreground=INK,
            rowheight=30,
            borderwidth=0,
            font=(f, 10),
        )
        st.configure(
            "Files.Treeview.Heading",
            background="#F7F8FA",
            foreground=MUTED,
            font=(f, 9),
            relief="flat",
            padding=(8, 7),
        )
        st.map("Files.Treeview", background=[("selected", "#E8EFFF")], foreground=[("selected", INK)])
        st.configure(
            "Accent.Horizontal.TProgressbar",
            troughcolor="#EDEFF3",
            background=ACCENT,
            bordercolor="#EDEFF3",
            lightcolor=ACCENT,
            darkcolor=ACCENT,
            borderwidth=0,
            thickness=8,
        )
        st.configure(
            "TCombobox",
            fieldbackground="#FFFFFF",
            background="#FFFFFF",
            foreground=INK,
            bordercolor=BORDER,
            arrowcolor=MUTED,
            padding=5,
            font=(f, 10),
        )
        st.map(
            "TCombobox",
            fieldbackground=[("readonly", "#FFFFFF"), ("disabled", "#F5F6F8")],
            selectbackground=[("readonly", "#FFFFFF")],
            selectforeground=[("readonly", INK)],
            bordercolor=[("focus", ACCENT), ("hover", "#C9D3E6")],
        )
        st.configure("TRadiobutton", background=CARD, font=(f, 10), foreground=INK)
        st.map("TRadiobutton", background=[("active", CARD)], foreground=[("active", INK)])
        st.configure("TCheckbutton", background=CARD, font=(f, 10), foreground=INK)
        st.map("TCheckbutton", background=[("active", CARD)], foreground=[("active", INK)])
        st.configure("TScrollbar", background="#DDE1E8", troughcolor="#F7F8FA", borderwidth=0, arrowsize=12)

    # ------------------------------------------------------------------ 布局
    def _build(self) -> None:
        f = self.font
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        # ---- 顶部标题栏
        header = tk.Frame(self, bg=CARD)
        header.grid(row=0, column=0, sticky="ew")
        inner = tk.Frame(header, bg=CARD)
        inner.pack(fill="x", padx=22, pady=(14, 12))
        tk.Label(inner, text="PDF 转换工坊", bg=CARD, fg=INK, font=(f, 17, "bold")).pack(anchor="w")
        tk.Label(
            inner,
            text="图片 · Word · Excel · 文本 · Markdown · 网页  →  PDF，可合并成一个文件",
            bg=CARD,
            fg=MUTED,
            font=(f, 9),
        ).pack(anchor="w", pady=(3, 0))
        tk.Frame(self, bg=BORDER, height=1).grid(row=0, column=0, sticky="sew")

        # ---- 主体
        body = tk.Frame(self, bg=BG)
        body.grid(row=1, column=0, sticky="nsew", padx=18, pady=(14, 8))
        body.columnconfigure(0, weight=1)
        body.columnconfigure(1, weight=0, minsize=318)
        body.rowconfigure(0, weight=1)
        self._build_file_card(body)
        self._build_option_card(body)

        self._build_log_card()
        self._build_footer()

    def _build_file_card(self, parent) -> None:
        f = self.font
        card = tk.Frame(parent, bg=CARD, highlightbackground=BORDER, highlightthickness=1)
        card.grid(row=0, column=0, sticky="nsew", padx=(0, 14))
        card.rowconfigure(1, weight=1)
        card.columnconfigure(0, weight=1)

        bar = tk.Frame(card, bg=CARD)
        bar.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 9))
        FlatButton(bar, "＋ 添加文件", self.add_files, (f, 10), padx=13).pack(side="left")
        FlatButton(bar, "添加文件夹", self.add_folder, (f, 10)).pack(side="left", padx=(8, 0))
        FlatButton(bar, "移除", self.remove_selected, (f, 10), padx=12).pack(side="left", padx=(8, 0))
        FlatButton(bar, "清空", self.clear_all, (f, 10), padx=12).pack(side="left", padx=(8, 0))
        FlatButton(bar, "↓", lambda: self.move(1), (f, 10), padx=9).pack(side="right")
        FlatButton(bar, "↑", lambda: self.move(-1), (f, 10), padx=9).pack(side="right", padx=(0, 6))
        tk.Label(bar, text="排序", bg=CARD, fg=MUTED, font=(f, 9)).pack(side="right", padx=(0, 8))

        wrap = tk.Frame(card, bg=CARD)
        wrap.grid(row=1, column=0, sticky="nsew", padx=12)
        wrap.rowconfigure(0, weight=1)
        wrap.columnconfigure(0, weight=1)

        cols = ("name", "kind", "size", "status")
        self.tree = ttk.Treeview(wrap, columns=cols, show="headings", style="Files.Treeview", selectmode="extended")
        for cid, text, width, anchor, stretch in (
            ("name", "文件名", 250, "w", True),
            ("kind", "类型", 78, "center", False),
            ("size", "大小", 76, "e", False),
            ("status", "状态", 78, "center", False),
        ):
            self.tree.heading(cid, text=text, anchor=anchor)
            self.tree.column(cid, width=width, minwidth=60, anchor=anchor, stretch=stretch)
        self.tree.grid(row=0, column=0, sticky="nsew")
        self.tree.tag_configure("ok", foreground=OK_GREEN)
        self.tree.tag_configure("err", foreground=ERR_RED)
        self.tree.tag_configure("run", foreground=ACCENT)

        sb = ttk.Scrollbar(wrap, orient="vertical", command=self.tree.yview)
        sb.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.bind("<Delete>", lambda e: self.remove_selected())
        self.tree.bind("<Double-1>", self._open_item)

        tk.Label(
            card,
            text="支持 JPG/PNG/BMP/GIF/WEBP/TIFF · DOCX · XLSX/CSV · TXT/MD/HTML · PDF",
            bg=CARD,
            fg=FAINT,
            font=(f, 9),
        ).grid(row=2, column=0, sticky="w", padx=14, pady=(8, 12))

    def _build_option_card(self, parent) -> None:
        f = self.font
        card = tk.Frame(parent, bg=CARD, highlightbackground=BORDER, highlightthickness=1)
        card.grid(row=0, column=1, sticky="nsew")

        def section(title: str) -> tk.Frame:
            tk.Label(card, text=title, bg=CARD, fg=MUTED, font=(f, 9, "bold")).pack(
                anchor="w", padx=16, pady=(15, 5)
            )
            box = tk.Frame(card, bg=CARD)
            box.pack(fill="x", padx=16)
            return box

        self.mode_var = tk.StringVar(value="separate")
        box = section("转换模式")
        ttk.Radiobutton(box, text="每个文件单独生成 PDF", variable=self.mode_var, value="separate").pack(anchor="w")
        ttk.Radiobutton(box, text="全部合并成一个 PDF", variable=self.mode_var, value="merge").pack(anchor="w", pady=(3, 0))

        box = section("页面设置")
        r1 = tk.Frame(box, bg=CARD)
        r1.pack(fill="x", pady=1)
        tk.Label(r1, text="纸张", bg=CARD, fg=INK, font=(f, 10), width=5, anchor="w").pack(side="left")
        self.page_var = tk.StringVar(value="A4")
        ttk.Combobox(r1, textvariable=self.page_var, values=PAGE_OPTIONS, state="readonly", width=11).pack(side="left")

        r2 = tk.Frame(box, bg=CARD)
        r2.pack(fill="x", pady=(8, 1))
        tk.Label(r2, text="方向", bg=CARD, fg=INK, font=(f, 10), width=5, anchor="w").pack(side="left")
        self.orient_var = tk.StringVar(value="跟随内容")
        ttk.Combobox(r2, textvariable=self.orient_var, values=list(ORIENT_LABEL), state="readonly", width=11).pack(side="left")

        r3 = tk.Frame(box, bg=CARD)
        r3.pack(fill="x", pady=(8, 1))
        tk.Label(r3, text="边距", bg=CARD, fg=INK, font=(f, 10), width=5, anchor="w").pack(side="left")
        self.margin_var = tk.StringVar(value="15")
        tk.Spinbox(
            r3,
            from_=0,
            to=60,
            increment=5,
            textvariable=self.margin_var,
            width=6,
            relief="flat",
            bg="#FFFFFF",
            fg=INK,
            font=(f, 10),
            highlightthickness=1,
            highlightbackground=BORDER,
            highlightcolor=ACCENT,
            buttonbackground="#F7F8FA",
            justify="center",
        ).pack(side="left")
        tk.Label(r3, text="mm", bg=CARD, fg=MUTED, font=(f, 9)).pack(side="left", padx=(6, 0))

        box = section("文档选项")
        self.pn_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(box, text="在页脚显示页码", variable=self.pn_var).pack(anchor="w")

        box = section("输出位置")
        row = tk.Frame(box, bg=CARD)
        row.pack(fill="x")
        default_out = os.path.join(os.path.expanduser("~"), "Desktop", "PDF输出")
        if not os.path.isdir(os.path.join(os.path.expanduser("~"), "Desktop")):
            default_out = os.path.join(os.path.expanduser("~"), "PDF输出")
        self.out_var = tk.StringVar(value=default_out)
        tk.Entry(
            row,
            textvariable=self.out_var,
            relief="flat",
            bg="#FBFCFD",
            fg=INK,
            font=(f, 9),
            highlightthickness=1,
            highlightbackground=BORDER,
            highlightcolor=ACCENT,
        ).pack(side="left", fill="x", expand=True, ipady=5)
        FlatButton(row, "浏览", self.choose_out, (f, 9), padx=11, pady=5).pack(side="left", padx=(8, 0))

        tk.Label(
            card,
            text="转换全程在本机完成，文件不会上传到任何服务器。",
            bg=CARD,
            fg=FAINT,
            font=(f, 8),
            wraplength=280,
            justify="left",
        ).pack(anchor="w", padx=16, pady=(18, 14), side="bottom")

    def _build_log_card(self) -> None:
        f = self.font
        card = tk.Frame(self, bg=CARD, highlightbackground=BORDER, highlightthickness=1)
        card.grid(row=2, column=0, sticky="ew", padx=18, pady=(0, 8))
        card.columnconfigure(0, weight=1)

        tk.Label(card, text="运行日志", bg=CARD, fg=MUTED, font=(f, 9, "bold")).grid(
            row=0, column=0, sticky="w", padx=14, pady=(8, 2)
        )
        wrap = tk.Frame(card, bg=CARD)
        wrap.grid(row=1, column=0, sticky="ew", padx=14, pady=(0, 10))
        wrap.columnconfigure(0, weight=1)
        self.log = tk.Text(
            wrap,
            height=4,
            bg="#FBFCFD",
            fg="#3C4450",
            relief="flat",
            font=(f, 9),
            wrap="word",
            padx=8,
            pady=6,
            highlightthickness=1,
            highlightbackground="#EDEFF3",
            state="disabled",
        )
        self.log.grid(row=0, column=0, sticky="ew")
        sb = ttk.Scrollbar(wrap, orient="vertical", command=self.log.yview)
        sb.grid(row=0, column=1, sticky="ns")
        self.log.configure(yscrollcommand=sb.set)
        self.log.tag_configure("ok", foreground=OK_GREEN)
        self.log.tag_configure("err", foreground=ERR_RED)
        self.log.tag_configure("dim", foreground=MUTED)

    def _build_footer(self) -> None:
        f = self.font
        footer = tk.Frame(self, bg=CARD, highlightbackground=BORDER, highlightthickness=1)
        footer.grid(row=3, column=0, sticky="ew", padx=18, pady=(0, 14))
        footer.columnconfigure(0, weight=1)

        self.status = tk.Label(footer, text="就绪 · 添加文件后点击「开始转换」", bg=CARD, fg=MUTED, font=(f, 9), anchor="w")
        self.status.grid(row=0, column=0, sticky="ew", padx=(16, 12), pady=(11, 4))

        self.progress = ProgressBar(footer)
        self.progress.grid(row=1, column=0, sticky="ew", padx=(16, 12), pady=(2, 14), ipady=0)

        self.btn_open = FlatButton(footer, "打开输出目录", self.open_out_dir, (f, 10), padx=13, pady=7)
        self.btn_open.grid(row=0, column=1, rowspan=2, padx=(0, 8), pady=10, sticky="e")
        self.btn_start = FlatButton(footer, "开始转换", self.start, (f, 11, "bold"), accent=True, padx=20, pady=7)
        self.btn_start.grid(row=0, column=2, rowspan=2, padx=(0, 14), pady=10, sticky="e")

    def _center(self) -> None:
        self.update_idletasks()
        w, h = 1010, 730
        x = (self.winfo_screenwidth() - w) // 2
        y = max((self.winfo_screenheight() - h) // 2 - 20, 0)
        self.geometry(f"{w}x{h}+{x}+{y}")

    # ------------------------------------------------------------ 文件列表操作
    def add_files(self) -> None:
        patterns = " ".join(f"*{e}" for e in sorted(SUPPORTED_EXTS))
        paths = filedialog.askopenfilenames(
            title="选择要转换的文件",
            filetypes=[("支持的文件", patterns), ("所有文件", "*.*")],
        )
        self._add(list(paths))

    def add_folder(self) -> None:
        folder = filedialog.askdirectory(title="选择文件夹（会扫描其中所有支持的文件）")
        if not folder:
            return
        found: list[str] = []
        for root, _dirs, files in os.walk(folder):
            for name in files:
                if os.path.splitext(name)[1].lower() in SUPPORTED_EXTS:
                    found.append(os.path.join(root, name))
            if len(found) > 500:
                break
        if not found:
            messagebox.showinfo("提示", "该文件夹中没有可转换的文件。")
            return
        self._add(sorted(found)[:500])

    def _add(self, paths: list[str]) -> None:
        exist = {it["path"] for it in self.items}
        added = 0
        for p in paths:
            p = os.path.abspath(p)
            if p in exist or not os.path.isfile(p):
                continue
            ext = os.path.splitext(p)[1].lower()
            try:
                size = os.path.getsize(p)
            except OSError:
                size = 0
            self.items.append(
                {
                    "path": p,
                    "kind": EXT_LABEL.get(ext, ext.upper().lstrip(".")),
                    "size": human_size(size),
                    "status": "待转换",
                    "tag": "",
                }
            )
            exist.add(p)
            added += 1
        self.refresh()
        if added:
            self.log_line(f"已添加 {added} 个文件，当前共 {len(self.items)} 个", "dim")
        self._update_idle_status()

    def refresh(self) -> None:
        for iid in self.tree.get_children():
            self.tree.delete(iid)
        for i, it in enumerate(self.items):
            self.tree.insert(
                "",
                "end",
                iid=str(i),
                values=(os.path.basename(it["path"]), it["kind"], it["size"], it["status"]),
                tags=(it["tag"],) if it["tag"] else (),
            )

    def _update_idle_status(self) -> None:
        if self.busy:
            return
        n = len(self.items)
        if n:
            self.status.configure(text=f"就绪 · 已添加 {n} 个文件，点击「开始转换」", fg=MUTED)
        else:
            self.status.configure(text="就绪 · 添加文件后点击「开始转换」", fg=MUTED)

    def _selected(self) -> list[int]:
        return sorted(int(i) for i in self.tree.selection())

    def remove_selected(self) -> None:
        idx = self._selected()
        if not idx or self.busy:
            return
        for i in reversed(idx):
            self.items.pop(i)
        self.refresh()
        self._update_idle_status()

    def clear_all(self) -> None:
        if self.busy:
            return
        self.items.clear()
        self.refresh()
        self.progress.reset()
        self._update_idle_status()

    def move(self, delta: int) -> None:
        if self.busy:
            return
        idx = self._selected()
        if len(idx) != 1:
            return
        i = idx[0]
        j = i + delta
        if 0 <= j < len(self.items):
            self.items[i], self.items[j] = self.items[j], self.items[i]
            self.refresh()
            self.tree.selection_set(str(j))
            self.tree.focus(str(j))

    def _open_item(self, _event=None) -> None:
        idx = self._selected()
        if not idx:
            return
        try:
            os.startfile(self.items[idx[0]]["path"])  # type: ignore[attr-defined]
        except Exception:
            pass

    # ------------------------------------------------------------------ 输出
    def choose_out(self) -> None:
        folder = filedialog.askdirectory(title="选择输出目录", initialdir=self.out_var.get() or None)
        if folder:
            self.out_var.set(folder)

    def open_out_dir(self) -> None:
        target = self.last_out_dir or self.out_var.get()
        if target and os.path.isdir(target):
            os.startfile(target)  # type: ignore[attr-defined]
        else:
            messagebox.showinfo("提示", "输出目录还不存在，转换完成后会自动创建。")

    # ------------------------------------------------------------------ 日志
    def log_line(self, text: str, tag: str = "") -> None:
        self.log.configure(state="normal")
        self.log.insert("end", text + "\n", tag)
        self.log.see("end")
        self.log.configure(state="disabled")

    def log_clear(self) -> None:
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.configure(state="disabled")

    # ------------------------------------------------------------------ 转换
    def _collect_options(self) -> Options:
        try:
            margin = float(self.margin_var.get())
        except ValueError:
            margin = 15.0
        margin = min(max(margin, 0.0), 60.0)
        return Options(
            merge=(self.mode_var.get() == "merge"),
            page_size=self.page_var.get(),
            orientation=ORIENT_LABEL.get(self.orient_var.get(), "portrait"),
            margin_mm=margin,
            out_dir=self.out_var.get().strip(),
            page_numbers=bool(self.pn_var.get()),
        )

    def start(self) -> None:
        if self.busy:
            return
        if not self.items:
            messagebox.showwarning("还没有文件", "请先添加要转换的文件。")
            return
        opts = self._collect_options()
        if not opts.out_dir:
            messagebox.showwarning("缺少输出目录", "请选择输出目录。")
            return

        paths = [it["path"] for it in self.items]
        for it in self.items:
            it["status"], it["tag"] = "排队中", ""
        self.refresh()
        self.log_clear()
        self.log_line(
            f"开始转换 {len(paths)} 个文件 → {'合并为一个 PDF' if opts.merge else '各自独立 PDF'}", "dim"
        )

        self.busy = True
        self.btn_start.set_enabled(False, "转换中…")
        self.progress.set_max(len(paths))
        self.progress.set(0)
        self.status.configure(text="正在准备…", fg=ACCENT)

        threading.Thread(target=self._work, args=(paths, opts), daemon=True).start()
        self.after(120, self._poll)

    def _work(self, paths: list[str], opts: Options) -> None:
        def cb(i: int, total: int, name: str) -> None:
            self.q.put(("progress", i, total, name))

        try:
            results = engine.run(paths, opts, cb)
            self.q.put(("done", results, opts.out_dir))
        except Exception as exc:  # noqa: BLE001
            self.q.put(("error", str(exc)))

    def _poll(self) -> None:
        finished = False
        while True:
            try:
                msg = self.q.get_nowait()
            except queue.Empty:
                break
            kind = msg[0]
            if kind == "progress":
                _, i, total, name = msg
                self.progress.set_max(total)
                self.progress.set(i)
                self.status.configure(text=f"正在转换 {i + 1}/{total}：{name}", fg=ACCENT)
                if i < len(self.items):
                    self.items[i]["status"], self.items[i]["tag"] = "转换中", "run"
                    self.tree.set(str(i), "status", "转换中")
                    self.tree.item(str(i), tags=("run",))
            elif kind == "done":
                _, results, out_dir = msg
                finished = True
                self.progress.finish()
                self.busy = False
                self.btn_start.set_enabled(True, "开始转换")
                self.last_out_dir = out_dir
                for it in self.items:
                    it["status"], it["tag"] = "完成", "ok"
                self.refresh()
                for r in results:
                    self.log_line(f"✔ 已生成：{r}", "ok")
                self.status.configure(text=f"转换完成 · 共 {len(results)} 个 PDF", fg=OK_GREEN)
                if results:
                    self._ask_open(results[0])
            elif kind == "error":
                finished = True
                self.busy = False
                self.btn_start.set_enabled(True, "开始转换")
                for it in self.items:
                    if it["status"] in ("排队中", "转换中"):
                        it["status"], it["tag"] = "失败", "err"
                self.refresh()
                self.log_line(f"✘ 转换失败：{msg[1]}", "err")
                self.status.configure(text="转换失败", fg=ERR_RED)
                messagebox.showerror("转换失败", msg[1])

        if not finished:
            self.after(120, self._poll)

    def _ask_open(self, first_pdf: str) -> None:
        if messagebox.askyesno("转换完成", "全部文件已转换完成。\n是否打开输出目录？"):
            try:
                os.startfile(os.path.dirname(first_pdf))  # type: ignore[attr-defined]
            except Exception:
                pass


def main() -> None:
    import sys

    # 隐藏自检模式：PDF转换工坊.exe --selftest
    if "--selftest" in sys.argv:
        from selftest import run as run_selftest

        report = run_selftest()
        base = (
            os.path.dirname(sys.executable)
            if getattr(sys, "frozen", False)
            else os.path.dirname(os.path.abspath(__file__))
        )
        with open(os.path.join(base, "自检结果.txt"), "w", encoding="utf-8") as fh:
            fh.write(report)
        return

    try:
        import ctypes

        ctypes.windll.shcore.SetProcessDpiAwareness(1)  # type: ignore[attr-defined]
    except Exception:
        pass
    try:
        App().mainloop()
    except Exception:
        import traceback

        detail = traceback.format_exc()
        try:
            base = (
                os.path.dirname(sys.executable)
                if getattr(sys, "frozen", False)
                else os.path.dirname(os.path.abspath(__file__))
            )
            with open(os.path.join(base, "启动错误.log"), "w", encoding="utf-8") as fh:
                fh.write(detail)
        except Exception:
            pass
        try:
            messagebox.showerror("程序异常", detail[-1200:])
        except Exception:
            pass


if __name__ == "__main__":
    main()
