# -*- coding: utf-8 -*-
"""
uni-pdf — PDF 변환 무료 유틸리티 (Windows/macOS 단일 실행파일 배포)

기능
  1) PDF → JPG   : 페이지별 이미지 저장. 파일명 "<이름>_1.jpg …". 원본 해상도 유지(고DPI).
  2) JPG → PDF   : 여러 이미지를 한 PDF로 묶기. 원본 화질 그대로 임베드.
  3) PDF 편집    : 페이지를 썸네일로 보며 순서 변경 · 삭제 · 다른 PDF 추가.
  4) 정보        : 버전 · 개발 정보 · 오픈소스 라이선스 고지.

UI: CustomTkinter (둥근 모서리·색·Pretendard). 좌측 사이드바 + 우측 콘텐츠 (macOS 스타일).
    디자인 정본 = Claude Design "Uniflow PDF 변환기 재설계" (uni-pdf.dc.html).

라이선스 깨끗한 조합만: pypdfium2(BSD) · Pillow(HPND) · pypdf(BSD) ·
  customtkinter(CC0/MIT) · darkdetect(BSD-3) · Pretendard(SIL OFL).
빌드(win): pyinstaller --onefile --windowed --name uni-pdf --collect-all customtkinter --add-data "fonts;fonts" uni_pdf.py
빌드(mac): ./build_mac.sh
"""
import os
import sys
import threading
import webbrowser

import customtkinter as ctk
from tkinter import filedialog, messagebox, font as tkfont

import pypdfium2 as pdfium
from PIL import Image
from pypdf import PdfReader, PdfWriter

APP_VERSION = "1.0"

# ── Apple 스타일 색 토큰 (디자인 정본) ──────────────────
CARD     = "#FFFFFF"
SIDE     = "#F6F6F8"
ACCENT   = "#0071E3"
ACCENT_D = "#0058B0"
INK      = "#1D1D1F"
SUB      = "#8A8A8E"
SUB2     = "#6E6E73"
LINE     = "#E3E3E7"
FIELD    = "#FBFBFC"
FLINE    = "#DDDDE2"
SEG      = "#EFEFF2"
NAV_HOV  = "#ECECEF"
DANGER_BG = "#FFF6F6"; DANGER_FG = "#C7362F"; DANGER_HOV = "#FDECEC"; DANGER_LINE = "#E4C6C6"
ADD_BG = "#EDF4FF"; ADD_FG = "#0060DA"; ADD_HOV = "#E2EEFF"; ADD_LINE = "#C9DFFF"
GRID_BG = "#FAFAFC"
CARD_LINE = "#E0E0E6"
SEL_BG = "#EDF4FF"

FONT = "Pretendard"


def resource_path(rel):
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, rel)


def load_embedded_fonts():
    """시스템 설치 없이 프로세스에 Pretendard 등록 (mac/win). 실패해도 폴백 폰트로 동작."""
    files = [resource_path(os.path.join("fonts", n)) for n in
             ("Pretendard-Regular.ttf", "Pretendard-SemiBold.ttf", "Pretendard-Bold.ttf")]
    files = [f for f in files if os.path.isfile(f)]
    if not files:
        return
    try:
        if sys.platform == "darwin":
            import ctypes
            from ctypes import util, c_void_p, c_bool, c_char_p, c_long
            cf = ctypes.CDLL(util.find_library("CoreFoundation"))
            ct = ctypes.CDLL(util.find_library("CoreText"))
            cf.CFStringCreateWithCString.restype = c_void_p
            cf.CFStringCreateWithCString.argtypes = [c_void_p, c_char_p, c_long]
            cf.CFURLCreateWithFileSystemPath.restype = c_void_p
            cf.CFURLCreateWithFileSystemPath.argtypes = [c_void_p, c_void_p, c_long, c_bool]
            ct.CTFontManagerRegisterFontsForURL.restype = c_bool
            ct.CTFontManagerRegisterFontsForURL.argtypes = [c_void_p, c_long, c_void_p]
            UTF8, POSIX, SCOPE_PROCESS = 0x08000100, 0, 1
            for path in files:
                s = cf.CFStringCreateWithCString(None, path.encode("utf-8"), UTF8)
                url = cf.CFURLCreateWithFileSystemPath(None, s, POSIX, False)
                ct.CTFontManagerRegisterFontsForURL(url, SCOPE_PROCESS, None)
        elif sys.platform.startswith("win"):
            import ctypes
            for path in files:
                ctypes.windll.gdi32.AddFontResourceExW(ctypes.c_wchar_p(path), 0x10, 0)
    except Exception:
        pass


