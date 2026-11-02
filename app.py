"""محوّل الوسائط — تحويل أي فيديو لأي صيغة، وتحويل أي ملف صوتي إلى MP3."""
import os
import subprocess
import sys

from PySide6.QtCore import (QEasingCurve, QPointF, QPropertyAnimation, QProcess,
                            QRectF, QSettings, QSize, Qt, QTimer, Signal)
from PySide6.QtGui import (QBrush, QColor, QFont, QFontMetrics, QIcon,
                           QLinearGradient, QPainter, QPainterPath, QPen, QPixmap)
from PySide6.QtWidgets import (QAbstractButton, QApplication, QButtonGroup,
                               QFileDialog, QFrame, QGraphicsDropShadowEffect,
                               QGraphicsOpacityEffect, QGridLayout, QHBoxLayout,
                               QLabel, QListWidget, QListWidgetItem, QMainWindow,
                               QMessageBox, QProgressBar, QPushButton, QScrollArea,
                               QSizePolicy, QStackedWidget, QVBoxLayout, QWidget)

import engine

APP_NAME = "محوّل الوسائط"
RLM = "\u200f"  # يجبر اتجاه النص المختلط (عربي/لاتيني) من اليمين لليسار


def ltr(text):
    """يبقي مقطعاً لاتينياً (مثل 48 kHz) بترتيبه الصحيح داخل نص عربي."""
    return "\u202a" + text + "\u202c"

BG = "#0B0D14"
SIDEBAR = "#0F121B"
CARD = "#141824"
CARD_HI = "#1A1F2E"
BORDER = "#242A3B"
TEXT = "#E9EBF3"
MUTED = "#8B92A9"
ACCENT1 = "#7C5CFF"
ACCENT2 = "#22D3EE"
SUCCESS = "#34D399"
ERROR = "#F87171"
WARN = "#FBBF24"

STYLE = f"""
* {{ color: {TEXT}; font-size: 13px; }}
QMainWindow, #root {{ background: {BG}; }}
#sidebar {{ background: {SIDEBAR}; border-left: 1px solid {BORDER}; }}
#card {{ background: {CARD}; border: 1px solid {BORDER}; border-radius: 16px; }}
#appTitle {{ font-size: 19px; font-weight: 800; }}
#appSub {{ color: {MUTED}; font-size: 11px; letter-spacing: 1px; }}
#pageTitle {{ font-size: 26px; font-weight: 800; }}
#pageSub {{ color: {MUTED}; font-size: 13px; }}
#sectionTitle {{ font-size: 13px; font-weight: 700; color: {TEXT}; }}
#muted {{ color: {MUTED}; font-size: 12px; }}
#pill {{ color: white; font-weight: 700; font-size: 12px; padding: 5px 12px; border-radius: 12px;
        background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 {ACCENT1}, stop:1 {ACCENT2}); }}
#navBtn {{ text-align: right; padding: 12px 16px; border-radius: 12px; border: none;
          background: transparent; color: {MUTED}; font-size: 14px; font-weight: 600; }}
#navBtn:hover {{ background: {CARD}; color: {TEXT}; }}
#navBtn:checked {{ background: {CARD_HI}; color: {TEXT}; border: 1px solid {BORDER}; }}
#seg {{ background: transparent; border: none; border-radius: 9px; padding: 8px 6px;
       color: {MUTED}; font-weight: 600; }}
#seg:hover {{ color: {TEXT}; }}
#seg:checked {{ background: {CARD_HI}; color: {TEXT}; border: 1px solid #343B52; }}
#seg:disabled {{ color: #4A5066; }}
#segWrap {{ background: {BG}; border: 1px solid {BORDER}; border-radius: 12px; }}
#ghostBtn {{ background: {CARD_HI}; border: 1px solid {BORDER}; border-radius: 10px;
            padding: 8px 14px; font-weight: 600; }}
#ghostBtn:hover {{ border-color: {ACCENT1}; }}
#ghostBtn:disabled {{ color: #4A5066; }}
#linkBtn {{ background: transparent; border: none; color: {MUTED}; font-weight: 600; padding: 4px 6px; }}
#linkBtn:hover {{ color: {ERROR}; }}
#linkBtn:disabled {{ color: #3A4056; }}
#primaryBtn {{ border: none; border-radius: 14px; padding: 15px; font-size: 16px; font-weight: 800; color: white;
              background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 {ACCENT1}, stop:1 {ACCENT2}); }}
#primaryBtn:hover {{ background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #8D72FF, stop:1 #45DDF2); }}
#primaryBtn:disabled {{ background: #232839; color: #59607A; }}
#dangerBtn {{ border: 1px solid #5A2A33; border-radius: 14px; padding: 15px; font-size: 15px; font-weight: 700;
             color: {ERROR}; background: #22161C; }}
#dangerBtn:hover {{ background: #2C1820; }}
#rowName {{ font-size: 14px; font-weight: 700; }}
#rowMeta {{ color: {MUTED}; font-size: 12px; }}
#rowX {{ background: transparent; border: none; color: {MUTED}; font-size: 15px; border-radius: 8px; }}
#rowX:hover {{ background: #2A1C24; color: {ERROR}; }}
#rowReveal {{ background: transparent; border: 1px solid {BORDER}; border-radius: 8px; color: {ACCENT2};
             font-size: 12px; font-weight: 600; padding: 4px 10px; }}
#rowReveal:hover {{ border-color: {ACCENT2}; }}
QListWidget {{ background: transparent; border: none; outline: none; }}
QListWidget::item {{ border: none; margin: 0; padding: 0; }}
QListWidget::item:selected {{ background: transparent; }}
QProgressBar {{ background: #1E2333; border: none; border-radius: 3px; }}
QProgressBar::chunk {{ border-radius: 3px;
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 {ACCENT1}, stop:1 {ACCENT2}); }}
QProgressBar[state="done"]::chunk {{ background: {SUCCESS}; }}
QProgressBar[state="error"]::chunk {{ background: {ERROR}; }}
QScrollArea {{ background: transparent; border: none; }}
QScrollArea > QWidget > QWidget {{ background: transparent; }}
QScrollBar:vertical {{ background: transparent; width: 8px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: #2A3045; border-radius: 4px; min-height: 30px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}
QToolTip {{ background: {CARD_HI}; color: {TEXT}; border: 1px solid {BORDER}; padding: 6px; border-radius: 6px; }}
#toast {{ background: {CARD_HI}; border: 1px solid #343B52; border-radius: 12px; padding: 12px 18px;
         font-weight: 600; }}
"""


# ---------------------------------------------------------------- أيقونات مرسومة

def gradient(rect, c1=ACCENT1, c2=ACCENT2):
    g = QLinearGradient(rect.topLeft(), rect.bottomRight())
    g.setColorAt(0, QColor(c1))
    g.setColorAt(1, QColor(c2))
    return g


