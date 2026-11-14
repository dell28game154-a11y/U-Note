"""
U NOTE
Notepad++ pratikliği + modern (VS tarzı) görünüm.
Çalıştırmak için:  pip install PyQt6   ->   python U_NOTE.py
"""
import os
import re
import sys

try:
    import PyQt6  # noqa: F401
except ImportError:
    print("PyQt6 kurulu değil. Önce şunu çalıştır:\n\n    pip install PyQt6\n")
    input("Kapatmak için Enter'a bas...")
    sys.exit(1)

from PyQt6.QtCore import QEvent, QPoint, QPointF, QRect, QRectF, QSettings, QSize, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import (
    QAction, QActionGroup, QColor, QFont, QIcon, QKeySequence, QPainter,
    QPainterPath, QPen, QPixmap, QSyntaxHighlighter, QTextCharFormat,
    QTextCursor, QTextDocument, QTextFormat,
)
from PyQt6.QtWidgets import (
    QApplication, QFileDialog, QHBoxLayout, QInputDialog, QLabel, QLineEdit,
    QListWidget, QListWidgetItem, QMainWindow, QMessageBox, QPlainTextEdit,
    QPushButton, QTabWidget, QTextEdit, QToolBar, QWidget, QVBoxLayout,
)

APP_NAME = "U NOTE"

# --------------------------------------------------------------------------
# TEMALAR
# --------------------------------------------------------------------------
THEMES = {
    "Camgöbeği": dict(
        bg="#0f1e24", fg="#d6f3f7", panel="#0b171c", panel2="#14313a",
        accent="#00bcd4", border="#1d4350", gutter_bg="#0c1a1f",
        gutter_fg="#4d7a86", gutter_active="#5ee7f7", line="#15303a",
        sel="#1b6577", keyword="#4dd0e1", string="#a5d6a7",
        comment="#5f8a94", number="#ffcc80", logo_line="#06323a",
    ),
    "Gece": dict(
        bg="#1e1e1e", fg="#d4d4d4", panel="#181818", panel2="#2a2a2a",
        accent="#3794ff", border="#333333", gutter_bg="#1b1b1b",
        gutter_fg="#6e7681", gutter_active="#c6c6c6", line="#282828",
        sel="#264f78", keyword="#569cd6", string="#ce9178",
        comment="#6a9955", number="#b5cea8", logo_line="#0b0b0b",
    ),
    "Açık": dict(
        bg="#ffffff", fg="#1f2328", panel="#f3f3f3", panel2="#e4e4e4",
        accent="#0099aa", border="#d0d7de", gutter_bg="#f7f7f7",
        gutter_fg="#8c959f", gutter_active="#1f2328", line="#eef6f8",
        sel="#b3e5ec", keyword="#0550ae", string="#0a7a3d",
        comment="#6e7781", number="#b35900", logo_line="#06323a",
    ),
    "Gün Batımı": dict(
        bg="#231a1f", fg="#f3e3dc", panel="#1a1217", panel2="#34242c",
        accent="#ff8a50", border="#4a3340", gutter_bg="#1d151a",
        gutter_fg="#8a6b78", gutter_active="#ffb590", line="#2e2229",
        sel="#6b3a2a", keyword="#ff9e64", string="#9ece6a",
        comment="#8a6b78", number="#e0af68", logo_line="#2b0f00",
    ),
    "Orman": dict(
        bg="#14201a", fg="#dcefe2", panel="#0f1914", panel2="#1e3328",
        accent="#4caf7a", border="#2a4a39", gutter_bg="#111c16",
        gutter_fg="#5d8570", gutter_active="#a6e8c3", line="#1a2c22",
        sel="#2c6b4a", keyword="#7bd9a4", string="#e6d08a",
        comment="#6a9480", number="#f0a672", logo_line="#06240f",
    ),
}
DEFAULT_THEME = "Camgöbeği"


# --------------------------------------------------------------------------
# U LOGOSU (elle çizilmiş U: dış çizgi siyah/koyu, içi tema rengi)
# --------------------------------------------------------------------------
def make_logo(size, fill, outline):
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)

    s = float(size)
    path = QPainterPath()
    path.moveTo(0.27 * s, 0.14 * s)
    path.lineTo(0.27 * s, 0.58 * s)
    path.arcTo(QRectF(0.27 * s, 0.36 * s, 0.46 * s, 0.46 * s), 180, 180)
    path.lineTo(0.73 * s, 0.14 * s)

    body = 0.22 * s
    border = 0.06 * s
    pen = QPen(QColor(outline), body + 2 * border)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen)
    p.drawPath(path)

    pen = QPen(QColor(fill), body)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen)
    p.drawPath(path)
    p.end()
    return pm


# --------------------------------------------------------------------------
# SÖZDİZİMİ RENKLENDİRME (Python / JS / C benzeri diller için basit)
# --------------------------------------------------------------------------
# Desteklenen diller. Yeni dil eklemek için buraya bir satır eklemen yeter.
STR_DEFAULT = r'"(?:\\.|[^"\\\n])*"|' + r"'(?:\\.|[^'\\\n])*'"
STR_JS = STR_DEFAULT + r"|`(?:\\.|[^`\\\n])*`"
LINE_C = r"//[^\n]*"
BLOCK_C = ("/*", "*/")