def has_pretendard():
    try:
        return "Pretendard" in set(tkfont.families())
    except Exception:
        return False


def F(size, bold=False):
    return ctk.CTkFont(family=FONT, size=size, weight="bold" if bold else "normal")


# ── 버튼 헬퍼 ────────────────────────────────────────────
def primary(parent, text, cmd, w=None):
    return ctk.CTkButton(parent, text=text, command=cmd, corner_radius=10, height=44,
                         fg_color=ACCENT, hover_color=ACCENT_D, text_color="#FFFFFF",
                         font=F(14, True), width=(w or 140))


def secondary(parent, text, cmd, w=None):
    return ctk.CTkButton(parent, text=text, command=cmd, corner_radius=8, height=36,
                         fg_color="#FFFFFF", hover_color="#F0F0F3", text_color=INK,
                         border_width=1, border_color=FLINE, font=F(13), width=(w or 76))


def danger(parent, text, cmd, w=None):
    return ctk.CTkButton(parent, text=text, command=cmd, corner_radius=8, height=36,
                         fg_color=DANGER_BG, hover_color=DANGER_HOV, text_color=DANGER_FG,
                         border_width=1, border_color=DANGER_LINE, font=F(13), width=(w or 72))


def add_btn(parent, text, cmd, w=None):
    return ctk.CTkButton(parent, text=text, command=cmd, corner_radius=8, height=36,
                         fg_color=ADD_BG, hover_color=ADD_HOV, text_color=ADD_FG,
                         border_width=1, border_color=ADD_LINE, font=F(13, True), width=(w or 80))


def lbl(parent, text, size=13, color=INK, bold=False, fg="transparent", h=None):
    kw = dict(text=text, font=F(size, bold), text_color=color, fg_color=fg)
    if h is not None:
        kw["height"] = h          # CTkLabel 기본 높이가 커서, 촘촘히 붙일 땐 명시
    return ctk.CTkLabel(parent, **kw)


def linkify(widget, url, base_color=None):
    """라벨을 클릭 가능한 링크로 — 손 커서만(색 변화 없음)."""
    widget.configure(cursor="hand2")
    widget.bind("<Button-1>", lambda e: webbrowser.open(url))