def draw_glyph(p, kind, r, color):
    """يرسم أيقونة بسيطة (video/audio/folder/upload/check) داخل المستطيل r."""
    p.save()
    pen = QPen(QColor(color) if isinstance(color, str) else color, max(1.6, r.width() * 0.085))
    pen.setCapStyle(Qt.RoundCap)
    pen.setJoinStyle(Qt.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.NoBrush)
    x, y, w, h = r.x(), r.y(), r.width(), r.height()
    if kind == "video":
        p.drawRoundedRect(QRectF(x + w * .08, y + h * .2, w * .84, h * .6), w * .12, w * .12)
        tri = QPainterPath()
        tri.moveTo(x + w * .42, y + h * .36)
        tri.lineTo(x + w * .64, y + h * .5)
        tri.lineTo(x + w * .42, y + h * .64)
        tri.closeSubpath()
        p.setBrush(pen.color())
        p.drawPath(tri)
    elif kind == "audio":
        bars = [.3, .6, .9, .55, .75, .35]
        bw = w / (len(bars) * 1.6)
        for i, b in enumerate(bars):
            cx = x + w * .12 + i * bw * 1.6 + bw / 2
            p.drawLine(QPointF(cx, y + h / 2 - h * b / 2.4), QPointF(cx, y + h / 2 + h * b / 2.4))
    elif kind == "folder":
        path = QPainterPath()
        path.moveTo(x + w * .1, y + h * .28)
        path.lineTo(x + w * .4, y + h * .28)
        path.lineTo(x + w * .48, y + h * .38)
        path.lineTo(x + w * .9, y + h * .38)
        path.lineTo(x + w * .9, y + h * .78)
        path.lineTo(x + w * .1, y + h * .78)
        path.closeSubpath()
        p.drawPath(path)
    elif kind == "upload":
        p.drawLine(QPointF(x + w * .5, y + h * .22), QPointF(x + w * .5, y + h * .66))
        p.drawLine(QPointF(x + w * .32, y + h * .4), QPointF(x + w * .5, y + h * .22))
        p.drawLine(QPointF(x + w * .68, y + h * .4), QPointF(x + w * .5, y + h * .22))
        p.drawLine(QPointF(x + w * .22, y + h * .8), QPointF(x + w * .78, y + h * .8))
    elif kind == "check":
        p.drawLine(QPointF(x + w * .25, y + h * .52), QPointF(x + w * .43, y + h * .7))
        p.drawLine(QPointF(x + w * .43, y + h * .7), QPointF(x + w * .76, y + h * .32))
    p.restore()


def make_icon(kind, color=TEXT, size=40):
    pm = QPixmap(size * 2, size * 2)
    pm.setDevicePixelRatio(2)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    draw_glyph(p, kind, QRectF(0, 0, size, size), color)
    p.end()
    return QIcon(pm)


def paint_logo(p, rect):
    p.setPen(Qt.NoPen)
    p.setBrush(QBrush(gradient(rect)))
    p.drawRoundedRect(rect, rect.width() * .26, rect.width() * .26)
    w, h = rect.width(), rect.height()
    tri = QPainterPath()
    tri.moveTo(rect.x() + w * .36, rect.y() + h * .27)
    tri.lineTo(rect.x() + w * .72, rect.y() + h * .5)
    tri.lineTo(rect.x() + w * .36, rect.y() + h * .73)
    tri.closeSubpath()
    p.setBrush(QColor("white"))
    p.drawPath(tri)


def logo_pixmap(size):
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    m = size * .09
    paint_logo(p, QRectF(m, m, size - 2 * m, size - 2 * m))
    p.end()
    return pm


class Logo(QWidget):
    def __init__(self, size=44):
        super().__init__()
        self.setFixedSize(size, size)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        paint_logo(p, QRectF(self.rect()))


# ---------------------------------------------------------------- عناصر واجهة

def card():
    f = QFrame()
    f.setObjectName("card")
    return f


def label(text, name=None):
    lb = QLabel(text)
    if name:
        lb.setObjectName(name)
    return lb


def human_size(n):
    for unit in ("بايت", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.0f} {unit}" if unit == "بايت" else f"{n:.1f} {unit}"
        n /= 1024


def human_time(sec):
    sec = int(round(sec))
    h, rem = divmod(sec, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


def reveal(path):
    """يفتح مدير الملفات ويحدد الملف (Finder على الماك، Explorer على ويندوز)."""
    if not (path and os.path.exists(path)):
        return
    if sys.platform == "darwin":
        subprocess.Popen(["open", "-R", path])
    elif os.name == "nt":
        subprocess.Popen(["explorer", "/select,", os.path.normpath(path)])
    else:
        subprocess.Popen(["xdg-open", os.path.dirname(path)])


def app_settings():
    """النسخة المحمولة (Portable) تحفظ إعداداتها في ملف بجانب البرنامج بدل الريجستري،
    حتى تنتقل معه على الفلاش. يُعرف ذلك من ملف PORTABLE الذي يضيفه سكربت البناء."""
    bundle = getattr(sys, "_MEIPASS", None)
    if bundle and os.path.exists(os.path.join(bundle, "PORTABLE")):
        exe_dir = os.path.dirname(os.path.abspath(sys.executable))
        if os.access(exe_dir, os.W_OK):
            return QSettings(os.path.join(exe_dir, "MediaConverter-settings.ini"), QSettings.IniFormat)
    return QSettings("MediaConverterPro", "app")


def dark_title_bar(widget):
    """ويندوز 10/11: شريط عنوان داكن ليتناسق مع الواجهة (الماك يتبع مظهر النظام)."""
    if os.name != "nt":
        return
    try:
        import ctypes
        hwnd = int(widget.winId())
        on = ctypes.c_int(1)
        # 20 = DWMWA_USE_IMMERSIVE_DARK_MODE، و 19 لإصدارات ويندوز 10 الأقدم
        for attr in (20, 19):
            if ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, attr, ctypes.byref(on), ctypes.sizeof(on)) == 0:
                break
    except Exception:
        pass


