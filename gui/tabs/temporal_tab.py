# File location
# gui/tabs/temporal_tab.py

#Import necessary libraries and modules
import time
import datetime
import math
from collections import Counter
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QSizePolicy, QFrame
)
from PyQt6.QtCore import Qt, QRectF, QSize, QPointF
from PyQt6.QtGui import QPainter, QColor, QFontMetrics, QPen, QFont
try:
    from anki_stats_gui.analytics import TemporalLearningPatterns
except Exception:
    try:
        from anki_stats_gui.analytics.temporal_patterns import TemporalLearningPatterns
    except Exception:
        TemporalLearningPatterns = None  # will be checked at runtime
from aqt import mw

#Retrieve and format data from analytics module
def ms_now():
    return int(time.time() * 1000)

def ms_for_days_ago(days: int):
    return ms_now() - days * 24 * 60 * 60 * 1000

def _format_hour_label(h: int) -> str:
    """Return hour label in 12-hour short form like '7 p' or '8 a'.
    0 -> '12 a', 12 -> '12 p', 13 -> '1 p', etc.
    """
    h = int(h) % 24
    suffix = 'a' if h < 12 else 'p'
    hour12 = h % 12
    if hour12 == 0:
        hour12 = 12
    return f"{hour12} {suffix}"

#
class MiniStat(QFrame):
    #Simple labeled stat used in panel.
    def __init__(self, title: str, value: str):
        super().__init__()
        self.setFrameShape(QFrame.Shape.StyledPanel)
        layout = QVBoxLayout()
        t = QLabel(f"<b>{title}</b>")
        t.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v = QLabel(value)
        v.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v.setWordWrap(True)
        layout.addWidget(t)
        layout.addWidget(v)
        self.setLayout(layout)

    def set_value(self, value: str):
        # second child is the value label
        self.layout().itemAt(1).widget().setText(value)


def _nice_ticks(max_val: float, desired_ticks: int = 5):
    """Return a list of "nice" tick values from 0..top inclusive.
    Ensures integer step >= 1 when max_val >= 1 (counts are integer).
    Steps chosen from 1,2,5 * 10^exp to make tick labels round.
    """
    if max_val <= 0:
        return [0]

    raw_step = float(max_val) / desired_ticks
    exp = math.floor(math.log10(raw_step)) if raw_step > 0 else 0
    mag = 10 ** exp
    residual = raw_step / mag if mag != 0 else raw_step

    if residual <= 1.5:
        nice = 1
    elif residual <= 3:
        nice = 2
    elif residual <= 7:
        nice = 5
    else:
        nice = 10

    step = nice * mag

    # Since review counts are integers, prefer integer step >= 1
    if max_val >= 1 and step < 1:
        step = 1

    # Round step to int if it is effectively integer
    if abs(round(step) - step) < 1e-9:
        step = int(round(step))

    top = math.ceil(max_val / step) * step
    ticks = []
    v = 0
    max_iters = 1000
    it = 0
    while v <= top + 1e-9 and it < max_iters:
        if abs(round(v) - v) < 1e-9:
            ticks.append(int(round(v)))
        else:
            ticks.append(v)
        v += step
        it += 1

    ticks = sorted(set(ticks))
    return ticks