# ─────────────────────────────────────────────────────────
# 1) PDF → JPG
# ─────────────────────────────────────────────────────────
class JpgView(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color=CARD, corner_radius=0)
        self.pdf_path = ctk.StringVar()
        self.out_dir = ctk.StringVar()
        self.prefix = ctk.StringVar()
        self.dpi = ctk.StringVar(value="300")
        self._build()

    def _entry_row(self, title, var, btn_text=None, btn_cmd=None, hint=None):
        box = ctk.CTkFrame(self.pad, fg_color="transparent")
        box.pack(fill="x", pady=(0, 20))
        lbl(box, title, 12, SUB2, True).pack(anchor="w", pady=(0, 7))
        row = ctk.CTkFrame(box, fg_color="transparent")
        row.pack(fill="x")
        e = ctk.CTkEntry(row, textvariable=var, height=40, corner_radius=8,
                         fg_color=FIELD, border_color=FLINE, border_width=1,
                         text_color=INK, font=F(13))
        e.pack(side="left", fill="x", expand=True)
        if btn_text:
            secondary(row, btn_text, btn_cmd).pack(side="left", padx=(10, 0))
        if hint:
            lbl(row, hint, 12, SUB).pack(side="left", padx=(12, 0))

    def _build(self):
        self.pad = ctk.CTkFrame(self, fg_color="transparent")
        self.pad.pack(fill="both", expand=True, padx=40, pady=30)

        self._entry_row("PDF 파일", self.pdf_path, "찾기", self._pick_pdf)
        self._entry_row("저장 폴더", self.out_dir, "찾기", self._pick_dir)
        self._entry_row("파일 이름", self.prefix, hint="→ 이름_1.jpg, 이름_2.jpg …")

        seg_box = ctk.CTkFrame(self.pad, fg_color="transparent")
        seg_box.pack(fill="x", pady=(0, 24))
        head = ctk.CTkFrame(seg_box, fg_color="transparent")
        head.pack(anchor="w", pady=(0, 8))
        lbl(head, "해상도", 12, SUB2, True).pack(side="left")
        lbl(head, "  클수록 선명하지만 파일이 큽니다 · 기본 300", 12, SUB).pack(side="left")
        ctk.CTkSegmentedButton(
            seg_box, values=["150", "200", "300", "600"], variable=self.dpi,
            font=F(13), corner_radius=8, height=34,
            fg_color=SEG, selected_color="#FFFFFF", selected_hover_color="#FFFFFF",
            unselected_color=SEG, unselected_hover_color="#E7E7EB",
            text_color=INK, text_color_disabled=SUB).pack(anchor="w")

        act = ctk.CTkFrame(self.pad, fg_color="transparent")
        act.pack(fill="x", pady=(6, 0))
        self.btn = primary(act, "JPG로 변환", self._convert, w=150)
        self.btn.pack(side="left")
        self.status = lbl(act, "", 12, SUB)
        self.status.pack(side="left", padx=(16, 0))

    def _pick_pdf(self):
        p = filedialog.askopenfilename(title="PDF 선택", filetypes=[("PDF", "*.pdf")])
        if p:
            self.pdf_path.set(p)
            if not self.out_dir.get():
                self.out_dir.set(os.path.dirname(p))
            if not self.prefix.get():
                self.prefix.set(os.path.splitext(os.path.basename(p))[0])

    def _pick_dir(self):
        d = filedialog.askdirectory(title="저장 폴더 선택")
        if d:
            self.out_dir.set(d)

    def _convert(self):
        pdf, out = self.pdf_path.get().strip(), self.out_dir.get().strip()
        prefix = self.prefix.get().strip() or "page"
        dpi = int(self.dpi.get())
        if not pdf or not os.path.isfile(pdf):
            messagebox.showwarning("uni-pdf", "PDF 파일을 선택해 주세요."); return
        if not out or not os.path.isdir(out):
            messagebox.showwarning("uni-pdf", "저장 폴더를 선택해 주세요."); return
        self.btn.configure(state="disabled")
        self.status.configure(text="변환 중…")

        def work():
            try:
                doc = pdfium.PdfDocument(pdf)
                n = len(doc); scale = dpi / 72.0
                for i in range(n):
                    img = doc[i].render(scale=scale).to_pil().convert("RGB")
                    img.save(os.path.join(out, f"{prefix}_{i+1}.jpg"),
                             "JPEG", quality=95, subsampling=0)
                    self.after(0, lambda i=i, n=n: self.status.configure(text=f"변환 중… {i+1}/{n}"))
                doc.close()
                self.after(0, lambda: self._done(n, out))
            except Exception as e:
                self.after(0, lambda e=e: self._fail(e))
        threading.Thread(target=work, daemon=True).start()

    def _done(self, n, out):
        self.btn.configure(state="normal")
        self.status.configure(text=f"완료 — {n}장 저장됨")
        messagebox.showinfo("uni-pdf", f"{n}장을 저장했습니다.\n{out}")

    def _fail(self, e):
        self.btn.configure(state="normal")
        self.status.configure(text="실패")
        messagebox.showerror("uni-pdf", f"변환 중 오류가 발생했습니다.\n\n{e}")


