# gui/tabs/temporal_tab.py
# Pure-PyQt6 implementation with improved chart aesthetics, "nice" Y-axis ticks,
# X- and Y-axis titles, and extra layout padding so axis titles don't overlap the plot.
import time
import datetime
import math
from collections import Counter

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QSizePolicy, QFrame
)
from PyQt6.QtCore import Qt, QRectF, QSize, QPointF
from PyQt6.QtGui import QPainter, QColor, QFontMetrics, QPen

# Import analytics engine (package-qualified so Anki finds it)
try:
    # analytics.__init__ should expose TemporalLearningPatterns
    from anki_stats_gui.analytics import TemporalLearningPatterns
except Exception:
    # As a fallback, try direct module import (in case __init__.py isn't exporting)
    try:
        from anki_stats_gui.analytics.temporal_patterns import TemporalLearningPatterns
    except Exception:
        TemporalLearningPatterns = None  # will be checked at runtime


def ms_now():
    return int(time.time() * 1000)


def ms_for_days_ago(days: int):
    return ms_now() - days * 24 * 60 * 60 * 1000


class MiniStat(QFrame):
    """Simple labeled stat used in the right-hand panel."""
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
        # make chart a bit larger by default so titles have room
        return QSize(560, 300)

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

        fm = QFontMetrics(self.font())
        label_height = fm.height() + 6

        # reserve extra vertical space for X-axis title if present
        xlabel_space = fm.height() + 6 if getattr(self, "xlabel", None) else 0
        bottom_area = int(label_height * 1.8 + xlabel_space + 6)
        top_area = 12

        # reserve extra horizontal space for Y-axis title if present
        ylabel_space = fm.height() + 10 if getattr(self, "ylabel", None) else 0

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
        max_tick_label = str(ticks[-1]) if ticks else str(max_val)
        y_label_width = fm.horizontalAdvance(max_tick_label) + 12 + ylabel_space

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

        # draw Y-axis tick labels
        painter.setPen(self._label_color)
        for t in ticks:
            if top_val == 0:
                y = plot_rect.bottom()
            else:
                y = plot_rect.bottom() - (t / top_val) * plot_rect.height()
            label_rect = QRectF(rect.left(), y - fm.height() / 2, y_label_width - ylabel_space - 8, fm.height())
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
        fm = QFontMetrics(self.font())
        for i, lbl in enumerate(self._labels):
            x = plot_rect.left() + spacing + i * (bar_width + spacing)
            label_rect = QRectF(x - spacing/2, plot_rect.bottom() + 6, bar_width + spacing, bottom_area - 6 - xlabel_space)
            elided = fm.elidedText(str(lbl), Qt.TextElideMode.ElideMiddle, int(label_rect.width()))
            painter.drawText(label_rect, Qt.AlignmentFlag.AlignCenter, elided)

        # draw X-axis title (put below the bar labels, in the extra reserved space)
        if getattr(self, "xlabel", None):
            painter.setPen(self._label_color)
            xlabel_rect = QRectF(plot_rect.left(), plot_rect.bottom() + bottom_area - xlabel_space + 2, plot_rect.width(), fm.height())
            painter.drawText(xlabel_rect, Qt.AlignmentFlag.AlignCenter, self.xlabel)

        # draw Y-axis title (rotated). position further left so it doesn't overlap tick labels.
        if getattr(self, "ylabel", None):
            painter.save()
            painter.setPen(self._label_color)
            # position: center of the Y-label/title area (left of plot)
            cx = rect.left() + (y_label_width - ylabel_space) / 2  # center between left edge and tick labels
            cy = plot_top + plot_height / 2
            painter.translate(cx, cy)
            painter.rotate(-90)
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

        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self.on_refresh)
        controls_layout.addWidget(self.refresh_btn)
        controls_layout.addStretch()

        # Left: charts stack (hourly, weekday) - Qt-only charts
        charts_layout = QVBoxLayout()

        charts_layout.addWidget(QLabel("<b>Reviews by Hour of Day</b>"))
        self.hour_chart = SimpleBarChart(
            [str(i) for i in range(24)], [0]*24,
            xlabel="Hour of day", ylabel="Reviews"
        )
        charts_layout.addWidget(self.hour_chart, 2)

        charts_layout.addWidget(QLabel("<b>Reviews by Weekday</b>"))
        weekday_labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        self.week_chart = SimpleBarChart(
            weekday_labels, [0]*7,
            xlabel="Weekday", ylabel="Reviews"
        )
        charts_layout.addWidget(self.week_chart, 1)

        # Right: small stats
        stats_layout = QVBoxLayout()
        self.stat_most_hour = MiniStat("Most Active Hour", "-")
        self.stat_most_weekday = MiniStat("Most Active Weekday", "-")
        self.stat_total_reviews = MiniStat("Total Reviews", "-")
        self.stat_avg_session = MiniStat("Avg Session Length (min)", "-")
        self.stat_session_count = MiniStat("Session Count", "-")

        stats_layout.addWidget(self.stat_most_hour)
        stats_layout.addWidget(self.stat_most_weekday)
        stats_layout.addWidget(self.stat_total_reviews)
        stats_layout.addWidget(self.stat_avg_session)
        stats_layout.addWidget(self.stat_session_count)
        stats_layout.addStretch()

        # Combine left/right
        body_layout = QHBoxLayout()
        left_widget = QWidget()
        left_widget.setLayout(charts_layout)
        body_layout.addWidget(left_widget, 3)

        right_widget = QWidget()
        right_widget.setLayout(stats_layout)
        right_widget.setMaximumWidth(300)
        body_layout.addWidget(right_widget, 1)

        # Main layout
        main_layout = QVBoxLayout()
        main_layout.addLayout(controls_layout)
        main_layout.addLayout(body_layout)
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
            revlog = self.engine.fetch_revlog()
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