LANGUAGES = {
    "Düz Metin": dict(ext=[".txt"], kind="plain"),
    "Python": dict(
        ext=[".py", ".pyw"], kind="code", line=r"#[^\n]*",
        kw="and as assert async await break class continue def del elif else except "
           "finally for from global if import in is lambda nonlocal not or pass raise "
           "return try while with yield self None True False",
    ),
    "JavaScript": dict(
        ext=[".js", ".mjs"], kind="code", line=LINE_C, block=BLOCK_C, strings=STR_JS,
        kw="async await break case catch class const continue debugger default delete do "
           "else export extends finally for function if import in instanceof let new of "
           "return static super switch this throw try typeof var void while with yield "
           "null undefined true false",
    ),
    "HTML": dict(ext=[".html", ".htm"], kind="html", block=("<!--", "-->")),
    "CSS": dict(ext=[".css"], kind="css", block=BLOCK_C),
    "JSON": dict(ext=[".json"], kind="json"),
    "Java": dict(
        ext=[".java"], kind="code", line=LINE_C, block=BLOCK_C,
        kw="abstract boolean break byte case catch char class const continue default do "
           "double else enum extends final finally float for if implements import "
           "instanceof int interface long new package private protected public return "
           "short static super switch this throw throws try void volatile while null "
           "true false String",
    ),
    "C": dict(
        ext=[".c", ".h"], kind="code", line=LINE_C, block=BLOCK_C,
        kw="auto break case char const continue default do double else enum extern float "
           "for goto if inline int long register return short signed sizeof static struct "
           "switch typedef union unsigned void volatile while",
    ),
    "C++": dict(
        ext=[".cpp", ".hpp", ".cc", ".cxx"], kind="code", line=LINE_C, block=BLOCK_C,
        kw="auto bool break case catch char class const continue default delete do double "
           "else enum explicit extern false float for if inline int long namespace new "
           "nullptr operator private protected public return short signed sizeof static "
           "struct switch template this throw true try typedef union unsigned using "
           "virtual void volatile while string",
    ),
    "C#": dict(
        ext=[".cs"], kind="code", line=LINE_C, block=BLOCK_C,
        kw="abstract as base bool break byte case catch char class const continue decimal "
           "default delegate do double else enum event false finally float for foreach if "
           "in int interface internal is lock long namespace new null object operator out "
           "override params private protected public readonly ref return sealed short "
           "static string struct switch this throw true try typeof uint ulong using var "
           "virtual void while",
    ),
    "Markdown": dict(ext=[".md", ".markdown"], kind="markdown"),
}
EXT_TO_LANG = {e: name for name, info in LANGUAGES.items() for e in info["ext"]}
ENC_NAMES = {"utf-8": "UTF-8", "cp1254": "Windows-1254"}
DEFAULT_EOL = "\r\n" if sys.platform == "win32" else "\n"


def lang_from_path(path):
    return EXT_TO_LANG.get(os.path.splitext(path)[1].lower())


def lang_filter(name):
    label = "Metin Dosyası" if name == "Düz Metin" else name
    return f"{label} ({' '.join('*' + e for e in LANGUAGES[name]['ext'])})"


FILTER_TO_LANG = {lang_filter(n): n for n in LANGUAGES}


class Highlighter(QSyntaxHighlighter):
    def __init__(self, doc, theme, language="Düz Metin"):
        super().__init__(doc)
        self.theme = theme
        self.language = language
        self.rules = []
        self.block = None
        self.comment_fmt = QTextCharFormat()
        self.build_rules()

    def set_theme(self, t, rehighlight=True):
        self.theme = t
        self.build_rules()
        if rehighlight:
            self.rehighlight()

    def set_language(self, language):
        self.language = language
        self.build_rules()
        self.rehighlight()

    def build_rules(self):
        t = self.theme
        lang = LANGUAGES.get(self.language, LANGUAGES["Düz Metin"])
        kind = lang["kind"]

        def fmt(color, bold=False, italic=False):
            f = QTextCharFormat()
            f.setForeground(QColor(color))
            if bold:
                f.setFontWeight(QFont.Weight.Bold)
            f.setFontItalic(italic)
            return f

        kw_fmt = fmt(t["keyword"], bold=True)
        num_fmt = fmt(t["number"])
        str_fmt = fmt(t["string"])
        self.comment_fmt = fmt(t["comment"], italic=True)
        self.block = lang.get("block")

        rules = []
        if kind == "code":
            words = "|".join(re.escape(w) for w in lang["kw"].split())
            rules.append((re.compile(r"\b(?:" + words + r")\b"), kw_fmt))
            rules.append((re.compile(r"\b\d+(?:\.\d+)?\b"), num_fmt))
            rules.append((re.compile(lang.get("strings", STR_DEFAULT)), str_fmt))
            rules.append((re.compile(lang["line"]), self.comment_fmt))
        elif kind == "json":
            rules.append((re.compile(r"-?\b\d+(?:\.\d+)?(?:[eE][+-]?\d+)?\b"), num_fmt))
            rules.append((re.compile(r"\b(?:true|false|null)\b"), kw_fmt))
            rules.append((re.compile(STR_DEFAULT), str_fmt))
            rules.append((re.compile(r'"(?:\\.|[^"\\\n])*"(?=\s*:)'), kw_fmt))
        elif kind == "html":
            rules.append((re.compile(r"</?[A-Za-z][^>]*>|<!DOCTYPE[^>]*>", re.I), kw_fmt))
            rules.append((re.compile(STR_DEFAULT), str_fmt))
        elif kind == "css":
            rules.append((re.compile(r"[A-Za-z-]+(?=\s*:)"), kw_fmt))
            rules.append((re.compile(
                r"#[0-9a-fA-F]{3,8}\b|\b\d+(?:\.\d+)?(?:px|em|rem|vh|vw|pt|ms|s|%)?"), num_fmt))
            rules.append((re.compile(STR_DEFAULT), str_fmt))
        elif kind == "markdown":
            rules.append((re.compile(r"^\s{0,3}#{1,6}\s.*$"), kw_fmt))
            rules.append((re.compile(r"^\s*(?:[-*+]|\d+\.)\s"), num_fmt))
            rules.append((re.compile(r"\*\*[^*\n]+\*\*|__[^_\n]+__"), num_fmt))
            rules.append((re.compile(r"`[^`\n]+`"), str_fmt))
            rules.append((re.compile(r"\[[^\]\n]*\]\([^)\n]*\)"), kw_fmt))
            rules.append((re.compile(r"^>.*$"), self.comment_fmt))
        self.rules = rules

    def highlightBlock(self, text):
        for pattern, f in self.rules:
            for m in pattern.finditer(text):
                self.setFormat(m.start(), m.end() - m.start(), f)

        # /* ... */ gibi birden çok satıra yayılan yorumlar
        self.setCurrentBlockState(0)
        if not self.block:
            return
        open_, close = self.block
        in_comment = self.previousBlockState() == 1
        start = 0 if in_comment else text.find(open_)
        while start >= 0:
            search_from = start if in_comment else start + len(open_)
            end = text.find(close, search_from)
            if end == -1:
                self.setCurrentBlockState(1)
                length = len(text) - start
            else:
                length = end - start + len(close)
            self.setFormat(start, length, self.comment_fmt)
            in_comment = False
            start = text.find(open_, start + length)