# ─────────────────────────────────────────────────────────
# 2) JPG → PDF
# ─────────────────────────────────────────────────────────
class PdfView(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color=CARD, corner_radius=0)
        self.paths = []
        self.sel = None
        self._build()

    def _build(self):
        pad = ctk.CTkFrame(self, fg_color="transparent")
        pad.pack(fill="both", expand=True, padx=32, pady=22)

        top = ctk.CTkFrame(pad, fg_color="transparent")
        top.pack(fill="x", pady=(0, 12))
        lbl(top, "위 → 아래 순서대로 한 개의 PDF로 묶입니다", 12, SUB).pack(side="left")
        add_btn(top, "＋ 추가", self._add).pack(side="right")
        danger(top, "비우기", self._clear).pack(side="right", padx=(0, 8))
        danger(top, "삭제", self._remove).pack(side="right", padx=(0, 8))
        secondary(top, "↓ 아래로", lambda: self._move(1), w=84).pack(side="right", padx=(0, 8))
        secondary(top, "↑ 위로", lambda: self._move(-1), w=76).pack(side="right", padx=(0, 8))

        self.listbox = ctk.CTkScrollableFrame(pad, fg_color="#FCFCFD", corner_radius=10,
                                              border_width=1, border_color=LINE)
        self.listbox.pack(fill="both", expand=True)

        bottom = ctk.CTkFrame(pad, fg_color="transparent")
        bottom.pack(fill="x", pady=(12, 0))
        self.count = lbl(bottom, "0개 이미지", 12, SUB)
        self.count.pack(side="left")
        self.btn = primary(bottom, "PDF로 묶기", self._convert, w=150)
        self.btn.pack(side="right")
        self.status = lbl(bottom, "", 12, SUB)
        self.status.pack(side="right", padx=(0, 14))
        self._refresh()

    def _refresh(self):
        for w in self.listbox.winfo_children():
            w.destroy()
        if not self.paths:
            lbl(self.listbox, "이미지를 ‘＋ 추가’로 넣으세요", 13, "#B0B0B6").pack(pady=90)
        for i, p in enumerate(self.paths):
            on = (i == self.sel)
            row = ctk.CTkFrame(self.listbox, fg_color=(SEL_BG if on else "#FCFCFD"),
                               corner_radius=8, height=52)
            row.pack(fill="x", pady=2, padx=2)
            lbl(row, f"{i+1}", 12, SUB).pack(side="left", padx=(12, 8))
            name = lbl(row, os.path.basename(p), 13, INK, on)
            name.pack(side="left", pady=10)
            try:
                w, h = Image.open(p).size
                lbl(row, f"  ·  {w} × {h}", 12, SUB).pack(side="left")
            except Exception:
                pass
            row.bind("<Button-1>", lambda e, i=i: self._select(i))
            name.bind("<Button-1>", lambda e, i=i: self._select(i))
        self.count.configure(text=f"{len(self.paths)}개 이미지")

    def _select(self, i):
        self.sel = i; self._refresh()

    def _add(self):
        for p in filedialog.askopenfilenames(
                title="이미지 선택",
                filetypes=[("이미지", "*.jpg *.jpeg *.png *.bmp *.webp")]):
            self.paths.append(p)
        self._refresh()

    def _move(self, d):
        i = self.sel
        if i is None or (d < 0 and i == 0) or (d > 0 and i == len(self.paths) - 1):
            return
        self.paths[i + d], self.paths[i] = self.paths[i], self.paths[i + d]
        self.sel = i + d; self._refresh()

    def _remove(self):
        if self.sel is None:
            return
        del self.paths[self.sel]; self.sel = None; self._refresh()

    def _clear(self):
        self.paths = []; self.sel = None; self._refresh()

    def _convert(self):
        if not self.paths:
            messagebox.showwarning("uni-pdf", "이미지를 추가해 주세요."); return
        out = filedialog.asksaveasfilename(title="PDF 저장", defaultextension=".pdf",
                                           filetypes=[("PDF", "*.pdf")])
        if not out:
            return
        self.btn.configure(state="disabled"); self.status.configure(text="묶는 중…")
        paths = list(self.paths)

        def work():
            try:
                imgs = [Image.open(p).convert("RGB") for p in paths]
                imgs[0].save(out, "PDF", save_all=True, append_images=imgs[1:])
                self.after(0, lambda: self._done(len(imgs), out))
            except Exception as e:
                self.after(0, lambda e=e: self._fail(e))
        threading.Thread(target=work, daemon=True).start()

    def _done(self, n, out):
        self.btn.configure(state="normal")
        self.status.configure(text=f"완료 — {n}장 → PDF")
        messagebox.showinfo("uni-pdf", f"{n}장을 PDF로 묶었습니다.\n{out}")

    def _fail(self, e):
        self.btn.configure(state="normal"); self.status.configure(text="실패")
        messagebox.showerror("uni-pdf", f"오류가 발생했습니다.\n\n{e}")