class SimpleBarChart(QWidget):
    """A lightweight bar chart drawn with QPainter. Labels and values lists must match.
    Improvements:
    - Rounded bars
    - Subtle grid lines
    - Left-side numeric Y-axis with "nice" tick labels (no duplicates, rounded multiples)
    - X- and Y-axis titles
    - Extra reserved space so axis titles don't overlap the plot
    """
    def __init__(self, labels=None, values=None, xlabel="", ylabel="", parent=None):
        super().__init__(parent)
        self._labels = labels or []
        self._values = values or []
        self.xlabel = xlabel
        self.ylabel = ylabel
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        # Colors and style
        self._bar_color = QColor(60, 130, 180)  # pleasant steel-blue
        self._bar_border = QColor(40, 90, 130)
        self._grid_color = QColor(220, 220, 220)
        self._label_color = QColor(40, 40, 40)
        self._bg_color = QColor(250, 250, 250)
        self._margin = 10
        self._desired_ticks = 5

    def sizeHint(self) -> QSize:
        # make chart wider than tall by default so titles have room
        return QSize(720, 320)

    def set_data(self, labels, values):
        self._labels = labels or []
        self._values = values or []
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect().adjusted(self._margin, self._margin, -self._margin, -self._margin)

        # background
        painter.fillRect(rect, self._bg_color)

        # use a slightly smaller font for tick/axis numbers to avoid overlap
        base_font = self.font()
        label_font = QFont(base_font)
        # reduce point size a couple of points where possible
        try:
            ps = base_font.pointSize()
        except Exception:
            ps = -1
        if ps <= 0:
            ps_new = 9
        else:
            ps_new = max(7, ps - 2)
        label_font.setPointSize(ps_new)
        fm = QFontMetrics(label_font)
        label_height = fm.height() + 6

        # reserve extra vertical space for X-axis title if present
        # add a bit more padding so long tick labels or titles don't collide
        xlabel_space = fm.height() + 8 if getattr(self, "xlabel", None) else 0
        bottom_area = int(label_height * 2.2 + xlabel_space + 8)
        top_area = 12

        # reserve extra horizontal space for Y-axis title if present
        # increase padding to keep rotated title clear of tick labels
        ylabel_space = fm.height() + 18 if getattr(self, "ylabel", None) else 0

        # handle empty or all-zero data
        if not self._values or max(self._values) == 0:
            painter.setPen(self._label_color)
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, "No data")
            painter.end()
            return

        max_val = max(self._values)
        n = len(self._values)

        # compute ticks
        ticks = _nice_ticks(max_val, self._desired_ticks)
        top_val = ticks[-1] if ticks else max_val

        # reserve left margin for Y labels plus enough space for rotated Y title
        # compute maximum tick label width from all ticks so labels never overlap
        try:
            max_tick_label = max((str(t) for t in ticks), key=lambda s: fm.horizontalAdvance(s)) if ticks else str(max_val)
            max_tick_w = fm.horizontalAdvance(max_tick_label)
        except Exception:
            max_tick_w = fm.horizontalAdvance(str(ticks[-1])) if ticks else fm.horizontalAdvance(str(max_val))
        # leave additional padding so the rotated Y title doesn't overlap tick labels
        y_label_width = max_tick_w + 20 + ylabel_space

        plot_left = rect.left() + y_label_width
        plot_right = rect.right()
        plot_top = rect.top() + top_area
        plot_bottom = rect.bottom() - bottom_area
        plot_width = max(4, plot_right - plot_left)
        plot_height = max(4, plot_bottom - plot_top)
        plot_rect = QRectF(plot_left, plot_top, plot_width, plot_height)

        spacing = max(2, int(plot_rect.width() * 0.02))
        bar_total_width = plot_rect.width() - spacing * (n + 1)
        bar_width = max(6, int(bar_total_width / n)) if n else 0
        radius = max(1, min(8, bar_width // 3))

        # draw horizontal grid lines at tick positions
        painter.setPen(QPen(self._grid_color))
        for t in ticks:
            if top_val == 0:
                y = plot_rect.bottom()
            else:
                y = plot_rect.bottom() - (t / top_val) * plot_rect.height()
            p1 = QPointF(plot_rect.left(), y)
            p2 = QPointF(plot_rect.right(), y)
            painter.drawLine(p1, p2)

        # draw Y-axis line
        painter.setPen(QPen(self._label_color))
        painter.drawLine(QPointF(plot_rect.left(), plot_rect.top()), QPointF(plot_rect.left(), plot_rect.bottom()))

        # draw Y-axis tick labels (use the smaller label font)
        painter.setFont(label_font)
        painter.setPen(self._label_color)
        for t in ticks:
            if top_val == 0:
                y = plot_rect.bottom()
            else:
                y = plot_rect.bottom() - (t / top_val) * plot_rect.height()
            # limit width to available left margin minus some safety padding
            label_rect = QRectF(rect.left(), y - fm.height() / 2, max(12, y_label_width - 14), fm.height())
            painter.drawText(label_rect, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, str(t))

        # draw bars with rounded corners and a small border
        for i, v in enumerate(self._values):
            x = plot_rect.left() + spacing + i * (bar_width + spacing)
            height = (v / top_val) * plot_rect.height() if top_val else 0
            y = plot_rect.bottom() - height
            bar_rect = QRectF(x, y, bar_width, height)
            painter.setPen(QPen(self._bar_border))
            painter.setBrush(self._bar_color)
            painter.drawRoundedRect(bar_rect, radius, radius)

        # draw labels under bars (elided if needed)
        painter.setPen(self._label_color)
        # keep using the smaller label font/metrics for tick labels under bars
        fm = QFontMetrics(label_font)
        for i, lbl in enumerate(self._labels):
            x = plot_rect.left() + spacing + i * (bar_width + spacing)
            label_rect = QRectF(x - spacing/2, plot_rect.bottom() + 6, bar_width + spacing, bottom_area - 6 - xlabel_space)
            elided = fm.elidedText(str(lbl), Qt.TextElideMode.ElideMiddle, int(label_rect.width()))
            painter.drawText(label_rect, Qt.AlignmentFlag.AlignCenter, elided)

        # draw X-axis title (put below the bar labels, in the extra reserved space)
        if getattr(self, "xlabel", None):
            # use a slightly larger/bold font for axis titles
            title_font = QFont(base_font)
            try:
                title_font.setPointSize(max(9, ps_new + 1))
            except Exception:
                pass
            title_font.setBold(True)
            painter.setFont(title_font)
            painter.setPen(self._label_color)
            xlabel_rect = QRectF(plot_rect.left(), plot_rect.bottom() + bottom_area - xlabel_space + 2, plot_rect.width(), fm.height())
            painter.drawText(xlabel_rect, Qt.AlignmentFlag.AlignCenter, self.xlabel)

        # draw Y-axis title (rotated). position further left so it doesn't overlap tick labels.
        if getattr(self, "ylabel", None):
            painter.save()
            painter.setPen(self._label_color)
            # move Y title further left away from the plot by applying an extra shift
            y_title_shift = 12 + (ylabel_space // 4)
            cx = rect.left() + (y_label_width) / 2 - y_title_shift
            cy = plot_top + plot_height / 2
            painter.translate(cx, cy)
            painter.rotate(-90)
            # use title font for the Y label as well
            title_font = QFont(base_font)
            try:
                title_font.setPointSize(max(9, ps_new + 1))
            except Exception:
                pass
            title_font.setBold(True)
            painter.setFont(title_font)
            # draw centered vertically along the rotated axis
            rotated_rect = QRectF(-plot_height / 2, -fm.height() / 2, plot_height, fm.height())
            painter.drawText(rotated_rect, Qt.AlignmentFlag.AlignCenter, self.ylabel)
            painter.restore()

        painter.end()


class TemporalTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        # Analytics engine instance (has fetch_revlog and compute helpers)
        if TemporalLearningPatterns is None:
            # We'll keep the tab functional but mark engine as unavailable; on_refresh will show error.
            self.engine = None
        else:
            self.engine = TemporalLearningPatterns()

        # Top controls: time range + refresh
        controls_layout = QHBoxLayout()
        self.range_select = QComboBox()
        self.range_select.addItems(["7 days", "30 days", "90 days", "All time"])
        controls_layout.addWidget(QLabel("Range:"))
        controls_layout.addWidget(self.range_select)

        # Deck selector: allow user to choose a specific deck (default: All decks)
        self.deck_select = QComboBox()
        # top entry means "include data from any deck"; store None as itemData
        self.deck_select.addItem("Any deck (all data)", None)
        try:
            decks = mw.col.decks.decks()
            # decks() returns a mapping of id -> info dict with 'name'
            items = [(did, info.get("name") if isinstance(info, dict) else str(info)) for did, info in decks.items()]
            # sort by name for predictable ordering and store numeric id as itemData
            for did, name in sorted(items, key=lambda x: x[1].lower() if x[1] else ""):
                self.deck_select.addItem(name, did)
        except Exception:
            # best-effort fallback: try to fetch by name list and resolve ids
            try:
                names = mw.col.decks.all_names()
                for name in names:
                    try:
                        did = mw.col.decks.id(name)
                        self.deck_select.addItem(name, did)
                    except Exception:
                        pass
            except Exception:
                pass
        controls_layout.addWidget(QLabel("Deck:"))
        controls_layout.addWidget(self.deck_select)
        # Refresh charts automatically when the selected deck changes
        try:
            self.deck_select.currentIndexChanged.connect(self.on_refresh)
        except Exception:
            # if connecting fails for any reason, ignore; user can still hit Refresh
            pass

        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self.on_refresh)
        controls_layout.addWidget(self.refresh_btn)
        controls_layout.addStretch()

        # Left: charts area — arrange two charts side-by-side (each with title above)
        charts_layout = QHBoxLayout()

        # Hour chart container (title + chart)
        hour_container = QWidget()
        hour_v = QVBoxLayout()
        title = QLabel("<b>Reviews by Hour of Day</b>")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hour_v.addWidget(title)
        self.hour_chart = SimpleBarChart(
            [str(i) for i in range(24)], [0]*24,
            xlabel="Hour of day", ylabel="Reviews"
        )
        hour_v.addWidget(self.hour_chart)
        hour_container.setLayout(hour_v)

        # Weekday chart container (title + chart)
        week_container = QWidget()
        week_v = QVBoxLayout()
        title = QLabel("<b>Reviews by Weekday</b>")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        week_v.addWidget(title)
        weekday_labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        self.week_chart = SimpleBarChart(
            weekday_labels, [0]*7,
            xlabel="Weekday", ylabel="Reviews"
        )
        week_v.addWidget(self.week_chart)
        week_container.setLayout(week_v)

        charts_layout.addWidget(hour_container, 1)
        charts_layout.addWidget(week_container, 1)

        # Top: small stats laid out horizontally (panel across the top)
        stats_h = QHBoxLayout()
        self.stat_most_hour = MiniStat("Most Active Hour", "-")
        self.stat_most_weekday = MiniStat("Most Active Weekday", "-")
        self.stat_total_reviews = MiniStat("Total Reviews", "-")
        self.stat_avg_session = MiniStat("Avg Session Length (min)", "-")
        self.stat_session_count = MiniStat("Session Count", "-")

        # Make stats display side-by-side and expand horizontally
        for w in (self.stat_most_hour, self.stat_most_weekday, self.stat_total_reviews, self.stat_avg_session, self.stat_session_count):
            w.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
            stats_h.addWidget(w)

        stats_widget = QWidget()
        stats_widget.setLayout(stats_h)

        # Charts widget: place both charts side-by-side across available width
        charts_widget = QWidget()
        charts_widget.setLayout(charts_layout)

        # Main layout: controls, top stats panel, then charts across full width
        main_layout = QVBoxLayout()
        main_layout.addLayout(controls_layout)
        main_layout.addWidget(stats_widget)
        main_layout.addWidget(charts_widget, 1)
        self.setLayout(main_layout)

        # Initial draw
        self.on_refresh()

    def _get_time_threshold_ms(self):
        sel = self.range_select.currentText()
        if sel == "7 days":
            return ms_for_days_ago(7)
        if sel == "30 days":
            return ms_for_days_ago(30)
        if sel == "90 days":
            return ms_for_days_ago(90)
        return 0  # All time

    def _filter_revlog_by_time(self, revlog_rows, since_ms: int):
        if since_ms <= 0:
            return revlog_rows
        return [r for r in revlog_rows if r[0] >= since_ms]

    def _plot_hourly_distribution_qt(self, hour_counter: Counter):
        labels = [str(i) for i in range(24)]
        counts = [hour_counter.get(h, 0) for h in range(24)]
        self.hour_chart.set_data(labels, counts)

    def _plot_weekday_distribution_qt(self, weekday_counter: Counter):
        labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        counts = [weekday_counter.get(i, 0) for i in range(7)]
        self.week_chart.set_data(labels, counts)

    def on_refresh(self):
        """Fetch revlog, filter by time range, compute distributions, and redraw."""
        if self.engine is None:
            self._set_error_state("Analytics engine unavailable.")
            return

        try:
            # get deck selection: we store None for "Any deck" or numeric did for real decks
            deck_id = None
            if getattr(self, 'deck_select', None):
                try:
                    deck_id = self.deck_select.currentData()
                except Exception:
                    deck_id = None
            revlog = self.engine.fetch_revlog(deck_id)
            # DEBUG: show how many rows were fetched and which deck id was used
            try:
                print(f"[temporal_tab] fetch_revlog returned {len(revlog)} rows for deck_id={deck_id}")
            except Exception:
                print("[temporal_tab] fetch_revlog returned (unable to determine length)")
            try:
                # temporarily show fetch count in the Total Reviews stat to help debugging
                self.stat_total_reviews.set_value(f"Fetched: {len(revlog)} (deck={deck_id})")
            except Exception:
                pass
        except Exception as e:
            self._set_error_state(f"Unable to load revlog: {e}")
            return

        since_ms = self._get_time_threshold_ms()
        revlog = self._filter_revlog_by_time(revlog, since_ms)

        if not revlog:
            self._set_error_state("No reviews in selected range.")
            return

        # Compute distributions
        hours = []
        weekdays = []
        for row in revlog:
            ts_ms = row[0]
            dt = datetime.datetime.fromtimestamp(ts_ms / 1000)
            hours.append(dt.hour)
            weekdays.append(dt.weekday())

        hour_counter = Counter(hours)
        weekday_counter = Counter(weekdays)

        # Session lengths: group by gaps > 15 minutes
        timestamps = sorted([r[0] for r in revlog])
        session_lengths = []
        session_start = timestamps[0]
        previous = timestamps[0]
        for t in timestamps[1:]:
            gap_minutes = (t - previous) / 1000 / 60
            if gap_minutes > 15:
                session_lengths.append((previous - session_start) / 1000 / 60)
                session_start = t
            previous = t
        session_lengths.append((previous - session_start) / 1000 / 60)

        # derive top-level stats safely
        most_active_hour = hour_counter.most_common(1)[0][0] if hour_counter else 0
        weekday_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        most_active_day_index = weekday_counter.most_common(1)[0][0] if weekday_counter else 0
        most_active_weekday = weekday_names[most_active_day_index]
        total_reviews = len(revlog)
        avg_session = round(sum(session_lengths) / len(session_lengths), 2) if session_lengths else 0
        session_count = len(session_lengths)

        # Update stats UI
        self.stat_most_hour.set_value(f"{most_active_hour}:00")
        self.stat_most_weekday.set_value(most_active_weekday)
        self.stat_total_reviews.set_value(str(total_reviews))
        self.stat_avg_session.set_value(str(avg_session))
        self.stat_session_count.set_value(str(session_count))

        # Draw charts (Qt-only)
        try:
            self._plot_hourly_distribution_qt(hour_counter)
            self._plot_weekday_distribution_qt(weekday_counter)
        except Exception as e:
            # if something fails, show empty charts and error in stats
            self._set_error_state(f"Plot error: {e}")

    def _set_error_state(self, message: str):
        # Clear charts and set stats to message
        if getattr(self, "hour_chart", None):
            try:
                self.hour_chart.set_data([str(i) for i in range(24)], [0]*24)
            except Exception:
                pass
        if getattr(self, "week_chart", None):
            try:
                self.week_chart.set_data(["Mon","Tue","Wed","Thu","Fri","Sat","Sun"], [0]*7)
            except Exception:
                pass

        self.stat_most_hour.set_value("-")
        self.stat_most_weekday.set_value("-")
        self.stat_total_reviews.set_value(message)
        self.stat_avg_session.set_value("-")
        self.stat_session_count.set_value("-")