# --------------------------------------------------------------------------
# EDİTÖR (satır numaralı)
# --------------------------------------------------------------------------
class LineNumberArea(QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        self.editor = editor

    def sizeHint(self):
        return QSize(self.editor.line_number_width(), 0)

    def paintEvent(self, event):
        self.editor.paint_line_numbers(event)


class CodeEditor(QPlainTextEdit):
    def __init__(self, theme, language="Düz Metin"):
        super().__init__()
        self.path = None
        self.theme = theme
        self.language = language
        self.encoding = "utf-8"
        self.eol = DEFAULT_EOL
        self.area = LineNumberArea(self)
        self.highlighter = Highlighter(self.document(), theme, language)

        font = QFont("Consolas", 11)
        font.setStyleHint(QFont.StyleHint.Monospace)
        self.setFont(font)
        self.setTabStopDistance(4 * self.fontMetrics().horizontalAdvance(" "))
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)

        self.blockCountChanged.connect(self.update_margin)
        self.updateRequest.connect(self.update_area)
        self.cursorPositionChanged.connect(self.highlight_line)

        self.update_margin()
        self.apply_theme(theme)

    # --- tema
    def apply_theme(self, t):
        self.theme = t
        self.setStyleSheet(
            f"QPlainTextEdit {{ background: {t['bg']}; color: {t['fg']};"
            f" selection-background-color: {t['sel']}; border: none; }}"
        )
        self.highlighter.set_theme(t)
        self.highlight_line()
        self.area.update()

    def set_language(self, language):
        self.language = language
        self.highlighter.set_language(language)

    # --- satır numaraları
    def line_number_width(self):
        digits = len(str(max(1, self.blockCount())))
        return 20 + self.fontMetrics().horizontalAdvance("9") * max(3, digits)

    def update_margin(self, *_):
        self.setViewportMargins(self.line_number_width(), 0, 0, 0)

    def update_area(self, rect, dy):
        if dy:
            self.area.scroll(0, dy)
        else:
            self.area.update(0, rect.y(), self.area.width(), rect.height())
        if rect.contains(self.viewport().rect()):
            self.update_margin()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        self.area.setGeometry(QRect(cr.left(), cr.top(), self.line_number_width(), cr.height()))

    def paint_line_numbers(self, event):
        t = self.theme
        painter = QPainter(self.area)
        painter.fillRect(event.rect(), QColor(t["gutter_bg"]))
        block = self.firstVisibleBlock()
        number = block.blockNumber()
        top = round(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + round(self.blockBoundingRect(block).height())
        current = self.textCursor().blockNumber()
        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                painter.setPen(QColor(t["gutter_active"] if number == current else t["gutter_fg"]))
                painter.drawText(
                    0, top, self.area.width() - 10, self.fontMetrics().height(),
                    Qt.AlignmentFlag.AlignRight, str(number + 1),
                )
            block = block.next()
            top = bottom
            bottom = top + round(self.blockBoundingRect(block).height())
            number += 1

    def highlight_line(self):
        sel = QTextEdit.ExtraSelection()
        sel.format.setBackground(QColor(self.theme["line"]))
        sel.format.setProperty(QTextFormat.Property.FullWidthSelection, True)
        sel.cursor = self.textCursor()
        sel.cursor.clearSelection()
        self.setExtraSelections([sel])
        self.area.update()

    # --- yazma kolaylıkları
    def keyPressEvent(self, e):
        if e.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            cur = self.textCursor()
            line = cur.block().text()[: cur.positionInBlock()]
            indent = line[: len(line) - len(line.lstrip())]
            kind = LANGUAGES[self.language]["kind"]
            if self.language == "Python":
                openers = (":", "(", "[", "{")
            elif kind in ("code", "css", "json"):
                openers = ("{", "(", "[")
            else:
                openers = ()
            if line.rstrip().endswith(openers):
                indent += "    "
            super().keyPressEvent(e)
            self.insertPlainText(indent)
            return
        if e.key() == Qt.Key.Key_Tab and not e.modifiers():
            plain = LANGUAGES[self.language]["kind"] == "plain"
            self.insertPlainText("\t" if plain else "    ")
            return
        super().keyPressEvent(e)

    # --- satır işlemleri
    def _line_range(self):
        cur = self.textCursor()
        doc = self.document()
        start = doc.findBlock(cur.selectionStart())
        end_pos = cur.selectionEnd()
        end = doc.findBlock(end_pos)
        # seçim bir satırın en başında bittiyse o satırı dahil etme
        if cur.hasSelection() and end_pos == end.position() and end != start:
            end = end.previous()
        return start.blockNumber(), end.blockNumber()

    def duplicate_line(self):
        a, b = self._line_range()
        doc = self.document()
        first, last = doc.findBlockByNumber(a), doc.findBlockByNumber(b)
        cur = QTextCursor(doc)
        cur.setPosition(first.position())
        cur.setPosition(last.position() + last.length() - 1, QTextCursor.MoveMode.KeepAnchor)
        text = cur.selectedText().replace("\u2029", "\n")
        cur.beginEditBlock()
        cur.setPosition(last.position() + last.length() - 1)
        cur.insertText("\n" + text)
        cur.endEditBlock()

    def delete_line(self):
        a, b = self._line_range()
        doc = self.document()
        first, last = doc.findBlockByNumber(a), doc.findBlockByNumber(b)
        cur = QTextCursor(doc)
        cur.beginEditBlock()
        if last.next().isValid():
            cur.setPosition(first.position())
            cur.setPosition(last.next().position(), QTextCursor.MoveMode.KeepAnchor)
        else:
            start = first.position() - 1 if first.previous().isValid() else first.position()
            cur.setPosition(start)
            cur.setPosition(last.position() + last.length() - 1, QTextCursor.MoveMode.KeepAnchor)
        cur.removeSelectedText()
        cur.endEditBlock()
        self.setTextCursor(cur)

    def move_lines(self, d):
        a, b = self._line_range()
        doc = self.document()
        if (d < 0 and a == 0) or (d > 0 and b >= doc.blockCount() - 1):
            return
        old = self.textCursor()
        had_sel, col = old.hasSelection(), old.positionInBlock()
        cur = QTextCursor(doc)
        cur.beginEditBlock()
        if d < 0:
            nb = doc.findBlockByNumber(a - 1)
            text = nb.text()
            cur.setPosition(nb.position())
            cur.setPosition(nb.next().position(), QTextCursor.MoveMode.KeepAnchor)
            cur.removeSelectedText()
            last = doc.findBlockByNumber(b - 1)
            cur.setPosition(last.position() + last.length() - 1)
            cur.insertText("\n" + text)
        else:
            nb = doc.findBlockByNumber(b + 1)
            text = nb.text()
            cur.setPosition(nb.position() - 1)
            cur.setPosition(nb.position() + nb.length() - 1, QTextCursor.MoveMode.KeepAnchor)
            cur.removeSelectedText()
            cur.setPosition(doc.findBlockByNumber(a).position())
            cur.insertText(text + "\n")
        cur.endEditBlock()
        na, nb_ = doc.findBlockByNumber(a + d), doc.findBlockByNumber(b + d)
        if had_sel:
            sel = QTextCursor(doc)
            sel.setPosition(na.position())
            sel.setPosition(nb_.position() + nb_.length() - 1, QTextCursor.MoveMode.KeepAnchor)
        else:
            sel = QTextCursor(doc)
            sel.setPosition(na.position() + min(col, len(na.text())))
        self.setTextCursor(sel)

    def toggle_comment(self):
        if self.language == "Python":
            mark = "#"
        elif LANGUAGES[self.language]["kind"] == "code":
            mark = "//"
        else:
            return
        a, b = self._line_range()
        doc = self.document()
        blocks = [doc.findBlockByNumber(i) for i in range(a, b + 1)]
        filled = [bl for bl in blocks if bl.text().strip()]
        if not filled:
            return
        remove = all(bl.text().lstrip().startswith(mark) for bl in filled)
        cur = QTextCursor(doc)
        cur.beginEditBlock()
        for bl in blocks:
            text = bl.text()
            if not text.strip():
                continue
            indent = len(text) - len(text.lstrip())
            cur.setPosition(bl.position() + indent)
            if remove:
                n = len(mark) + (1 if text[indent + len(mark):indent + len(mark) + 1] == " " else 0)
                cur.movePosition(QTextCursor.MoveOperation.Right, QTextCursor.MoveMode.KeepAnchor, n)
                cur.removeSelectedText()
            else:
                cur.insertText(mark + " ")
        cur.endEditBlock()

    # --- dosyayı sürükleyip bırakınca aç
    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()
        else:
            super().dragEnterEvent(e)

    def dragMoveEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()
        else:
            super().dragMoveEvent(e)

    def dropEvent(self, e):
        if e.mimeData().hasUrls():
            paths = [u.toLocalFile() for u in e.mimeData().urls() if u.isLocalFile()]
            win = self.window()
            e.acceptProposedAction()
            QTimer.singleShot(0, lambda: [win.open_path(p) for p in paths if os.path.isfile(p)])
        else:
            super().dropEvent(e)

    def wheelEvent(self, e):
        if e.modifiers() & Qt.KeyboardModifier.ControlModifier:
            if e.angleDelta().y() > 0:
                self.zoomIn(1)
            else:
                self.zoomOut(1)
            return
        super().wheelEvent(e)


# --------------------------------------------------------------------------
# macOS TARZI YUVARLAK AÇILIR PENCERE + DİL SEÇİCİ
# --------------------------------------------------------------------------
def round_menu(menu):
    """QMenu'yu yuvarlak köşeli yapar (şeffaf arka plan + çerçevesiz)."""
    menu.setWindowFlags(
        menu.windowFlags()
        | Qt.WindowType.FramelessWindowHint
        | Qt.WindowType.NoDropShadowWindowHint
    )
    menu.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)