# ─────────────────────────────────────────────────────────
# 3) PDF 편집 — 5열 썸네일 그리드
# ─────────────────────────────────────────────────────────
class EditView(ctk.CTkFrame):
    COLS = 5
    TW = 130

    def __init__(self, master):
        super().__init__(master, fg_color=CARD, corner_radius=0)
        self.items = []
        self.thumbs = {}
        self.selected = set()
        self._build()

    def _build(self):
        pad = ctk.CTkFrame(self, fg_color="transparent")
        pad.pack(fill="both", expand=True, padx=28, pady=20)

        top = ctk.CTkFrame(pad, fg_color="transparent")
        top.pack(fill="x", pady=(0, 12))
        secondary(top, "PDF 열기", self._open, w=90).pack(side="left")
        secondary(top, "다른 PDF 추가", self._append, w=120).pack(side="left", padx=(8, 0))
        self.selinfo = lbl(top, "카드를 눌러 선택하세요", 12, SUB)
        self.selinfo.pack(side="right")

        self.grid = ctk.CTkScrollableFrame(pad, fg_color=GRID_BG, corner_radius=10,
                                           border_width=1, border_color=LINE)
        self.grid.pack(fill="both", expand=True)

        bottom = ctk.CTkFrame(pad, fg_color="transparent")
        bottom.pack(fill="x", pady=(12, 0))
        secondary(bottom, "◀ 앞으로", lambda: self._move(-1), w=90).pack(side="left")
        secondary(bottom, "뒤로 ▶", lambda: self._move(1), w=84).pack(side="left", padx=(8, 0))
        danger(bottom, "선택 삭제", self._remove, w=90).pack(side="left", padx=(8, 0))
        self.count = lbl(bottom, "", 12, SUB)
        self.count.pack(side="left", padx=(10, 0))
        self.btn = primary(bottom, "PDF로 저장", self._save, w=140)
        self.btn.pack(side="right")

    def _open(self):
        p = filedialog.askopenfilename(title="PDF 열기", filetypes=[("PDF", "*.pdf")])
        if p:
            self._load(p, False)

    def _append(self):
        p = filedialog.askopenfilename(title="추가할 PDF", filetypes=[("PDF", "*.pdf")])
        if p:
            self._load(p, True)

    def _load(self, path, append):
        try:
            n = len(PdfReader(path).pages)
        except Exception as e:
            messagebox.showerror("uni-pdf", f"PDF를 열 수 없습니다.\n\n{e}"); return
        if not append:
            self.items, self.thumbs, self.selected = [], {}, set()
        for i in range(n):
            self.items.append((path, i))
        self._render()
        self._render_thumbs()

    def _render(self):
        for w in self.grid.winfo_children():
            w.destroy()
        self.cards = []
        for idx, (path, pidx) in enumerate(self.items):
            r, c = divmod(idx, self.COLS)
            on = idx in self.selected
            card = ctk.CTkFrame(self.grid, fg_color="#FFFFFF", corner_radius=8,
                                border_width=2, border_color=(ACCENT if on else CARD_LINE))
            card.grid(row=r, column=c, padx=8, pady=8)
            key = (path, pidx)
            if key in self.thumbs:
                im = ctk.CTkLabel(card, image=self.thumbs[key], text="")
            else:
                im = ctk.CTkLabel(card, text="…", text_color=SUB,
                                  width=self.TW, height=int(self.TW * 0.75), font=F(12))
            im.pack(padx=6, pady=6)
            num = lbl(card, f"{idx+1}", 12, (ACCENT if on else SUB), on)
            num.pack(pady=(0, 6))
            for w in (card, im, num):
                w.bind("<Button-1>", lambda e, i=idx: self._toggle(i))
            self.cards.append((card, im))
        self.count.configure(text=f"{len(self.items)}쪽" if self.items else "")
        s = len(self.selected)
        self.selinfo.configure(text=f"{s}쪽 선택됨" if s else "카드를 눌러 선택하세요")

    def _render_thumbs(self):
        todo = [k for k in {(p, i) for p, i in self.items} if k not in self.thumbs]
        if not todo:
            return
        def work():
            for path, pidx in todo:
                try:
                    doc = pdfium.PdfDocument(path)
                    im = doc[pidx].render(scale=0.5).to_pil().convert("RGB")
                    doc.close()
                    im.thumbnail((self.TW, int(self.TW * 1.5)))
                    self.after(0, lambda k=(path, pidx), im=im: self._set_thumb(k, im))
                except Exception:
                    pass
        threading.Thread(target=work, daemon=True).start()

    def _set_thumb(self, key, im):
        cimg = ctk.CTkImage(light_image=im, size=im.size)
        self.thumbs[key] = cimg
        for idx, (path, pidx) in enumerate(self.items):
            if (path, pidx) == key and idx < len(self.cards):
                _, im_lbl = self.cards[idx]
                im_lbl.configure(image=cimg, text="")

    def _toggle(self, idx):
        self.selected.discard(idx) if idx in self.selected else self.selected.add(idx)
        self._render()

    def _move(self, d):
        if not self.selected:
            return
        order = sorted(self.selected)
        if (d < 0 and order[0] == 0) or (d > 0 and order[-1] == len(self.items) - 1):
            return
        for i in (order if d < 0 else reversed(order)):
            self.items[i + d], self.items[i] = self.items[i], self.items[i + d]
        self.selected = {i + d for i in self.selected}
        self._render()

    def _remove(self):
        if not self.selected:
            messagebox.showinfo("uni-pdf", "삭제할 페이지를 먼저 선택해 주세요."); return
        self.items = [it for i, it in enumerate(self.items) if i not in self.selected]
        self.selected = set(); self._render()

    def _save(self):
        if not self.items:
            messagebox.showwarning("uni-pdf", "페이지가 없습니다. PDF를 먼저 열어 주세요."); return
        out = filedialog.asksaveasfilename(title="PDF 저장", defaultextension=".pdf",
                                           filetypes=[("PDF", "*.pdf")])
        if not out:
            return
        items = list(self.items)

        def work():
            try:
                readers, writer = {}, PdfWriter()
                for path, pidx in items:
                    if path not in readers:
                        readers[path] = PdfReader(path)
                    writer.add_page(readers[path].pages[pidx])
                with open(out, "wb") as f:
                    writer.write(f)
                self.after(0, lambda: messagebox.showinfo(
                    "uni-pdf", f"{len(items)}쪽 PDF를 저장했습니다.\n{out}"))
            except Exception as e:
                self.after(0, lambda e=e: messagebox.showerror(
                    "uni-pdf", f"오류가 발생했습니다.\n\n{e}"))
        threading.Thread(target=work, daemon=True).start()