class Tile(QAbstractButton):
    """زر بطاقة: عنوان كبير ووصف صغير، مع حدّ متدرّج عند الاختيار."""

    def __init__(self, title, desc, tag=None):
        super().__init__()
        self.title, self.desc, self.tag = title, desc, tag
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumSize(96, 54)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._hover = False

    def sizeHint(self):
        return QSize(110, 54)

    def enterEvent(self, e):
        self._hover = True
        self.update()

    def leaveEvent(self, e):
        self._hover = False
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        if self.isChecked():
            p.setPen(Qt.NoPen)
            p.setBrush(QBrush(gradient(r)))
            p.drawRoundedRect(r, 12, 12)
            inner = r.adjusted(1.6, 1.6, -1.6, -1.6)
            bg = QLinearGradient(inner.topLeft(), inner.bottomRight())
            bg.setColorAt(0, QColor("#221C45"))
            bg.setColorAt(1, QColor("#122B36"))
            p.setBrush(QBrush(bg))
            p.drawRoundedRect(inner, 10.5, 10.5)
        else:
            p.setPen(QPen(QColor("#3A4158" if self._hover else BORDER), 1))
            p.setBrush(QColor(CARD_HI if self._hover else BG))
            p.drawRoundedRect(r, 12, 12)
        enabled = self.isEnabled()
        f = QFont(self.font())
        f.setPixelSize(16)
        f.setWeight(QFont.ExtraBold)
        p.setFont(f)
        p.setPen(QColor(TEXT if enabled else "#4A5066"))
        p.drawText(r.adjusted(0, 9, 0, -r.height() / 2 + 4), Qt.AlignHCenter | Qt.AlignVCenter, self.title)
        f.setPixelSize(11)
        f.setWeight(QFont.Medium)
        p.setFont(f)
        p.setPen(QColor((ACCENT2 if self.isChecked() else MUTED) if enabled else "#3A4056"))
        p.drawText(r.adjusted(4, r.height() / 2, -4, -8), Qt.AlignHCenter | Qt.AlignVCenter, self.desc)
        if self.tag:
            f.setPixelSize(9)
            f.setWeight(QFont.Bold)
            p.setFont(f)
            tr = QRectF(r.right() - 34, r.top() + 6, 28, 15)
            p.setPen(Qt.NoPen)
            p.setBrush(QColor("#1F3A3F" if enabled else "#1C2030"))
            p.drawRoundedRect(tr, 7, 7)
            p.setPen(QColor(ACCENT2 if enabled else "#3A4056"))
            p.drawText(tr, Qt.AlignCenter, self.tag)


class Segmented(QFrame):
    """مجموعة أزرار متجاورة لاختيار خيار واحد."""
    changed = Signal(int)

    def __init__(self, options, current=0):
        super().__init__()
        self.setObjectName("segWrap")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(4, 4, 4, 4)
        lay.setSpacing(4)
        self.group = QButtonGroup(self)
        self.buttons = []
        for i, text in enumerate(options):
            b = QPushButton(text)
            b.setObjectName("seg")
            b.setCheckable(True)
            b.setCursor(Qt.PointingHandCursor)
            self.group.addButton(b, i)
            lay.addWidget(b)
            self.buttons.append(b)
        self.buttons[min(current, len(options) - 1)].setChecked(True)
        self.group.idClicked.connect(self.changed.emit)

    def value(self):
        return self.group.checkedId()


class DropZone(QWidget):
    files_dropped = Signal(list)

    def __init__(self, glyph, title, hint):
        super().__init__()
        self.glyph, self.title, self.hint = glyph, title, hint
        self.setAcceptDrops(True)
        self.setCursor(Qt.PointingHandCursor)
        self.compact = False
        self._drag = False
        self._hover = False
        self.setFixedHeight(190)
        self.on_click = None

    def set_compact(self, compact):
        if compact != self.compact:
            self.compact = compact
            self.setFixedHeight(84 if compact else 190)
            self.update()

    def enterEvent(self, e):
        self._hover = True
        self.update()

    def leaveEvent(self, e):
        self._hover = False
        self.update()

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.LeftButton and self.on_click:
            self.on_click()

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()
            self._drag = True
            self.update()

    def dragLeaveEvent(self, e):
        self._drag = False
        self.update()

    def dropEvent(self, e):
        self._drag = False
        self.update()
        paths = []
        for url in e.mimeData().urls():
            path = url.toLocalFile()
            if os.path.isdir(path):
                for root, _, names in os.walk(path):
                    paths += [os.path.join(root, n) for n in sorted(names)]
            elif path:
                paths.append(path)
        self.files_dropped.emit(paths)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        active = self._drag or self._hover
        bg = QLinearGradient(r.topLeft(), r.bottomRight())
        bg.setColorAt(0, QColor("#1A1636" if self._drag else ("#161A28" if active else CARD)))
        bg.setColorAt(1, QColor("#0F2530" if self._drag else CARD))
        p.setBrush(QBrush(bg))
        pen = QPen(QBrush(gradient(r)) if active else QColor("#30374C"), 1.6, Qt.DashLine)
        pen.setDashPattern([5, 4])
        p.setPen(pen)
        p.drawRoundedRect(r, 18, 18)

        title_font = QFont(self.font())
        title_font.setPixelSize(16 if not self.compact else 14)
        title_font.setWeight(QFont.Bold)
        hint_font = QFont(self.font())
        hint_font.setPixelSize(12)

        if self.compact:
            ic = QRectF(r.right() - 64, r.center().y() - 22, 44, 44)
            self._badge(p, ic)
            text_r = QRectF(r.left() + 20, r.top(), ic.left() - r.left() - 34, r.height())
            p.setFont(title_font)
            p.setPen(QColor(TEXT))
            p.drawText(text_r.adjusted(0, 0, 0, -r.height() / 2 + 4), Qt.AlignRight | Qt.AlignBottom,
                       "أضف المزيد من الملفات")
            p.setFont(hint_font)
            p.setPen(QColor(MUTED))
            p.drawText(text_r.adjusted(0, r.height() / 2 + 4, 0, 0), Qt.AlignRight | Qt.AlignTop, self.hint)
            return

        ic = QRectF(r.center().x() - 30, r.top() + 30, 60, 60)
        self._badge(p, ic)
        p.setFont(title_font)
        p.setPen(QColor(TEXT))
        p.drawText(QRectF(r.left(), ic.bottom() + 14, r.width(), 24), Qt.AlignCenter, self.title)
        p.setFont(hint_font)
        p.setPen(QColor(MUTED))
        p.drawText(QRectF(r.left(), ic.bottom() + 40, r.width(), 20), Qt.AlignCenter, self.hint)

    def _badge(self, p, ic):
        glow = QColor(ACCENT1)
        glow.setAlpha(40 if not self._drag else 90)
        p.setPen(Qt.NoPen)
        p.setBrush(glow)
        p.drawEllipse(ic.adjusted(-6, -6, 6, 6))
        p.setBrush(QBrush(gradient(ic)))
        p.drawEllipse(ic)
        draw_glyph(p, "upload", ic.adjusted(ic.width() * .2, ic.height() * .2,
                                            -ic.width() * .2, -ic.height() * .2), "white")


