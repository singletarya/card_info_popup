# gui/tabs/temporal_tab.py
# Combined implementation that:
# - Uses matplotlib if available (optional)
# - Falls back to a pure-PyQt6 SimpleBarChart when matplotlib is absent
# - Uses package-qualified imports so Anki can resolve modules inside the add-on
# - Avoids import-time crashes for optional dependencies
import time
import datetime
from collections import Counter

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QSizePolicy, QFrame
)
from PyQt6.QtCore import Qt, QRectF, QSize, QPointF
from PyQt6.QtGui import QPainter, QColor, QFontMetrics, QPen

# Try to import matplotlib if available (optional nicer rendering)
_HAS_MATPLOTLIB = True
try:
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
except Exception:
    Figure = None
    FigureCanvas = None
    _HAS_MATPLOTLIB = False

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


class SimpleBarChart(QWidget):
    """A lightweight bar chart drawn with QPainter. Labels and values lists must match."""
    def __init__(self, labels=None, values=None, xlabel="", ylabel="", parent=None):
        super().__init__(parent)
        self._labels = labels or []
        self._values = values or []
        self.xlabel = xlabel
        self.ylabel = ylabel
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._bar_color = QColor(70, 130, 180)  # steelblue
        self._grid_color = QColor(200, 200, 200)
        self._label_color = QColor(30, 30, 30)
        self._margin = 10

    def sizeHint(self) -> QSize:
        return QSize(400, 200)

    def set_data(self, labels, values):
        self._labels = labels
        self._values = values
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect().adjusted(self._margin, self._margin, -self._margin, -self._margin)

        # background
        painter.fillRect(rect, QColor(255, 255, 255))

        # determine drawing area
        fm = QFontMetrics(self.font())
        label_height = fm.height() + 6
        bottom_area = int(label_height * 1.6)
        top_area = 10
        plot_rect = QRectF(rect.left(), rect.top() + top_area,
                           rect.width(), rect.height() - bottom_area - top_area)

        # handle empty data
        if not self._values:
            painter.setPen(self._label_color)
            painter.drawText(plot_rect, Qt.AlignmentFlag.AlignCenter, "No data")
            painter.end()
            return

        max_val = max(self._values) or 1
        n = len(self._values)
        spacing = max(2, int(plot_rect.width() * 0.02))
        bar_total_width = plot_rect.width() - spacing * (n + 1)
        bar_width = max(4, int(bar_total_width / n)) if n else 0

        # draw horizontal gridlines (5 lines) using QPointF to avoid float/int overload mismatch
        painter.setPen(QPen(self._grid_color))
        for i in range(6):
            y = plot_rect.top() + (plot_rect.height() * i / 5.0)
            p1 = QPointF(plot_rect.left(), y)
            p2 = QPointF(plot_rect.right(), y)
            painter.drawLine(p1, p2)

        # draw bars
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(self._bar_color)
        for i, v in enumerate(self._values):
            x = plot_rect.left() + spacing + i * (bar_width + spacing)
            height = (v / max_val) * plot_rect.height()
            y = plot_rect.bottom() - height
            painter.drawRect(QRectF(x, y, bar_width, height))

        # draw labels under bars
        painter.setPen(self._label_color)
        fm = QFontMetrics(self.font())
        for i, lbl in enumerate(self._labels):
            x = plot_rect.left() + spacing + i * (bar_width + spacing)
            label_rect = QRectF(x - spacing/2, plot_rect.bottom() + 4, bar_width + spacing, bottom_area - 4)
            elided = fm.elidedText(str(lbl), Qt.TextElideMode.ElideMiddle, int(label_rect.width()))
            painter.drawText(label_rect, Qt.AlignmentFlag.AlignCenter, elided)

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

        # Left: charts stack (hourly, weekday)
        charts_layout = QVBoxLayout()

        # Use matplotlib if available otherwise SimpleBarChart
        if _HAS_MATPLOTLIB:
            self.fig_hour = Figure(figsize=(5, 2.5), tight_layout=True)
            self.canvas_hour = FigureCanvas(self.fig_hour)
            self.canvas_hour.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            charts_layout.addWidget(QLabel("<b>Reviews by Hour of Day</b>"))
            charts_layout.addWidget(self.canvas_hour, 2)

            self.fig_week = Figure(figsize=(5, 2.0), tight_layout=True)
            self.canvas_week = FigureCanvas(self.fig_week)
            self.canvas_week.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            charts_layout.addWidget(QLabel("<b>Reviews by Weekday</b>"))
            charts_layout.addWidget(self.canvas_week, 1)
        else:
            # Pure-Qt fallback charts
            charts_layout.addWidget(QLabel("<b>Reviews by Hour of Day</b>"))
            self.hour_chart = SimpleBarChart([str(i) for i in range(24)], [0]*24)
            charts_layout.addWidget(self.hour_chart, 2)

            charts_layout.addWidget(QLabel("<b>Reviews by Weekday</b>"))
            weekday_labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
            self.week_chart = SimpleBarChart(weekday_labels, [0]*7)
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
        right_widget.setMaximumWidth(280)
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

    def _plot_hourly_distribution_matplotlib(self, hour_counter: Counter):
        ax = self.fig_hour.subplots()
        ax.clear()
        hours = list(range(24))
        counts = [hour_counter.get(h, 0) for h in hours]
        ax.bar(hours, counts, align="center")
        ax.set_xlabel("Hour of day")
        ax.set_ylabel("Reviews")
        ax.set_xticks(hours)
        ax.set_xlim(-0.5, 23.5)
        ax.grid(axis="y", linestyle=":", alpha=0.5)
        self.canvas_hour.draw()

    def _plot_weekday_distribution_matplotlib(self, weekday_counter: Counter):
        ax = self.fig_week.subplots()
        ax.clear()
        weekday_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        counts = [weekday_counter.get(i, 0) for i in range(7)]
        ax.bar(range(7), counts, align="center")
        ax.set_xticks(range(7))
        ax.set_xticklabels(weekday_names)
        ax.set_xlabel("Weekday")
        ax.set_ylabel("Reviews")
        ax.grid(axis="y", linestyle=":", alpha=0.5)
        self.canvas_week.draw()

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

        # Draw charts (choose matplotlib if available)
        if _HAS_MATPLOTLIB and Figure and FigureCanvas:
            try:
                self._plot_hourly_distribution_matplotlib(hour_counter)
                self._plot_weekday_distribution_matplotlib(weekday_counter)
            except Exception:
                # If matplotlib fails at runtime, fall back to Qt charts
                self._plot_hourly_distribution_qt(hour_counter)
                self._plot_weekday_distribution_qt(weekday_counter)
        else:
            self._plot_hourly_distribution_qt(hour_counter)
            self._plot_weekday_distribution_qt(weekday_counter)

    def _set_error_state(self, message: str):
        # Clear charts and set stats to message
        if _HAS_MATPLOTLIB and getattr(self, "fig_hour", None):
            try:
                self.fig_hour.clear()
                self.canvas_hour.draw()
                self.fig_week.clear()
                self.canvas_week.draw()
            except Exception:
                pass
        else:
            # set charts to empty data
            if getattr(self, "hour_chart", None):
                self.hour_chart.set_data([str(i) for i in range(24)], [0]*24)
            if getattr(self, "week_chart", None):
                self.week_chart.set_data(["Mon","Tue","Wed","Thu","Fri","Sat","Sun"], [0]*7)

        self.stat_most_hour.set_value("-")
        self.stat_most_weekday.set_value("-")
        self.stat_total_reviews.set_value(message)
        self.stat_avg_session.set_value("-")
        self.stat_session_count.set_value("-")