# ─────────────────────────────────────────────────────────
# 4) 정보
# ─────────────────────────────────────────────────────────
class InfoView(ctk.CTkFrame):
    LIBS = [
        ("Python 3.14", "PSF License"),
        ("Tcl/Tk", "BSD 계열"),
        ("CustomTkinter", "CC0 / MIT"),
        ("pypdfium2 · PDFium", "BSD-3-Clause"),
        ("Pillow", "MIT-CMU (HPND)"),
        ("pypdf", "BSD-3-Clause"),
        ("Pretendard", "SIL Open Font License 1.1"),
    ]

    def __init__(self, master):
        super().__init__(master, fg_color=CARD, corner_radius=0)
        pad = ctk.CTkFrame(self, fg_color="transparent")
        pad.pack(fill="both", expand=True, padx=44, pady=36)

        head = ctk.CTkFrame(pad, fg_color="transparent")
        head.pack(fill="x")
        badge = ctk.CTkFrame(head, fg_color=ACCENT, corner_radius=14, width=58, height=58)
        badge.pack(side="left"); badge.pack_propagate(False)
        lbl(badge, "uni", 18, "#FFFFFF", True).place(relx=0.5, rely=0.5, anchor="center")
        ht = ctk.CTkFrame(head, fg_color="transparent")
        ht.pack(side="left", padx=16)
        lbl(ht, "uni-pdf", 22, INK, True).pack(anchor="w")
        lbl(ht, f"버전 {APP_VERSION} · PDF ↔ JPG 변환 · PDF 페이지 편집", 12, SUB).pack(anchor="w")

        ctk.CTkFrame(pad, height=1, fg_color=LINE).pack(fill="x", pady=22)

        lbl(pad, "만든 곳", 12, INK, True, h=17).pack(anchor="w")
        made = lbl(pad, "uniflow.kr", 13, SUB2, h=20)
        made.pack(anchor="w", pady=(4, 0))
        linkify(made, "https://uniflow.kr", base_color=SUB2)
        mail = lbl(pad, "문의: uniflow.kr@gmail.com", 13, SUB2, h=20)
        mail.pack(anchor="w", pady=(0, 18))
        linkify(mail, "mailto:uniflow.kr@gmail.com", base_color=SUB2)

        lbl(pad, "오픈소스 라이선스", 12, INK, True).pack(anchor="w", pady=(0, 8))
        table = ctk.CTkFrame(pad, fg_color="#FCFCFD", corner_radius=10,
                             border_width=1, border_color="#E9E9ED")
        table.pack(anchor="w", fill="x")
        for i, (name, lic) in enumerate(self.LIBS):
            row = ctk.CTkFrame(table, fg_color="transparent")
            row.pack(fill="x", padx=16, pady=7)
            lbl(row, name, 13, INK, h=18).pack(side="left")
            lbl(row, lic, 12, SUB, h=18).pack(side="right")
            if i < len(self.LIBS) - 1:
                ctk.CTkFrame(table, height=1, fg_color="#F0F0F3").pack(fill="x")

        lbl(pad, "이용 조건", 12, INK, True).pack(anchor="w", pady=(18, 6))
        lbl(pad, "무료로 사용할 수 있습니다. 수정 · 재배포 · 판매는 금지됩니다.",
            13, SUB2).pack(anchor="w")
        lbl(pad, "© 2026 uniflow.kr · 무료 배포", 11, SUB).pack(anchor="w", pady=(14, 0))