class LangPopup(QWidget):
    """Yuvarlak köşeli, gölgeli, aramalı dil listesi."""
    chosen = pyqtSignal(str)
    SHADOW = 14   # gölge için ayrılan boşluk (px)
    RADIUS = 14

    def __init__(self, parent=None):
        super().__init__(
            parent,
            Qt.WindowType.Popup
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.NoDropShadowWindowHint,
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.theme = THEMES[DEFAULT_THEME]
        m = self.SHADOW + 8
        lay = QVBoxLayout(self)
        lay.setContentsMargins(m, m - 2, m, m + 2)
        lay.setSpacing(8)

        self.search = QLineEdit()
        self.search.setPlaceholderText("Dil ara…")
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(self.filter)
        self.search.returnPressed.connect(self.pick_current)
        self.search.installEventFilter(self)
        lay.addWidget(self.search)

        self.list = QListWidget()
        self.list.setFrameShape(QListWidget.Shape.NoFrame)
        self.list.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.list.itemClicked.connect(lambda it: self.pick(it.text()))
        lay.addWidget(self.list)
        self.setFixedWidth(230)

    def apply_theme(self, t):
        self.theme = t
        self.setStyleSheet(f"""
            QLineEdit {{ background: {t['bg']}; color: {t['fg']}; border: 1px solid {t['border']};
                        border-radius: 9px; padding: 6px 10px; }}
            QLineEdit:focus {{ border: 1px solid {t['accent']}; }}
            QListWidget {{ background: transparent; color: {t['fg']}; outline: 0; }}
            QListWidget::item {{ padding: 7px 12px; border-radius: 8px; margin: 1px 0; }}
            QListWidget::item:hover {{ background: {t['panel2']}; }}
            QListWidget::item:selected {{ background: {t['accent']}; color: {t['bg']}; }}
        """)
        self.update()

    def paintEvent(self, _):
        t = self.theme
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        body = QRectF(self.rect()).adjusted(self.SHADOW, self.SHADOW - 4, -self.SHADOW, -self.SHADOW - 4)
        # yumuşak gölge: üst üste şeffaf yuvarlak dikdörtgenler
        p.setPen(Qt.PenStyle.NoPen)
        for i in range(self.SHADOW, 0, -1):
            p.setBrush(QColor(0, 0, 0, int(2.2 * (self.SHADOW - i + 1))))
            p.drawRoundedRect(body.adjusted(-i, -i, i, i + 4), self.RADIUS + i, self.RADIUS + i)
        p.setBrush(QColor(t["panel"]))
        p.setPen(QPen(QColor(t["border"]), 1))
        p.drawRoundedRect(body, self.RADIUS, self.RADIUS)

    def open_at(self, widget, current):
        self.search.clear()
        self.fill(current)
        rows = self.list.count()
        self.list.setFixedHeight(min(rows, 9) * 34 + 4)
        self.adjustSize()
        pos = widget.mapToGlobal(QPoint(0, widget.height()))
        self.move(pos.x() - self.SHADOW - 8, pos.y() - self.SHADOW + 2)
        self.show()
        self.search.setFocus()

    def fill(self, current=None):
        self.list.clear()
        q = self.search.text().strip().lower()
        for name in LANGUAGES:
            if q in name.lower():
                self.list.addItem(QListWidgetItem(name))
        for i in range(self.list.count()):
            if self.list.item(i).text() == current:
                self.list.setCurrentRow(i)
                break
        else:
            if self.list.count():
                self.list.setCurrentRow(0)
        self._current = current

    def filter(self, _):
        self.fill(getattr(self, "_current", None))

    def pick(self, name):
        self.hide()
        self.chosen.emit(name)

    def pick_current(self):
        it = self.list.currentItem()
        if it:
            self.pick(it.text())

    def eventFilter(self, obj, ev):
        # arama kutusundayken ↑/↓ ile listede gezin
        if obj is self.search and ev.type() == QEvent.Type.KeyPress:
            if ev.key() in (Qt.Key.Key_Down, Qt.Key.Key_Up):
                step = 1 if ev.key() == Qt.Key.Key_Down else -1
                r = max(0, min(self.list.count() - 1, self.list.currentRow() + step))
                self.list.setCurrentRow(r)
                return True
            if ev.key() == Qt.Key.Key_Escape:
                self.hide()
                return True
        return super().eventFilter(obj, ev)


class LangButton(QPushButton):
    """Araç çubuğundaki yuvarlak 'Python ⌄' düğmesi; tıklayınca LangPopup açılır."""
    languageChosen = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.language = "Düz Metin"
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("Dosyanın dilini seç: renklendirme ve kayıt uzantısı buna göre değişir")
        self.popup = LangPopup(self)
        self.popup.chosen.connect(self.languageChosen)
        self.clicked.connect(lambda: self.popup.open_at(self, self.language))
        self.set_language(self.language)

    def set_language(self, name):
        self.language = name
        self.setText(f"{name}  ⌄")

    def apply_theme(self, t):
        self.popup.apply_theme(t)


# --------------------------------------------------------------------------
# BUL / DEĞİŞTİR ÇUBUĞU
# --------------------------------------------------------------------------
class FindBar(QWidget):
    def __init__(self, window):
        super().__init__()
        self.setObjectName("findbar")
        self.win = window
        lay = QHBoxLayout(self)
        lay.setContentsMargins(8, 6, 8, 6)

        self.find_edit = QLineEdit()
        self.find_edit.setPlaceholderText("Bul…")
        self.replace_edit = QLineEdit()
        self.replace_edit.setPlaceholderText("Şununla değiştir…")
        self.find_edit.returnPressed.connect(self.find_next)

        btns = [
            ("Sonraki", self.find_next), ("Önceki", self.find_prev),
            ("Değiştir", self.replace_one), ("Tümünü Değiştir", self.replace_all),
            ("✕", self.hide),
        ]
        lay.addWidget(self.find_edit, 3)
        lay.addWidget(self.replace_edit, 3)
        for text, fn in btns:
            b = QPushButton(text)
            b.clicked.connect(fn)
            lay.addWidget(b)
        self.hide()

    def focus_find(self):
        self.show()
        ed = self.win.current_editor()
        if ed and ed.textCursor().hasSelection():
            self.find_edit.setText(ed.textCursor().selectedText())
        self.find_edit.setFocus()
        self.find_edit.selectAll()

    def _search(self, backward=False):
        ed = self.win.current_editor()
        text = self.find_edit.text()
        if not ed or not text:
            return False
        flags = QTextDocument.FindFlag.FindBackward if backward else QTextDocument.FindFlag(0)
        if ed.find(text, flags):
            return True
        # sona/başa gelince baştan/sondan devam et
        cur = ed.textCursor()
        cur.movePosition(QTextCursor.MoveOperation.End if backward else QTextCursor.MoveOperation.Start)
        ed.setTextCursor(cur)
        if ed.find(text, flags):
            return True
        self.win.statusBar().showMessage("Bulunamadı", 2000)
        return False

    def find_next(self):
        self._search(False)

    def find_prev(self):
        self._search(True)

    def replace_one(self):
        ed = self.win.current_editor()
        if not ed:
            return
        cur = ed.textCursor()
        if cur.hasSelection() and cur.selectedText().lower() == self.find_edit.text().lower():
            cur.insertText(self.replace_edit.text())
        self._search(False)

    def replace_all(self):
        ed = self.win.current_editor()
        text = self.find_edit.text()
        if not ed or not text:
            return
        doc = ed.document()
        cur = QTextCursor(doc)
        cur.beginEditBlock()
        count = 0
        pos = QTextCursor(doc)
        while True:
            pos = doc.find(text, pos)
            if pos.isNull():
                break
            pos.insertText(self.replace_edit.text())
            count += 1
        cur.endEditBlock()
        self.win.statusBar().showMessage(f"{count} yer değiştirildi", 3000)


# --------------------------------------------------------------------------
# ANA PENCERE
# --------------------------------------------------------------------------
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings = QSettings("UNotDefteri", "UNotDefteri")
        name = self.settings.value("tema", DEFAULT_THEME)
        self.theme_name = name if name in THEMES else DEFAULT_THEME
        self.untitled_count = 0

        self.resize(1100, 700)
        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.setMovable(True)
        self.tabs.setDocumentMode(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.tabs.currentChanged.connect(self.on_tab_changed)

        self.findbar = FindBar(self)
        central = QWidget()
        lay = QVBoxLayout(central)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        lay.addWidget(self.tabs)
        lay.addWidget(self.findbar)
        self.setCentralWidget(central)

        self.build_status()
        self.build_menus()
        self.build_toolbar()
        self.apply_theme(self.theme_name)

        for path in sys.argv[1:]:
            if os.path.isfile(path):
                self.open_path(path)
        if self.tabs.count() == 0:
            self.new_file()

    # --- menüler
    def build_menus(self):
        mb = self.menuBar()

        def act(menu, text, fn, shortcut=None):
            a = QAction(text, self)
            if shortcut:
                a.setShortcut(QKeySequence(shortcut))
            a.triggered.connect(fn)
            menu.addAction(a)
            return a

        m = mb.addMenu("&Dosya")
        round_menu(m)
        act(m, "Yeni", self.new_file, "Ctrl+N")
        act(m, "Aç…", self.open_dialog, "Ctrl+O")
        act(m, "Kaydet", self.save, "Ctrl+S")
        act(m, "Farklı Kaydet…", self.save_as, "Ctrl+Shift+S")
        m.addSeparator()
        act(m, "Sekmeyi Kapat", lambda: self.close_tab(self.tabs.currentIndex()), "Ctrl+W")
        act(m, "Çıkış", self.close, "Ctrl+Q")

        m = mb.addMenu("&Düzen")
        round_menu(m)
        act(m, "Geri Al", lambda: self.ed_call("undo"), "Ctrl+Z")
        act(m, "Yinele", lambda: self.ed_call("redo"), "Ctrl+Y")
        m.addSeparator()
        act(m, "Kes", lambda: self.ed_call("cut"), "Ctrl+X")
        act(m, "Kopyala", lambda: self.ed_call("copy"), "Ctrl+C")
        act(m, "Yapıştır", lambda: self.ed_call("paste"), "Ctrl+V")
        act(m, "Tümünü Seç", lambda: self.ed_call("selectAll"), "Ctrl+A")
        m.addSeparator()
        act(m, "Bul / Değiştir", self.findbar.focus_find, "Ctrl+F")
        act(m, "Satıra Git…", self.goto_line, "Ctrl+G")
        m.addSeparator()
        act(m, "Satırı Çoğalt", lambda: self.ed_call("duplicate_line"), "Ctrl+D")
        act(m, "Satırı Sil", lambda: self.ed_call("delete_line"), "Ctrl+Shift+K")
        act(m, "Satırı Yukarı Taşı", lambda: self.ed_call("move_lines", -1), "Alt+Up")
        act(m, "Satırı Aşağı Taşı", lambda: self.ed_call("move_lines", 1), "Alt+Down")
        act(m, "Yorum Satırı Yap / Kaldır", lambda: self.ed_call("toggle_comment"), "Ctrl+/")

        m = mb.addMenu("&Görünüm")
        round_menu(m)
        tm = m.addMenu("Tema")
        round_menu(tm)
        group = QActionGroup(self)
        group.setExclusive(True)
        for name in THEMES:
            a = QAction(name, self, checkable=True)
            a.setChecked(name == self.theme_name)
            a.triggered.connect(lambda _, n=name: self.apply_theme(n))
            group.addAction(a)
            tm.addAction(a)
        m.addSeparator()
        act(m, "Satır Kaydırma", self.toggle_wrap).setCheckable(True)
        act(m, "Yakınlaştır", lambda: self.ed_call("zoomIn", 1), "Ctrl+=")
        act(m, "Uzaklaştır", lambda: self.ed_call("zoomOut", 1), "Ctrl+-")

        m = mb.addMenu("&Yardım")
        round_menu(m)
        act(m, "Hakkında", self.about)

    def build_status(self):
        sb = self.statusBar()
        self.logo_label = QLabel()
        self.pos_label = QLabel("Satır 1, Sütun 1")
        self.count_label = QLabel("0 kelime")
        self.lang_label = QLabel("Düz Metin")
        self.enc_label = QLabel("UTF-8")
        self.theme_label = QLabel()
        sb.addWidget(self.logo_label)
        sb.addPermanentWidget(self.count_label)
        sb.addPermanentWidget(self.pos_label)
        sb.addPermanentWidget(self.lang_label)
        sb.addPermanentWidget(self.enc_label)
        sb.addPermanentWidget(self.theme_label)

    # --- üst araç çubuğu (dil seçimi)
    def build_toolbar(self):
        tb = QToolBar("Araçlar")
        tb.setMovable(False)
        self.addToolBar(tb)
        buttons = (
            ("Yeni", self.new_file),
            ("Aç", self.open_dialog),
            ("Kaydet", lambda: self.save()),
        )
        for text, fn in buttons:
            a = QAction(text, self)
            a.triggered.connect(lambda _checked=False, f=fn: f())
            tb.addAction(a)
        tb.addSeparator()
        tb.addWidget(QLabel("  Dil: "))
        self.lang_combo = LangButton()
        self.lang_combo.languageChosen.connect(self.change_language)
        tb.addWidget(self.lang_combo)

    def change_language(self, name):
        ed = self.current_editor()
        if ed and name in LANGUAGES:
            ed.set_language(name)
            self.sync_combo()
            self.update_status()
            ed.setFocus()

    def sync_combo(self):
        ed = self.current_editor()
        if ed:
            self.lang_combo.set_language(ed.language)

    def on_tab_changed(self, *_):
        self.sync_combo()
        self.update_status()

    # --- tema
    def apply_theme(self, name):
        self.theme_name = name
        self.settings.setValue("tema", name)
        t = THEMES[name]
        self.setStyleSheet(f"""
            QMainWindow, QWidget#findbar {{ background: {t['panel']}; color: {t['fg']}; }}
            QMenuBar {{ background: {t['panel']}; color: {t['fg']}; }}
            QMenuBar::item {{ padding: 5px 10px; border-radius: 7px; }}
            QMenuBar::item:selected {{ background: {t['panel2']}; }}
            QMenu {{ background: {t['panel']}; color: {t['fg']}; border: 1px solid {t['border']};
                    border-radius: 12px; padding: 6px; }}
            QMenu::item {{ padding: 6px 26px 6px 14px; border-radius: 7px; margin: 1px 2px; }}
            QMenu::item:selected {{ background: {t['accent']}; color: {t['bg']}; }}
            QMenu::separator {{ height: 1px; background: {t['border']}; margin: 5px 10px; }}
            QTabWidget::pane {{ border: none; }}
            QTabBar {{ background: {t['panel']}; }}
            QTabBar::tab {{ background: transparent; color: {t['gutter_fg']}; padding: 7px 16px;
                           margin: 5px 2px 0 2px; border-radius: 9px; }}
            QTabBar::tab:selected {{ background: {t['bg']}; color: {t['fg']}; }}
            QTabBar::tab:hover:!selected {{ background: {t['panel2']}; }}
            QStatusBar {{ background: {t['accent']}; color: {t['bg']}; }}
            QStatusBar QLabel {{ color: {t['logo_line']}; padding: 0 8px; font-weight: 600; }}
            QLineEdit {{ background: {t['bg']}; color: {t['fg']}; border: 1px solid {t['border']};
                        padding: 5px 10px; border-radius: 9px; }}
            QLineEdit:focus {{ border: 1px solid {t['accent']}; }}
            QPushButton {{ background: {t['panel2']}; color: {t['fg']}; border: 1px solid {t['border']};
                          padding: 5px 14px; border-radius: 9px; }}
            QPushButton:hover {{ background: {t['accent']}; color: {t['bg']}; border-color: {t['accent']}; }}
            QToolBar {{ background: {t['panel']}; border: none; padding: 5px; spacing: 6px; }}
            QToolBar QLabel {{ color: {t['fg']}; }}
            QToolButton {{ background: transparent; color: {t['fg']}; padding: 6px 13px; border-radius: 9px; }}
            QToolButton:hover {{ background: {t['panel2']}; }}
            QMessageBox, QInputDialog {{ background: {t['panel']}; color: {t['fg']}; }}
            QScrollBar:vertical {{ background: {t['bg']}; width: 12px; margin: 2px; }}
            QScrollBar:horizontal {{ background: {t['bg']}; height: 12px; margin: 2px; }}
            QScrollBar::handle {{ background: {t['border']}; border-radius: 6px; min-height: 30px; min-width: 30px; }}
            QScrollBar::handle:hover {{ background: {t['accent']}; }}
            QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; }}
        """)
        self.setWindowIcon(QIcon(make_logo(128, t["accent"], t["logo_line"])))
        self.logo_label.setPixmap(make_logo(20, t["bg"], t["logo_line"]))
        self.theme_label.setText(name)
        self.lang_combo.apply_theme(t)
        for i in range(self.tabs.count()):
            self.tabs.widget(i).apply_theme(t)

    # --- yardımcılar
    def current_editor(self):
        return self.tabs.currentWidget()

    def ed_call(self, method, *args):
        ed = self.current_editor()
        if ed:
            getattr(ed, method)(*args)

    def update_status(self, *_):
        ed = self.current_editor()
        if not ed:
            return
        c = ed.textCursor()
        self.pos_label.setText(f"Satır {c.blockNumber() + 1}, Sütun {c.positionInBlock() + 1}")
        self.lang_label.setText(ed.language)
        doc = ed.document()
        chars = doc.characterCount() - 1
        words = len(ed.toPlainText().split()) if chars < 500_000 else "—"
        self.count_label.setText(f"{words} kelime · {chars} karakter")
        enc = ENC_NAMES.get(ed.encoding, ed.encoding.upper())
        eol = "CRLF" if ed.eol == "\r\n" else "LF"
        self.enc_label.setText(f"{enc}  {eol}")
        self.update_title()

    def update_title(self):
        ed = self.current_editor()
        name = os.path.basename(ed.path) if ed and ed.path else "isimsiz"
        self.setWindowTitle(f"{name} - {APP_NAME}")

    def tab_title(self, ed):
        name = os.path.basename(ed.path) if ed.path else ed.untitled_name
        return name + (" ●" if ed.document().isModified() else "")

    def refresh_tab(self, ed):
        i = self.tabs.indexOf(ed)
        if i >= 0:
            self.tabs.setTabText(i, self.tab_title(ed))
            self.tabs.setTabToolTip(i, ed.path or "")
        self.update_title()

    def add_editor(self, text="", path=None, language="Düz Metin", encoding="utf-8", eol=DEFAULT_EOL):
        ed = CodeEditor(THEMES[self.theme_name], language)
        ed.path = path
        ed.encoding = encoding
        ed.eol = eol
        if not path:
            self.untitled_count += 1
            ed.untitled_name = f"isimsiz {self.untitled_count}"
        ed.setPlainText(text)
        ed.document().setModified(False)
        ed.document().modificationChanged.connect(lambda _, e=ed: self.refresh_tab(e))
        ed.cursorPositionChanged.connect(self.update_status)
        i = self.tabs.addTab(ed, self.tab_title(ed))
        self.tabs.setCurrentIndex(i)
        self.refresh_tab(ed)
        ed.setFocus()
        return ed

    # --- dosya işlemleri
    def new_file(self):
        self.add_editor()

    def open_dialog(self):
        exts = " ".join("*" + e for info in LANGUAGES.values() for e in info["ext"])
        filters = ";;".join(
            [f"Desteklenen Dosyalar ({exts})"] + [lang_filter(n) for n in LANGUAGES] + ["Tüm Dosyalar (*)"]
        )
        paths, _ = QFileDialog.getOpenFileNames(self, "Dosya Aç", "", filters)
        for p in paths:
            self.open_path(p)

    def open_path(self, path):
        for i in range(self.tabs.count()):
            if self.tabs.widget(i).path == path:
                self.tabs.setCurrentIndex(i)
                return
        try:
            with open(path, "rb") as f:
                raw = f.read()
        except OSError as e:
            QMessageBox.warning(self, APP_NAME, f"Dosya açılamadı:\n{e}")
            return
        # Önce UTF-8 dene; olmazsa eski Windows (Türkçe ANSI) kodlamasına bak
        try:
            text, enc = raw.decode("utf-8"), "utf-8"
        except UnicodeDecodeError:
            text, enc = raw.decode("cp1254", errors="replace"), "cp1254"
        if text.startswith("﻿"):
            text = text[1:]
        eol = "\r\n" if b"\r\n" in raw else ("\n" if b"\n" in raw else DEFAULT_EOL)
        text = text.replace("\r\n", "\n")
        language = lang_from_path(path) or "Düz Metin"
        # boş isimsiz sekme varsa onu yeniden kullan
        cur = self.current_editor()
        if cur and not cur.path and not cur.document().isModified() and not cur.toPlainText():
            self.tabs.removeTab(self.tabs.indexOf(cur))
        self.add_editor(text, path, language, enc, eol)

    def save(self, ed=None):
        ed = ed or self.current_editor()
        if not ed:
            return False
        if not ed.path:
            return self.save_as(ed)
        return self._write(ed, ed.path)

    def save_as(self, ed=None):
        ed = ed or self.current_editor()
        if not ed:
            return False
        suggested = ed.path or ("isimsiz" + LANGUAGES[ed.language]["ext"][0])
        filters = ";;".join([lang_filter(n) for n in LANGUAGES] + ["Tüm Dosyalar (*)"])
        path, chosen = QFileDialog.getSaveFileName(
            self, "Farklı Kaydet", suggested, filters, lang_filter(ed.language)
        )
        if not path:
            return False
        if not os.path.splitext(path)[1]:
            lang = FILTER_TO_LANG.get(chosen, ed.language)
            path += LANGUAGES[lang]["ext"][0]
        if not self._write(ed, path):
            return False
        # Uzantıdan dili anla (ör. dosyayı .py olarak kaydettiysen dil Python olur)
        lang = lang_from_path(path)
        if lang and lang != ed.language:
            ed.set_language(lang)
            self.sync_combo()
            self.update_status()
        return True

    def _write(self, ed, path):
        text = ed.toPlainText()
        if ed.eol != "\n":
            text = text.replace("\n", ed.eol)
        try:
            try:
                data = text.encode(ed.encoding)
            except UnicodeEncodeError:
                ed.encoding = "utf-8"
                data = text.encode("utf-8")
            with open(path, "wb") as f:
                f.write(data)
        except OSError as e:
            QMessageBox.warning(self, APP_NAME, f"Kaydedilemedi:\n{e}")
            return False
        ed.path = path
        ed.document().setModified(False)
        self.refresh_tab(ed)
        self.statusBar().showMessage("Kaydedildi", 2000)
        self.update_status()
        return True

    def maybe_save(self, ed):
        if not ed.document().isModified():
            return True
        name = os.path.basename(ed.path) if ed.path else ed.untitled_name
        box = QMessageBox(self)
        box.setWindowTitle(APP_NAME)
        box.setText(f"“{name}” üzerinde kaydedilmemiş değişiklikler var.")
        save = box.addButton("Kaydet", QMessageBox.ButtonRole.AcceptRole)
        discard = box.addButton("Kaydetme", QMessageBox.ButtonRole.DestructiveRole)
        box.addButton("İptal", QMessageBox.ButtonRole.RejectRole)
        box.exec()
        clicked = box.clickedButton()
        if clicked is save:
            return self.save(ed)
        return clicked is discard

    def close_tab(self, index):
        ed = self.tabs.widget(index)
        if ed is None or not self.maybe_save(ed):
            return
        self.tabs.removeTab(index)
        ed.deleteLater()
        if self.tabs.count() == 0:
            self.new_file()

    def closeEvent(self, event):
        for i in range(self.tabs.count()):
            ed = self.tabs.widget(i)
            self.tabs.setCurrentIndex(i)
            if not self.maybe_save(ed):
                event.ignore()
                return
        event.accept()

    # --- diğer
    def goto_line(self):
        ed = self.current_editor()
        if not ed:
            return
        n, ok = QInputDialog.getInt(self, "Satıra Git", "Satır no:", 1, 1, ed.blockCount())
        if ok:
            block = ed.document().findBlockByNumber(n - 1)
            cur = QTextCursor(block)
            ed.setTextCursor(cur)
            ed.centerCursor()

    def toggle_wrap(self, checked):
        mode = QPlainTextEdit.LineWrapMode.WidgetWidth if checked else QPlainTextEdit.LineWrapMode.NoWrap
        for i in range(self.tabs.count()):
            self.tabs.widget(i).setLineWrapMode(mode)

    def about(self):
        QMessageBox.about(self, APP_NAME, "ULAŞ ONUR CANTÜRK TARAFINDAN CLAUDE YARDIMIYLA KODLANDI")


def main():
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    try:
        main()
    except Exception:
        import traceback
        traceback.print_exc()
        input("\nBir hata oldu. Bu yazıyı bana gönder. Kapatmak için Enter'a bas...")