class FileRow(QWidget):
    remove_requested = Signal(object)

    def __init__(self, job, glyph):
        super().__init__()
        self.job = job
        self.setFixedHeight(76)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(14, 10, 14, 10)
        lay.setSpacing(12)

        self.badge = QLabel()
        self.badge.setFixedSize(46, 46)
        self.badge.setAlignment(Qt.AlignCenter)
        self.badge.setPixmap(make_icon(glyph, ACCENT2, 22).pixmap(22, 22))
        self.badge.setStyleSheet(f"background:#1B2232; border:1px solid {BORDER}; border-radius:12px;")
        lay.addWidget(self.badge)

        mid = QVBoxLayout()
        mid.setSpacing(5)
        top = QHBoxLayout()
        top.setSpacing(8)
        self.name = label("", "rowName")
        self.name.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        top.addWidget(self.name, 1)
        self.status = label("جاهز", "rowMeta")
        top.addWidget(self.status)
        mid.addLayout(top)
        meta = [os.path.splitext(job.src)[1].lstrip(".").upper(), human_size(job.size)]
        if job.info.get("duration"):
            meta.append(human_time(job.info["duration"]))
        if job.info.get("width"):
            meta.append(f"{job.info['width']}×{job.info['height']}")
        self.meta = label("  ·  ".join(meta), "rowMeta")
        mid.addWidget(self.meta)
        self.bar = QProgressBar()
        self.bar.setFixedHeight(5)
        self.bar.setTextVisible(False)
        self.bar.setRange(0, 1000)
        self.bar.setValue(0)
        mid.addWidget(self.bar)
        lay.addLayout(mid, 1)

        self.reveal_btn = QPushButton("إظهار")
        self.reveal_btn.setObjectName("rowReveal")
        self.reveal_btn.setCursor(Qt.PointingHandCursor)
        self.reveal_btn.hide()
        self.reveal_btn.clicked.connect(lambda: reveal(self.job.dst))
        lay.addWidget(self.reveal_btn)

        self.x_btn = QPushButton("✕")
        self.x_btn.setObjectName("rowX")
        self.x_btn.setFixedSize(30, 30)
        self.x_btn.setCursor(Qt.PointingHandCursor)
        self.x_btn.setToolTip("إزالة من القائمة")
        self.x_btn.clicked.connect(lambda: self.remove_requested.emit(self.job))
        lay.addWidget(self.x_btn)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        fm = QFontMetrics(self.name.font())
        self.name.setText(fm.elidedText(os.path.basename(self.job.src), Qt.ElideMiddle,
                                        max(60, self.name.width())))
        self.name.setToolTip(self.job.src)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(QPen(QColor(BORDER), 1))
        p.setBrush(QColor(BG))
        p.drawRoundedRect(QRectF(self.rect()).adjusted(1, 3, -1, -3), 12, 12)

    def _set_bar_state(self, state):
        self.bar.setProperty("state", state)
        self.bar.style().unpolish(self.bar)
        self.bar.style().polish(self.bar)

    def refresh(self):
        j = self.job
        colors = {"pending": MUTED, "running": ACCENT2, "done": SUCCESS, "error": ERROR}
        self.status.setStyleSheet(f"color:{colors[j.state]}; font-size:12px; font-weight:700;")
        if j.state == "pending":
            self.status.setText(j.note or "جاهز")
            self.bar.setValue(0)
            self._set_bar_state("")
        elif j.state == "running":
            self.status.setText(f"{int(j.progress * 100)}%")
            self.bar.setValue(int(j.progress * 1000))
            self._set_bar_state("")
        elif j.state == "done":
            self.status.setText("✓ تم")
            self.bar.setValue(1000)
            self._set_bar_state("done")
        elif j.state == "error":
            self.status.setText("✕ " + (j.note or "فشل"))
            self.bar.setValue(1000)
            self._set_bar_state("error")
        self.status.setToolTip(j.detail or "")
        self.reveal_btn.setVisible(j.state == "done")
        self.x_btn.setEnabled(j.state != "running")
        if j.state == "done" and j.dst:
            self.meta.setText(f"{RLM}← {os.path.basename(j.dst)}  ·  {human_size(os.path.getsize(j.dst))}"
                              if os.path.exists(j.dst) else self.meta.text())


class Job:
    def __init__(self, src, info):
        self.src = src
        self.info = info
        self.size = os.path.getsize(src)
        self.state = "pending"
        self.progress = 0.0
        self.dst = None
        self.note = ""
        self.detail = ""
        self.row = None
        self.item = None


class Toast(QLabel):
    def __init__(self, parent):
        super().__init__(parent)
        self.setObjectName("toast")
        self.hide()
        self.effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.effect)
        self.anim = QPropertyAnimation(self.effect, b"opacity", self)
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self._fade)
        self.anim.finished.connect(self.hide)

    def show_message(self, text, color=TEXT, ms=3500):
        self.setText(text)
        self.setStyleSheet(f"color:{color};")
        self.adjustSize()
        # الزاوية العلوية اليسرى فارغة دائماً (العنوان على اليمين)
        self.move(32, 24)
        self.raise_()
        self.show()
        self.anim.stop()
        self.effect.setOpacity(1)
        self.timer.start(ms)

    def _fade(self):
        self.anim.setDuration(400)
        self.anim.setStartValue(1)
        self.anim.setEndValue(0)
        self.anim.setEasingCurve(QEasingCurve.OutCubic)
        self.anim.start()


# ---------------------------------------------------------------- صفحة التحويل