# ─────────────────────────────────────────────────────────
class App(ctk.CTk):
    NAV = [
        ("jpg",  "▤", "PDF → JPG", "PDF 각 쪽을 이미지로 저장합니다"),
        ("pdf",  "▦", "JPG → PDF", "여러 이미지를 하나의 PDF로 묶습니다"),
        ("edit", "✂", "PDF 편집",  "쪽 순서를 바꾸거나 지웁니다"),
        ("info", "ⓘ", "정보",      "버전 및 오픈소스 라이선스"),
    ]

    def __init__(self):
        super().__init__()
        global FONT
        FONT = ("Pretendard" if has_pretendard()
                else ("Apple SD Gothic Neo" if "Apple SD Gothic Neo" in set(tkfont.families())
                      else "Helvetica"))
        self.title("uni-pdf — PDF 변환기")
        self.geometry("1040x700")
        self.minsize(940, 640)
        self.configure(fg_color=CARD)

        # 사이드바
        side = ctk.CTkFrame(self, width=236, fg_color=SIDE, corner_radius=0)
        side.pack(side="left", fill="y"); side.pack_propagate(False)

        brand = ctk.CTkFrame(side, fg_color="transparent")
        brand.pack(fill="x", padx=18, pady=(18, 20))
        badge = ctk.CTkFrame(brand, fg_color=ACCENT, corner_radius=9, width=36, height=36)
        badge.pack(side="left"); badge.pack_propagate(False)
        lbl(badge, "uni", 13, "#FFFFFF", True).place(relx=0.5, rely=0.5, anchor="center")
        bt = ctk.CTkFrame(brand, fg_color="transparent")
        bt.pack(side="left", padx=11)
        lbl(bt, "uni-pdf", 14, INK, True, h=19).pack(anchor="w")
        lbl(bt, "버전 1.0 · 무료 배포", 11, SUB, h=15).pack(anchor="w")

        lbl(side, "작업", 11, "#9A9AA0", True, h=16).pack(anchor="w", padx=22, pady=(0, 6))
        self.nav_btns = {}
        for key, icon, text, _ in self.NAV:
            b = ctk.CTkButton(side, text=f"  {icon}   {text}", anchor="w",
                              corner_radius=7, height=38, font=F(13),
                              fg_color="transparent", text_color="#3A3A3E",
                              hover_color=NAV_HOV, command=lambda k=key: self.show(k))
            b.pack(fill="x", padx=10, pady=1)
            self.nav_btns[key] = b

        foot = ctk.CTkFrame(side, fg_color="transparent")
        foot.pack(side="bottom", fill="x", padx=20, pady=16)
        lbl(foot, "모든 변환은 이 컴퓨터에서만\n처리됩니다. 업로드 없음.", 11, "#9A9AA0").pack(anchor="w")

        # 오른쪽: 헤더 + 콘텐츠
        right = ctk.CTkFrame(self, fg_color=CARD, corner_radius=0)
        right.pack(side="left", fill="both", expand=True)
        header = ctk.CTkFrame(right, fg_color=CARD, corner_radius=0, height=60)
        header.pack(fill="x"); header.pack_propagate(False)
        htext = ctk.CTkFrame(header, fg_color="transparent")
        htext.place(x=24, rely=0.5, anchor="w")           # 세로 중앙 정렬
        self.h_title = lbl(htext, "", 15, INK, True, h=20)
        self.h_title.pack(anchor="w")
        self.h_sub = lbl(htext, "", 11, SUB, h=15)
        self.h_sub.pack(anchor="w")
        hlink = lbl(header, "uniflow.kr", 11, "#A0A0A6")
        hlink.place(relx=1.0, rely=0.5, anchor="e", x=-24)
        linkify(hlink, "https://uniflow.kr", base_color="#A0A0A6")
        ctk.CTkFrame(right, height=1, fg_color="#ECECEF").pack(fill="x")

        self.container = ctk.CTkFrame(right, fg_color=CARD, corner_radius=0)
        self.container.pack(fill="both", expand=True)
        self.views = {"jpg": JpgView(self.container), "pdf": PdfView(self.container),
                      "edit": EditView(self.container), "info": InfoView(self.container)}
        self.current = None
        self.show("jpg")

    def show(self, key):
        if self.current:
            self.views[self.current].pack_forget()
        self.views[key].pack(fill="both", expand=True)
        self.current = key
        for k, b in self.nav_btns.items():
            sel = (k == key)
            b.configure(fg_color=(ACCENT if sel else "transparent"),
                        text_color=("#FFFFFF" if sel else "#3A3A3E"),
                        hover_color=(ACCENT_D if sel else NAV_HOV),
                        font=F(13, sel))
        meta = next(x for x in self.NAV if x[0] == key)
        self.h_title.configure(text=meta[2]); self.h_sub.configure(text=meta[3])


def main():
    # DPI awareness 는 CustomTkinter 가 자동 처리한다(수동 호출 시 오히려 흐려짐).
    load_embedded_fonts()
    ctk.set_appearance_mode("light")
    App().mainloop()


if __name__ == "__main__":
    main()