class ConverterPage(QWidget):
    """الهيكل المشترك: إسقاط ملفات، قائمة، خيارات، تشغيل FFmpeg بالتتابع."""
    busy_changed = Signal(bool)

    exts = ()
    accepts = ""  # وصف الملفات المقبولة لرسالة التنبيه
    glyph = "video"
    key = ""

    def __init__(self, window, title, pill, subtitle, drop_title, drop_hint, file_filter):
        super().__init__()
        self.window_ = window
        self.settings = app_settings()
        self.file_filter = file_filter
        self.jobs = []
        self.queue = []
        self.proc = None
        self.current = None
        self.cancelled = False
        self.out_dir = self.settings.value(f"{self.key}/out_dir", "") or ""
        if self.out_dir and not os.path.isdir(self.out_dir):
            self.out_dir = ""
        self.last_dst = None

        root = QVBoxLayout(self)
        root.setContentsMargins(32, 28, 32, 28)
        root.setSpacing(22)

        head = QHBoxLayout()
        tl = QVBoxLayout()
        tl.setSpacing(6)
        t_row = QHBoxLayout()
        t_row.setSpacing(12)
        t_row.addWidget(label(title, "pageTitle"))
        pill_lb = label(pill, "pill")
        t_row.addWidget(pill_lb, 0, Qt.AlignVCenter)
        t_row.addStretch()
        tl.addLayout(t_row)
        tl.addWidget(label(subtitle, "pageSub"))
        head.addLayout(tl)
        root.addLayout(head)

        body = QHBoxLayout()
        body.setSpacing(22)
        root.addLayout(body, 1)

        # عمود الملفات
        files_col = QVBoxLayout()
        files_col.setSpacing(16)
        self.drop = DropZone(self.glyph, drop_title, drop_hint)
        self.drop.on_click = self.browse
        self.drop.files_dropped.connect(self.add_files)
        files_col.addWidget(self.drop)

        files_card = card()
        fc = QVBoxLayout(files_card)
        fc.setContentsMargins(16, 14, 16, 12)
        fc.setSpacing(8)
        fh = QHBoxLayout()
        self.files_title = label("الملفات", "sectionTitle")
        fh.addWidget(self.files_title)
        fh.addStretch()
        self.clear_done_btn = QPushButton("إزالة المكتملة")
        self.clear_done_btn.setObjectName("linkBtn")
        self.clear_done_btn.setCursor(Qt.PointingHandCursor)
        self.clear_done_btn.clicked.connect(self.clear_done)
        fh.addWidget(self.clear_done_btn)
        self.clear_btn = QPushButton("مسح الكل")
        self.clear_btn.setObjectName("linkBtn")
        self.clear_btn.setCursor(Qt.PointingHandCursor)
        self.clear_btn.clicked.connect(self.clear_all)
        fh.addWidget(self.clear_btn)
        fc.addLayout(fh)

        self.list_stack = QStackedWidget()
        empty = QWidget()
        el = QVBoxLayout(empty)
        el.addStretch()
        empty_icon = QLabel()
        empty_icon.setAlignment(Qt.AlignCenter)
        empty_icon.setPixmap(make_icon(self.glyph, "#3A4158", 44).pixmap(44, 44))
        el.addWidget(empty_icon)
        e_lb = label("لا توجد ملفات بعد", "muted")
        e_lb.setAlignment(Qt.AlignCenter)
        el.addWidget(e_lb)
        el.addStretch()
        self.list_stack.addWidget(empty)
        self.list = QListWidget()
        self.list.setVerticalScrollMode(QListWidget.ScrollPerPixel)
        self.list.setSpacing(0)
        self.list.setSelectionMode(QListWidget.NoSelection)
        self.list.setFocusPolicy(Qt.NoFocus)
        self.list_stack.addWidget(self.list)
        fc.addWidget(self.list_stack, 1)
        files_col.addWidget(files_card, 1)
        body.addLayout(files_col, 1)

        # عمود الإعدادات
        side = QVBoxLayout()
        side.setSpacing(16)
        opt_card = card()
        oc = QVBoxLayout(opt_card)
        oc.setContentsMargins(18, 16, 18, 18)
        oc.setSpacing(0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        inner = QWidget()
        self.opts = QVBoxLayout(inner)
        self.opts.setContentsMargins(0, 0, 0, 0)
        self.opts.setSpacing(10)
        self.build_options(self.opts)
        self.opts.addStretch()
        scroll.setWidget(inner)
        oc.addWidget(scroll)
        side.addWidget(opt_card, 1)

        out_card = card()
        ol = QVBoxLayout(out_card)
        ol.setContentsMargins(18, 14, 18, 14)
        ol.setSpacing(8)
        ol.addWidget(label("مجلد الحفظ", "sectionTitle"))
        orow = QHBoxLayout()
        orow.setSpacing(8)
        fic = QLabel()
        fic.setPixmap(make_icon("folder", MUTED, 20).pixmap(20, 20))
        orow.addWidget(fic)
        self.out_label = label("", "muted")
        self.out_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        orow.addWidget(self.out_label, 1)
        self.out_btn = QPushButton("تغيير…")
        self.out_btn.setObjectName("ghostBtn")
        self.out_btn.setCursor(Qt.PointingHandCursor)
        self.out_btn.clicked.connect(self.choose_out_dir)
        orow.addWidget(self.out_btn)
        self.out_reset = QPushButton("↺")
        self.out_reset.setObjectName("ghostBtn")
        self.out_reset.setToolTip("الحفظ بجانب الملف الأصلي")
        self.out_reset.setCursor(Qt.PointingHandCursor)
        self.out_reset.clicked.connect(lambda: self.set_out_dir(""))
        orow.addWidget(self.out_reset)
        ol.addLayout(orow)
        files_col.addWidget(out_card)

        act = card()
        al = QVBoxLayout(act)
        al.setContentsMargins(18, 16, 18, 18)
        al.setSpacing(10)
        st = QHBoxLayout()
        self.summary = label("أضف ملفات للبدء", "muted")
        st.addWidget(self.summary, 1)
        self.overall_pct = label("", "sectionTitle")
        st.addWidget(self.overall_pct)
        al.addLayout(st)
        self.overall = QProgressBar()
        self.overall.setFixedHeight(6)
        self.overall.setTextVisible(False)
        self.overall.setRange(0, 1000)
        al.addWidget(self.overall)
        self.start_btn = QPushButton("ابدأ التحويل")
        self.start_btn.setObjectName("primaryBtn")
        self.start_btn.setCursor(Qt.PointingHandCursor)
        self.start_btn.clicked.connect(self.start)
        self.start_glow = QGraphicsDropShadowEffect(self.start_btn)
        self.start_glow.setBlurRadius(28)
        self.start_glow.setOffset(0, 6)
        self.start_glow.setColor(QColor(124, 92, 255, 90))
        self.start_btn.setGraphicsEffect(self.start_glow)
        al.addWidget(self.start_btn)
        self.cancel_btn = QPushButton("إيقاف")
        self.cancel_btn.setObjectName("dangerBtn")
        self.cancel_btn.setCursor(Qt.PointingHandCursor)
        self.cancel_btn.clicked.connect(self.cancel)
        self.cancel_btn.hide()
        al.addWidget(self.cancel_btn)
        self.open_btn = QPushButton("فتح مجلد الملفات المحوّلة")
        self.open_btn.setObjectName("ghostBtn")
        self.open_btn.setCursor(Qt.PointingHandCursor)
        self.open_btn.clicked.connect(lambda: reveal(self.last_dst))
        self.open_btn.hide()
        al.addWidget(self.open_btn)
        side.addWidget(act)

        side_w = QWidget()
        side_w.setLayout(side)
        side_w.setFixedWidth(420)
        body.addWidget(side_w)

        self.set_out_dir(self.out_dir)
        self.update_state()

    # --- تُعرّف في الصفحات الفرعية
    def build_options(self, lay):
        raise NotImplementedError

    def build_command(self, job, out_dir):
        raise NotImplementedError

    def options_changed(self):
        self.update_state()

    # --- الملفات
    def section(self, lay, text, top=8):
        lay.addSpacing(top)
        lay.addWidget(label(text, "sectionTitle"))

    def browse(self):
        if self.is_busy():
            return
        start = self.settings.value(f"{self.key}/last_dir", os.path.expanduser("~"))
        paths, _ = QFileDialog.getOpenFileNames(self, "اختر الملفات", start, self.file_filter)
        if paths:
            self.settings.setValue(f"{self.key}/last_dir", os.path.dirname(paths[0]))
            self.add_files(paths)

    def add_files(self, paths):
        if self.is_busy():
            self.window_.toast.show_message("انتظر حتى ينتهي التحويل الحالي", WARN)
            return
        added = skipped = 0
        known = {j.src for j in self.jobs}
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            for path in paths:
                if os.path.basename(path).startswith("."):
                    continue
                if os.path.splitext(path)[1].lower() not in self.exts:
                    skipped += 1
                    continue
                if path in known:
                    continue
                known.add(path)
                job = Job(path, engine.probe(path))
                job.row = FileRow(job, self.glyph)
                job.row.remove_requested.connect(self.remove_job)
                job.item = QListWidgetItem()
                job.item.setSizeHint(QSize(10, 76))
                self.list.addItem(job.item)
                self.list.setItemWidget(job.item, job.row)
                job.row.refresh()
                self.jobs.append(job)
                added += 1
        finally:
            QApplication.restoreOverrideCursor()
        if skipped:
            self.window_.toast.show_message(f"تم تجاهل {skipped} ملف — هذا القسم يقبل {self.accepts} فقط", WARN)
        elif added:
            self.window_.toast.show_message(f"تمت إضافة {added} ملف", SUCCESS, 1800)
        self.update_state()

    def remove_job(self, job):
        if job.state == "running":
            return
        self.list.takeItem(self.list.row(job.item))
        self.jobs.remove(job)
        self.update_state()

    def clear_all(self):
        if self.is_busy():
            return
        self.list.clear()
        self.jobs.clear()
        self.update_state()

    def clear_done(self):
        for job in [j for j in self.jobs if j.state == "done"]:
            self.remove_job(job)

    # --- مجلد الإخراج
    def choose_out_dir(self):
        d = QFileDialog.getExistingDirectory(self, "اختر مجلد الحفظ", self.out_dir or os.path.expanduser("~"))
        if d:
            self.set_out_dir(d)

    def set_out_dir(self, d):
        self.out_dir = d
        self.settings.setValue(f"{self.key}/out_dir", d)
        if d:
            fm = QFontMetrics(self.out_label.font())
            self.out_label.setText("‎" + fm.elidedText(d.replace(os.path.expanduser("~"), "~"),
                                                            Qt.ElideMiddle, 230))
            self.out_label.setToolTip(d)
        else:
            self.out_label.setText("بجانب الملف الأصلي")
            self.out_label.setToolTip("")
        self.out_reset.setVisible(bool(d))

    # --- الحالة
    def is_busy(self):
        return self.proc is not None

    def update_state(self):
        busy = self.is_busy()
        n = len(self.jobs)
        todo = [j for j in self.jobs if j.state in ("pending", "error")]
        done = sum(1 for j in self.jobs if j.state == "done")
        self.list_stack.setCurrentIndex(1 if n else 0)
        self.drop.set_compact(n > 0)
        self.files_title.setText(f"الملفات ({n})" if n else "الملفات")
        self.clear_btn.setEnabled(n > 0 and not busy)
        self.clear_done_btn.setVisible(done > 0 and not busy)
        self.start_btn.setVisible(not busy)
        self.cancel_btn.setVisible(busy)
        self.start_btn.setEnabled(bool(todo))
        self.start_glow.setEnabled(bool(todo))
        self.start_btn.setText(f"ابدأ التحويل ({len(todo)})" if len(todo) > 1 else "ابدأ التحويل")
        self.out_btn.setEnabled(not busy)
        if not busy:
            if not n:
                self.summary.setText("أضف ملفات للبدء")
            elif not todo:
                self.summary.setText(f"اكتمل تحويل {done} ملف ✓")
            else:
                self.summary.setText(self.estimate_text(todo) or f"{len(todo)} ملف بانتظار التحويل")

    def estimate_text(self, jobs):
        return ""

    # --- التشغيل
    def start(self):
        todo = [j for j in self.jobs if j.state in ("pending", "error")]
        if not todo:
            return
        for j in todo:
            j.state, j.progress, j.note, j.detail = "pending", 0.0, "في الانتظار", ""
            j.row.refresh()
        self.queue = todo
        self.total = len(todo)
        self.finished_count = 0
        self.ok_count = 0
        self.fail_count = 0
        self.cancelled = False
        self.overall.setValue(0)
        self.overall_pct.setText("0%")
        self.open_btn.hide()
        self.busy_changed.emit(True)
        self.next_job()

    def next_job(self):
        if self.cancelled or not self.queue:
            self.finish()
            return
        job = self.queue.pop(0)
        self.current = job
        out_dir = self.out_dir or os.path.dirname(job.src)
        try:
            if not os.access(out_dir, os.W_OK):
                raise engine.ConvertError("لا يمكن الكتابة في مجلد الحفظ")
            args, dst = self.build_command(job, out_dir)
        except engine.ConvertError as e:
            job.state, job.note = "error", str(e)
            job.row.refresh()
            self.fail_count += 1
            self.finished_count += 1
            QTimer.singleShot(0, self.next_job)
            return
        job.dst = dst
        job.state, job.progress = "running", 0.0
        job.row.refresh()
        self.list.scrollToItem(job.item)
        self.summary.setText(f"جارٍ تحويل {self.finished_count + 1} من {self.total}")
        self._stderr = b""
        self._buf = b""
        self.proc = QProcess(self)
        self.proc.readyReadStandardOutput.connect(self.on_stdout)
        self.proc.readyReadStandardError.connect(self.on_stderr)
        self.proc.finished.connect(self.on_finished)
        self.proc.errorOccurred.connect(self.on_proc_error)
        self.update_state()
        self.proc.start(engine.FFMPEG, args)

    def on_stdout(self):
        self._buf += bytes(self.proc.readAllStandardOutput())
        *lines, self._buf = self._buf.split(b"\n")
        job = self.current
        dur = job.info.get("duration") or 0
        for line in lines:
            if line.startswith(b"out_time_us=") and dur:
                try:
                    t = int(line.split(b"=")[1]) / 1e6
                except ValueError:
                    continue
                job.progress = max(0.0, min(0.999, t / dur))
            elif line.startswith(b"progress=end"):
                job.progress = 1.0
        job.row.refresh()
        overall = (self.finished_count + job.progress) / self.total
        self.overall.setValue(int(overall * 1000))
        self.overall_pct.setText(f"{int(overall * 100)}%")

    def on_stderr(self):
        self._stderr = (self._stderr + bytes(self.proc.readAllStandardError()))[-6000:]

    def on_proc_error(self, err):
        if err == QProcess.FailedToStart:
            self.on_finished(-1, None)

    def on_finished(self, code, _status):
        if self.proc is None:
            return
        job = self.current
        self.on_stderr()
        self.proc.deleteLater()
        self.proc = None
        if self.cancelled:
            if job.dst and os.path.exists(job.dst):
                os.remove(job.dst)
            job.state, job.note, job.progress = "pending", "أُلغي", 0.0
        elif code == 0 and job.dst and os.path.exists(job.dst):
            job.state, job.progress = "done", 1.0
            self.ok_count += 1
            self.last_dst = job.dst
        else:
            if job.dst and os.path.exists(job.dst):
                os.remove(job.dst)
            lines = [l for l in self._stderr.decode("utf-8", "replace").splitlines() if l.strip()]
            job.state, job.note = "error", "فشل التحويل"
            job.detail = "\n".join(lines[-4:]) or "تعذّر تشغيل FFmpeg"
            self.fail_count += 1
        job.row.refresh()
        self.finished_count += 1
        self.next_job()

    def cancel(self):
        if self.proc:
            self.cancelled = True
            for j in self.queue:
                j.note = ""
                j.row.refresh()
            self.queue = []
            self.proc.kill()

    def finish(self):
        self.current = None
        self.busy_changed.emit(False)
        self.update_state()
        if self.cancelled:
            self.overall.setValue(0)
            self.overall_pct.setText("")
            self.window_.toast.show_message("تم إيقاف التحويل", WARN)
            return
        self.overall.setValue(1000)
        self.overall_pct.setText("100%")
        if self.fail_count:
            self.summary.setText(f"نجح {self.ok_count} · فشل {self.fail_count} — مرّر الماوس على الخطأ للتفاصيل")
            self.window_.toast.show_message(f"انتهى التحويل مع {self.fail_count} خطأ", ERROR)
        else:
            self.summary.setText(f"اكتمل تحويل {self.ok_count} ملف بنجاح ✓")
            self.window_.toast.show_message("اكتمل التحويل بنجاح ✓", SUCCESS)
        self.open_btn.setVisible(self.ok_count > 0)
        QApplication.alert(self.window_)


FORMAT_HINTS = {
    "mp4": "H.264 + AAC — يعمل على كل الأجهزة والمنصات.",
    "mkv": "H.264 + AAC داخل حاوية Matroska — تحفظ عدة مسارات صوت.",
    "mov": "H.264 + AAC — مناسب لـ iMovie و Final Cut وأجهزة أبل.",
    "webm": "VP9 + Opus — حجم صغير بجودة عالية، مثالي للمواقع. (أبطأ في التحويل)",
    "wmv": "Windows Media Video — للتوافق مع برامج ويندوز القديمة.",
    "flv": "H.264 داخل حاوية Flash Video.",
    "mpeg": "MPEG-2 — مناسب لمشغلات DVD والأجهزة القديمة.",
    "3gp": "H.264 Baseline — للجوالات البسيطة.",
    "gif": "صورة متحركة بلوحة ألوان محسّنة (بدون صوت). الدقة الافتراضية 480p.",
    "mp3": "استخراج الصوت فقط بصيغة MP3 (عالية = 320kbps).",
    "m4a": "استخراج الصوت فقط بصيغة AAC.",
    "wav": "استخراج الصوت فقط بدون ضغط (أعلى جودة، حجم كبير).",
}


class VideoPage(ConverterPage):
    exts = engine.VIDEO_INPUT_EXTS
    accepts = "ملفات الفيديو"
    glyph = "video"
    key = "video"

    def __init__(self, window):
        patterns = " ".join(f"*{e} *{e.upper()}" for e in self.exts)
        super().__init__(window, "تحويل الفيديو", RLM + "أي فيديو ← أي صيغة",
                         "حوّل أي فيديو مثل MP4 و MOV و AVI و MKV إلى الصيغة التي تحتاجها للرفع، أو استخرج الصوت منه",
                         "اسحب ملفات الفيديو وأفلتها هنا",
                         "أو اضغط لاختيار الملفات — كل صيغ الفيديو، عدة ملفات ومجلدات",
                         f"ملفات الفيديو ({patterns})")

    def build_options(self, lay):
        s = self.settings
        self.section(lay, "صيغة الإخراج", 0)
        grid = QGridLayout()
        grid.setSpacing(8)
        self.fmt_group = QButtonGroup(self)
        current = s.value("video/format", "mp4")
        for i, (key, name, _, desc, audio) in enumerate(engine.VIDEO_FORMATS):
            t = Tile(name, desc, "صوت" if audio else None)
            t.setProperty("key", key)
            t.setToolTip(RLM + FORMAT_HINTS[key])
            self.fmt_group.addButton(t, i)
            grid.addWidget(t, i // 3, i % 3)
            if key == current:
                t.setChecked(True)
        if not self.fmt_group.checkedButton():
            self.fmt_group.button(0).setChecked(True)
        self.fmt_group.idClicked.connect(lambda _: self.options_changed())
        lay.addLayout(grid)

        self.section(lay, "الجودة")
        self.quality = Segmented(["عالية", "متوازنة", "حجم أصغر"], int(s.value("video/quality", 1)))
        self.quality.changed.connect(lambda _: self.options_changed())
        lay.addWidget(self.quality)

        self.section(lay, "الدقة")
        self.res = Segmented(["الأصلية", "1080p", "720p", "480p"], int(s.value("video/res", 0)))
        self.res.changed.connect(lambda _: self.options_changed())
        lay.addWidget(self.res)

    def fmt(self):
        return self.fmt_group.checkedButton().property("key")

    def options_changed(self):
        s = self.settings
        s.setValue("video/format", self.fmt())
        s.setValue("video/quality", self.quality.value())
        s.setValue("video/res", self.res.value())
        f = engine.FORMAT_BY_KEY[self.fmt()]
        audio_only = f[4]
        for b in self.res.buttons:
            b.setEnabled(not audio_only)
        self.update_state()

    def build_command(self, job, out_dir):
        height = [None, 1080, 720, 480][self.res.value()]
        return engine.build_video_cmd(job.src, out_dir, self.fmt(), self.quality.value(), height, job.info)

    def estimate_text(self, jobs):
        total = sum(j.info.get("duration") or 0 for j in jobs)
        name = engine.FORMAT_BY_KEY[self.fmt()][1]
        extra = f" · المدة {human_time(total)}" if total else ""
        return f"{len(jobs)} ملف ← {name}{extra}"


class AudioPage(ConverterPage):
    exts = engine.AUDIO_INPUT_EXTS
    accepts = "ملفات الصوت"
    glyph = "audio"
    key = "audio"

    BITRATES = [(320, "أعلى جودة"), (256, "ممتازة"), (192, "قياسية"), (128, "حجم صغير")]

    def __init__(self, window):
        patterns = " ".join(f"*{e} *{e.upper()}" for e in self.exts)
        super().__init__(window, "تحويل الصوت", RLM + "أي صوت ← MP3",
                         "حوّل أي ملف صوتي مثل WAV و M4A و FLAC و AIFF إلى MP3 مع الحفاظ على البيانات وصورة الغلاف",
                         "اسحب ملفات الصوت وأفلتها هنا",
                         "أو اضغط لاختيار الملفات — كل صيغ الصوت، عدة ملفات ومجلدات",
                         f"ملفات الصوت ({patterns})")

    def build_options(self, lay):
        s = self.settings
        self.section(lay, "معدل البت (kbps)", 0)
        grid = QGridLayout()
        grid.setSpacing(8)
        self.br_group = QButtonGroup(self)
        current = int(s.value("audio/bitrate", 320))
        for i, (br, desc) in enumerate(self.BITRATES):
            t = Tile(str(br), desc)
            t.setProperty("br", br)
            self.br_group.addButton(t, i)
            grid.addWidget(t, i // 2, i % 2)
            if br == current:
                t.setChecked(True)
        if not self.br_group.checkedButton():
            self.br_group.button(0).setChecked(True)
        self.br_group.idClicked.connect(lambda _: self.options_changed())
        lay.addLayout(grid)

        self.section(lay, "معدل العينة")
        self.sr = Segmented(["الأصلي", ltr("44.1 kHz"), ltr("48 kHz")], int(s.value("audio/sr", 0)))
        self.sr.changed.connect(lambda _: self.options_changed())
        lay.addWidget(self.sr)

        self.section(lay, "القنوات")
        self.ch = Segmented(["الأصلية", "ستيريو", "مونو"], int(s.value("audio/ch", 0)))
        self.ch.changed.connect(lambda _: self.options_changed())
        lay.addWidget(self.ch)

        self.hint = label("", "muted")
        self.hint.setWordWrap(True)
        lay.addSpacing(4)
        lay.addWidget(self.hint)

    def bitrate(self):
        return self.br_group.checkedButton().property("br")

    def options_changed(self):
        s = self.settings
        s.setValue("audio/bitrate", self.bitrate())
        s.setValue("audio/sr", self.sr.value())
        s.setValue("audio/ch", self.ch.value())
        self.hint.setText(f"ترميز LAME بمعدل ثابت {ltr(f'{self.bitrate()} kbps')} — "
                          f"الدقيقة الواحدة ≈ {ltr(f'{self.bitrate() * 60 / 8 / 1024:.1f} MB')}")
        self.update_state()

    def build_command(self, job, out_dir):
        sr = [None, 44100, 48000][self.sr.value()]
        ch = [None, 2, 1][self.ch.value()]
        return engine.build_audio_cmd(job.src, out_dir, self.bitrate(), sr, ch, job.info.get("cover"))

    def estimate_text(self, jobs):
        total = sum(j.info.get("duration") or 0 for j in jobs)
        src = sum(j.size for j in jobs)
        if not total:
            return f"{len(jobs)} ملف بانتظار التحويل"
        est = total * self.bitrate() * 1000 / 8
        return f"{len(jobs)} ملف · {ltr(human_size(src))} ← {ltr('≈ ' + human_size(est))}"


# ---------------------------------------------------------------- النافذة الرئيسية

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.resize(1280, 840)
        self.setMinimumSize(1120, 760)

        root = QWidget()
        root.setObjectName("root")
        self.setCentralWidget(root)
        lay = QHBoxLayout(root)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(250)
        sl = QVBoxLayout(sidebar)
        sl.setContentsMargins(18, 26, 18, 20)
        sl.setSpacing(6)
        brand = QHBoxLayout()
        brand.setSpacing(12)
        brand.addWidget(Logo(46))
        bt = QVBoxLayout()
        bt.setSpacing(1)
        bt.addWidget(label(APP_NAME, "appTitle"))
        bt.addWidget(label("MEDIA CONVERTER PRO", "appSub"))
        brand.addLayout(bt)
        brand.addStretch()
        sl.addLayout(brand)
        sl.addSpacing(30)
        sl.addWidget(label("الأدوات", "muted"))
        sl.addSpacing(4)

        self.stack = QStackedWidget()
        self.toast = Toast(root)
        self.pages = [VideoPage(self), AudioPage(self)]
        self.nav = QButtonGroup(self)
        navs = [("  تحويل الفيديو", "video", RLM + "أي فيديو ← MP4، MKV، MOV…"),
                ("  تحويل الصوت", "audio", RLM + "أي صوت ← MP3")]
        for i, (text, glyph, tip) in enumerate(navs):
            b = QPushButton(text)
            b.setObjectName("navBtn")
            b.setCheckable(True)
            b.setCursor(Qt.PointingHandCursor)
            b.setIcon(make_icon(glyph, ACCENT2, 20))
            b.setIconSize(QSize(20, 20))
            b.setToolTip(tip)
            self.nav.addButton(b, i)
            sl.addWidget(b)
            self.stack.addWidget(self.pages[i])
            self.pages[i].busy_changed.connect(self.on_busy)
        self.nav.idClicked.connect(self.stack.setCurrentIndex)
        start = int(app_settings().value("page", 0))
        self.nav.button(start).setChecked(True)
        self.stack.setCurrentIndex(start)

        sl.addStretch()
        eng = QFrame()
        eng.setObjectName("card")
        el = QHBoxLayout(eng)
        el.setContentsMargins(12, 10, 12, 10)
        dot = QLabel()
        dot.setFixedSize(8, 8)
        dot.setStyleSheet(f"background:{SUCCESS}; border-radius:4px;")
        el.addWidget(dot)
        ev = QVBoxLayout()
        ev.setSpacing(0)
        ev.addWidget(label("محرك التحويل جاهز", "sectionTitle"))
        ev.addWidget(label(f"FFmpeg {engine.ffmpeg_version()}", "muted"))
        el.addLayout(ev, 1)
        sl.addWidget(eng)

        lay.addWidget(sidebar)
        lay.addWidget(self.stack, 1)

    def on_busy(self, busy):
        # منع التنقل بين الصفحات أثناء التحويل
        for b in self.nav.buttons():
            b.setEnabled(not busy or b.isChecked())

    def closeEvent(self, e):
        app_settings().setValue("page", self.stack.currentIndex())
        busy = [p for p in self.pages if p.is_busy()]
        if busy:
            r = QMessageBox.question(self, APP_NAME, "يوجد تحويل قيد التنفيذ. هل تريد الإيقاف والخروج؟")
            if r != QMessageBox.Yes:
                e.ignore()
                return
            for p in busy:
                p.cancel()
                if p.proc:
                    p.proc.waitForFinished(3000)
        e.accept()


def export_icon(path):
    """يحفظ أيقونة التطبيق PNG بحجم 1024 (يُستخدم لبناء ملف .icns)."""
    logo_pixmap(1024).save(path)


def main():
    if "--version" in sys.argv:
        print(f"{APP_NAME} — FFmpeg {engine.ffmpeg_version()} ({engine.FFMPEG})")
        return
    if len(sys.argv) == 3 and sys.argv[1] == "--export-icon":
        app = QApplication(sys.argv)
        export_icon(sys.argv[2])
        return
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setLayoutDirection(Qt.RightToLeft)
    app.setWindowIcon(QIcon(logo_pixmap(512)))
    app.setStyleSheet(STYLE)
    w = MainWindow()
    dark_title_bar(w)
    w.show()
    for p in w.pages:
        p.options_changed()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
