import os
import sys
import time

from PyQt5 import uic
from PyQt5.QtCore import QAbstractTableModel, Qt, QModelIndex, QThread, pyqtSignal
from PyQt5.QtGui import QBrush, QColor, QFont, QFontMetrics
from PyQt5.QtWidgets import (
    QAbstractItemView, QApplication, QCheckBox, QComboBox, QDialog, QDialogButtonBox,
    QFormLayout, QGridLayout, QHBoxLayout, QHeaderView, QLabel, QLineEdit,
    QMainWindow, QMessageBox, QPushButton, QSpinBox,
    QTableView, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

import searching
import sorting
from data import COLUMNS, HEADERS, TYPES, DataStore, convert
from scraper import ScraperThread

UI_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "App.ui")
AUTO_LAYOUT = True


class CricketModel(QAbstractTableModel):
    def __init__(self):
        super().__init__()
        self.rows = []

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.rows)

    def columnCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(HEADERS)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        col = index.column()
        if role == Qt.DisplayRole:
            v = self.rows[index.row()][col]
            return f"{v:.2f}" if TYPES[col] == "float" else str(v)
        if role == Qt.TextAlignmentRole and TYPES[col] != "str":
            return int(Qt.AlignRight | Qt.AlignVCenter)
        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole:
            return HEADERS[section] if orientation == Qt.Horizontal else str(section + 1)
        return None

    def set_rows(self, rows):
        self.beginResetModel()
        self.rows = rows
        self.endResetModel()

    def add_rows(self, new):
        n = len(self.rows)
        self.beginInsertRows(QModelIndex(), n, n + len(new) - 1)
        self.rows.extend(new)
        self.endInsertRows()


class FuncThread(QThread):
    done = pyqtSignal(object)
    failed = pyqtSignal(str)

    def __init__(self, fn):
        super().__init__()
        self.fn = fn

    def run(self):
        try:
            self.done.emit(self.fn())
        except Exception as e:
            self.failed.emit(str(e))


class RowDialog(QDialog):

    def __init__(self, parent, row=None):
        super().__init__(parent)
        self.setWindowTitle("Edit match" if row else "Add match")
        self.setMinimumWidth(480)
        form = QFormLayout()
        self.edits = []
        for i, (name, _t) in enumerate(COLUMNS):
            e = QLineEdit(str(row[i]) if row else "")
            if i == 0:
                e.setReadOnly(True)
                if not row:
                    e.setText("LOCAL" + str(int(time.time())))
            self.edits.append(e)
            form.addRow(name, e)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        lay = QVBoxLayout(self)
        lay.addLayout(form)
        lay.addWidget(buttons)

    def values(self):
        out = []
        for e, (name, t) in zip(self.edits, COLUMNS):
            text = e.text().strip()
            if t != "str":
                try:
                    float(text or 0)
                except ValueError:
                    raise ValueError(f"'{name}' must be a number")
            out.append(convert(text, t))
        if not out[1] or not out[7]:
            raise ValueError("Date and Team 1 are required")
        return out

    def accept(self):
        try:
            self._values = self.values()
        except ValueError as e:
            QMessageBox.warning(self, "Invalid input", str(e))
            return
        super().accept()


class BenchmarkDialog(QDialog):
    def __init__(self, parent, results, n, column, desc):
        super().__init__(parent)
        self.setWindowTitle("Benchmark")
        self.resize(820, 420)
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel(f"Column: <b>{column}</b> ({'descending' if desc else 'ascending'})"
                             f" · {n:,} rows sampled · same data for every algorithm"))
        heads = ["Algorithm", "Complexity", "Stable", "Time (ms)", "Comparisons", "Swaps / moves"]
        table = QTableWidget(len(results), len(heads))
        table.setHorizontalHeaderLabels(heads)
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        timed = [r["ms"] for r in results if r["ms"] is not None]
        best = min(timed) if timed else None
        for i, r in enumerate(results):
            vals = [r["name"], r["complexity"], "Yes" if r["stable"] else "No",
                    "n/a" if r["ms"] is None else f"{r['ms']:.2f}",
                    "n/a" if r["comparisons"] is None else f"{r['comparisons']:,}",
                    "n/a" if r["swaps"] is None else f"{r['swaps']:,}"]
            for j, v in enumerate(vals):
                item = QTableWidgetItem(v)
                if j >= 3:
                    item.setTextAlignment(int(Qt.AlignRight | Qt.AlignVCenter))
                if best is not None and r["ms"] == best:
                    item.setBackground(QBrush(QColor(46, 125, 50, 90)))
                    f = QFont()
                    f.setBold(True)
                    item.setFont(f)
                table.setItem(i, j, item)
        table.resizeColumnsToContents()
        table.horizontalHeader().setStretchLastSection(True)
        lay.addWidget(table)
        lay.addWidget(QLabel("Green = fastest. Counting / Radix / Bucket only appear for numeric columns. "
                             "Comparisons are 0 for non-comparison sorts."))


class ConditionRow(QWidget):

    def __init__(self, on_remove):
        super().__init__()
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        self.connector = QComboBox()
        self.connector.addItems(["AND", "OR"])
        self.connector.setFixedWidth(90)
        self.not_box = QCheckBox("NOT")
        self.col = QComboBox()
        self.col.addItems(HEADERS)
        self.col.setMinimumWidth(165)
        self.op = QComboBox()
        self.op.setMinimumWidth(120)
        self.value = QLineEdit()
        self.value.setPlaceholderText("value")
        self.algo = QComboBox()
        self.algo.addItems(searching.ALGOS)
        rm = QPushButton("×")
        rm.setFixedSize(36, 32)
        rm.setToolTip("Remove this condition")
        rm.setStyleSheet("font-size: 15pt; font-weight: 700; padding: 0;")
        rm.clicked.connect(lambda: on_remove(self))
        for w in (self.connector, self.not_box, self.col, self.op):
            lay.addWidget(w)
        lay.addWidget(self.value, 1)
        lay.addWidget(self.algo)
        lay.addWidget(rm)
        for w in (self.connector, self.col, self.op, self.value, self.algo):
            w.setMinimumHeight(32)
        self.col.currentIndexChanged.connect(self.refresh_ops)
        self.refresh_ops()

    def refresh_ops(self):
        self.op.clear()
        self.op.addItems(searching.STRING_OPS if TYPES[self.col.currentIndex()] == "str"
                         else searching.NUMBER_OPS)

    def spec(self):
        return dict(connector=self.connector.currentText(), negate=self.not_box.isChecked(),
                    col=self.col.currentIndex(), op=self.op.currentText(),
                    value=self.value.text(), algo=self.algo.currentText())


class MainWindow(QMainWindow):
    def __init__(self, path=None):
        super().__init__()
        uic.loadUi(UI_FILE, self)
        self.setWindowTitle("CricketData Pro 🏏 - DSA Project 1")

        self.store = DataStore(path)
        self.filter_ids = None
        self.levels = []
        self.cond_rows = []
        self.scraper = None
        self.worker = None
        self.model = CricketModel()
        self.model.set_rows(list(self.store.rows))
        self.cond_layout = QVBoxLayout(self.cond_container)
        self.cond_layout.setContentsMargins(0, 0, 0, 0)
        self.cond_layout.setSpacing(8)

        if AUTO_LAYOUT:
            self._apply_layouts()
        self._setup_widgets()
        self._connect_signals()

        self.add_condition()
        self.refresh_algos()
        self.update_count()
        if not self.store.rows:
            self.tabs.setCurrentIndex(1)
        self._fit_to_screen()

    @property
    def view_rows(self):
        return self.model.rows

    def _apply_layouts(self):
        self.tabs.setParent(None)
        self.root.layout().setContentsMargins(16, 14, 16, 14)
        self.root.layout().setSpacing(10)
        self.root.layout().addWidget(self.tabs, 1)
        self.header.setFixedHeight(104)
        hl = QHBoxLayout(self.header_inner)
        hl.setContentsMargins(14, 4, 14, 4)
        left = QVBoxLayout()
        left.setSpacing(0)
        left.addStretch(1)
        left.addWidget(self.title)
        left.addWidget(self.subtitle)
        left.addStretch(1)
        hl.addLayout(left, 1)
        for s in (self.stat_Total, self.Stat_Shown):
            s.setFixedHeight(34)
            hl.addWidget(s)

        tab_lay = self.tab.layout()
        tab_lay.setSpacing(10)
        tab_lay.addWidget(self.grp_search, 1)
        tab_lay.setStretch(0, 0)

        self.levels_label_2.hide()
        g = QGridLayout(self.grp_sort)
        g.setContentsMargins(14, 22, 14, 12)
        g.setHorizontalSpacing(12)
        g.setVerticalSpacing(10)
        g.addWidget(self.label_2, 0, 0)
        g.addWidget(self.sort_col, 0, 1)
        g.addWidget(self.label_4, 0, 2)
        g.addWidget(self.sort_order, 0, 3)
        g.addWidget(self.label_6, 0, 4)
        g.addWidget(self.algo_combo, 0, 5)
        g.addWidget(self.label, 1, 0)
        g.addWidget(self.scope_combo, 1, 1)
        g.addWidget(self.btn_level, 1, 2)
        g.addWidget(self.btn_clear_levels, 1, 3)
        g.addWidget(self.levels_label, 1, 4, 1, 2)
        g.addWidget(self.btn_sort, 2, 0)
        g.addWidget(self.btn_bench, 2, 1)
        g.addWidget(self.label_3, 2, 2)
        g.addWidget(self.bench_n, 2, 3)
        g.addWidget(self.metrics, 3, 0, 1, 6)
        g.setColumnStretch(1, 2)
        g.setColumnStretch(3, 1)
        g.setColumnStretch(5, 3)

        sv = QVBoxLayout(self.grp_search)
        sv.setContentsMargins(14, 22, 14, 12)
        sv.setSpacing(8)
        sv.addWidget(self.cond_container)
        row = QHBoxLayout()
        for w in (self.btn_add_cond, self.btn_search, self.btn_clear_filter):
            row.addWidget(w)
        row.addWidget(self.search_info, 1)
        sv.addLayout(row)
        sv.addWidget(self.table, 1)
        crud = QHBoxLayout()
        for w in (self.btn_add_row, self.btn_edit_row, self.btn_delete_row):
            crud.addWidget(w)
        crud.addStretch(1)
        crud.addWidget(self.count_label)
        sv.addLayout(crud)

        lay = QVBoxLayout(self.tab_2)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(12)
        lay.addWidget(self.info_label)
        lay.addWidget(self.url_edit)
        row = QHBoxLayout()
        row.addWidget(self.lbl_target)
        row.addWidget(self.target_spin)
        for b in (self.btn_start, self.btn_pause, self.btn_resume, self.btn_stop):
            row.addWidget(b)
        row.addStretch(1)
        lay.addLayout(row)
        lay.addWidget(self.progress)
        lay.addWidget(self.log, 1)

        for b in self.findChildren(QPushButton):
            b.setMinimumHeight(32)
            b.setMinimumWidth(100)
        for w in self.findChildren((QComboBox, QLineEdit, QSpinBox)):
            w.setMinimumHeight(32)
        self.btn_bench.setMinimumWidth(190)
        self.btn_level.setMinimumWidth(150)
        self.btn_add_row.setMinimumWidth(130)
        self.btn_delete_row.setMinimumWidth(130)
        self.target_spin.setFixedWidth(110)
        self.progress.setMinimumHeight(26)

    def _fit_to_screen(self):
        screen = QApplication.primaryScreen()
        if screen is not None:
            a = screen.availableGeometry()
            self.resize(min(self.width(), a.width()), min(self.height(), a.height()))

    def _setup_widgets(self):
        self.sort_col.addItems(HEADERS)
        self.sort_order.addItems(["Ascending", "Descending"])
        self.scope_combo.addItems(["Full dataset", "Filtered results only"])
        self.algo_combo.setMinimumWidth(330)
        self.bench_n.setToolTip("How many rows to use for the benchmark. The O(n²) sorts are slow "
                                "on large inputs, so 3000 keeps it quick. Raise it for full-size runs.")
        self.levels_label.setText("Sort levels: (none - single column sort)")
        self.metrics.setWordWrap(True)

        self.table.setModel(self.model)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.setWordWrap(False)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(30)
        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(QHeaderView.Interactive)
        hh.setStretchLastSection(True)
        hh.setMinimumSectionSize(70)
        widths = [100, 125, 100, 80, 230, 260, 130, 170, 170, 170, 110, 170, 80, 110, 190, 90, 70]
        bold = QFont(hh.font())
        bold.setBold(True)
        fm = QFontMetrics(bold)
        for i, w in enumerate(widths):
            need = fm.horizontalAdvance(HEADERS[i]) + 44
            self.table.setColumnWidth(i, max(w, need))
        self.tabs.tabBar().setStyleSheet("QTabBar::tab { min-width: 120px; }")
        self.tabs.tabBar().setElideMode(Qt.ElideNone)

        self.info_label.setText(
            "Downloads real cricket matches from Cricsheet.org (Open Data Commons Attribution "
            "License), 17 attributes per match. Leave the URL empty to fetch every yearly archive "
            "(2001-2026, about 23,000 matches), or paste one Cricsheet zip link (bonus), e.g.  "
            "https://cricsheet.org/downloads/2024_json.zip")
        self.info_label.setWordWrap(True)
        self.url_edit.setPlaceholderText("Optional: Cricsheet zip URL to scrape")
        self.target_spin.setValue(15_000)
        self.progress.setFormat("%v / %m matches")
        self.progress.setMaximum(self.target_spin.value())
        self.progress.setValue(min(len(self.store.rows), self.target_spin.value()))
        self.log.setMaximumBlockCount(500)
        self.set_scrape_state("idle")

        for b in self.findChildren(QPushButton):
            b.setCursor(Qt.PointingHandCursor)

    def _connect_signals(self):
        self.sort_col.currentIndexChanged.connect(self.refresh_algos)
        self.btn_sort.clicked.connect(self.do_sort)
        self.btn_bench.clicked.connect(self.do_benchmark)
        self.btn_level.clicked.connect(self.add_level)
        self.btn_clear_levels.clicked.connect(self.clear_levels)
        self.btn_add_cond.clicked.connect(self.add_condition)
        self.btn_search.clicked.connect(self.do_search)
        self.btn_clear_filter.clicked.connect(self.clear_filter)
        self.table.doubleClicked.connect(self.edit_row)
        self.btn_add_row.clicked.connect(self.add_row)
        self.btn_edit_row.clicked.connect(self.edit_row)
        self.btn_delete_row.clicked.connect(self.delete_rows)
        self.btn_start.clicked.connect(self.start_scrape)
        self.btn_pause.clicked.connect(self.pause_scrape)
        self.btn_resume.clicked.connect(self.resume_scrape)
        self.btn_stop.clicked.connect(self.stop_scrape)

    def refresh_algos(self):
        specs = self.levels if self.levels else [(self.sort_col.currentIndex(), False)]
        current = self.algo_combo.currentData()
        self.algo_combo.blockSignals(True)
        self.algo_combo.clear()
        for name in sorting.ALGORITHMS:
            if sorting.applicable(name, specs):
                self.algo_combo.addItem(sorting.label(name), name)
        i = self.algo_combo.findData(current)
        if i >= 0:
            self.algo_combo.setCurrentIndex(i)
        else:
            i = self.algo_combo.findData("Merge Sort")
            self.algo_combo.setCurrentIndex(max(i, 0))
        self.algo_combo.blockSignals(False)

    def add_level(self):
        col = self.sort_col.currentIndex()
        desc = self.sort_order.currentIndex() == 1
        self.levels = [lv for lv in self.levels if lv[0] != col] + [(col, desc)]
        self.update_levels_label()

    def clear_levels(self):
        self.levels = []
        self.update_levels_label()

    def update_levels_label(self):
        if self.levels:
            txt = "  →  ".join(f"{HEADERS[c]} {'↓' if d else '↑'}" for c, d in self.levels)
            self.levels_label.setText("Sort levels: " + txt)
        else:
            self.levels_label.setText("Sort levels: (none - single column sort)")
        self.refresh_algos()

    def run_in_thread(self, fn, on_done, busy_text):
        self.tabs.setEnabled(False)
        self.metrics.setText(busy_text)
        QApplication.setOverrideCursor(Qt.WaitCursor)
        self.worker = FuncThread(fn)

        def finish():
            QApplication.restoreOverrideCursor()
            self.tabs.setEnabled(True)

        def ok(result):
            finish()
            on_done(result)

        def fail(msg):
            finish()
            self.metrics.setText("")
            QMessageBox.warning(self, "Error", msg)

        self.worker.done.connect(ok)
        self.worker.failed.connect(fail)
        self.worker.start()

    def do_sort(self):
        col = self.sort_col.currentIndex()
        desc = self.sort_order.currentIndex() == 1
        specs = list(self.levels) if self.levels else [(col, desc)]
        algo = self.algo_combo.currentData()
        full = self.scope_combo.currentIndex() == 0
        rows = self.store.rows if full else self.view_rows
        if not rows:
            return
        if algo in sorting.SLOW_ALGOS and len(rows) > 8000:
            ans = QMessageBox.question(
                self, "This may be slow",
                f"{algo} is quadratic in the worst case and you are sorting {len(rows):,} rows.\n"
                "It can take a minute or more. Continue?")
            if ans != QMessageBox.Yes:
                return
        names = ", ".join(f"{HEADERS[c]} {'↓' if d else '↑'}" for c, d in specs)

        def done(res):
            if full:
                self.store.rows = res["rows"]
                self.apply_filter_to_view()
            else:
                self.model.set_rows(res["rows"])
            info = sorting.ALGORITHMS[algo]
            self.metrics.setText(
                f"Sorted {len(res['rows']):,} rows by {names} with {algo} "
                f"({info['complexity']}, {'stable' if info['stable'] else 'unstable'}) · "
                f"time: {res['ms']:.2f} ms · comparisons: {res['comparisons']:,} · "
                f"swaps/moves: {res['swaps']:,}")

        self.run_in_thread(lambda: sorting.run_sort(rows, specs, algo), done,
                           f"Sorting {len(rows):,} rows with {algo} ...")

    def do_benchmark(self):
        col = self.sort_col.currentIndex()
        desc = self.sort_order.currentIndex() == 1
        full = self.scope_combo.currentIndex() == 0
        rows = self.store.rows if full else self.view_rows
        if not rows:
            return
        n = self.bench_n.value()

        def done(out):
            results, used = out
            self.metrics.setText(f"Benchmark finished on {used:,} rows.")
            BenchmarkDialog(self, results, used, HEADERS[col], desc).exec_()

        self.run_in_thread(lambda: sorting.benchmark(rows, col, desc, n), done,
                           "Running all algorithms ...")

    def add_condition(self):
        row = ConditionRow(self.remove_condition)
        self.cond_rows.append(row)
        self.cond_layout.addWidget(row)
        self.update_connectors()

    def remove_condition(self, row):
        if len(self.cond_rows) == 1:
            row.value.clear()
            return
        self.cond_rows.remove(row)
        self.cond_layout.removeWidget(row)
        row.deleteLater()
        self.update_connectors()

    def update_connectors(self):
        for i, r in enumerate(self.cond_rows):
            r.connector.setVisible(i > 0)

    def do_search(self):
        specs = [r.spec() for r in self.cond_rows]
        if any(not s["value"].strip() for s in specs):
            QMessageBox.information(self, "Search", "Fill in a value for every condition (or remove it).")
            return
        rows = self.store.rows
        all_ids = {id(r) for r in rows}
        result, total_cmp, used_algos = None, 0, []
        t0 = time.perf_counter()
        try:
            for s in specs:
                ids, c, used = searching.search_condition(rows, s)
                total_cmp += c
                used_algos.append(used)
                if s["negate"]:
                    ids = all_ids - ids
                if result is None:
                    result = ids
                elif s["connector"] == "AND":
                    result = result & ids
                else:
                    result = result | ids
        except ValueError:
            QMessageBox.warning(self, "Search", "A numeric column needs a numeric value.")
            return
        ms = (time.perf_counter() - t0) * 1000
        self.filter_ids = result
        self.apply_filter_to_view()
        self.search_info.setText(
            f"{len(result):,} of {len(rows):,} rows match · {ms:.2f} ms · comparisons: {total_cmp:,} · "
            f"algorithms: {', '.join(used_algos)}")

    def clear_filter(self):
        self.filter_ids = None
        self.apply_filter_to_view()
        self.search_info.setText("")

    def apply_filter_to_view(self):
        if self.filter_ids is None:
            self.model.set_rows(list(self.store.rows))
        else:
            ids = self.filter_ids
            self.model.set_rows([r for r in self.store.rows if id(r) in ids])
        self.update_count()

    def update_count(self):
        self.count_label.setText(f"Showing {len(self.view_rows):,} of {len(self.store.rows):,} matches")
        self.stat_Total.setText(f"{len(self.store.rows):,} matches")
        self.Stat_Shown.setText(f"{len(self.view_rows):,} shown")
        for lab in (self.stat_Total, self.Stat_Shown):
            f = QFont(lab.font())
            f.setBold(True)
            f.setPointSizeF(max(f.pointSizeF(), 11.0))
            lab.setMinimumWidth(QFontMetrics(f).horizontalAdvance("00,000 matches") + 44)

    def selected_rows(self):
        idx = sorted({i.row() for i in self.table.selectionModel().selectedRows()})
        return [self.view_rows[i] for i in idx]

    def add_row(self):
        dlg = RowDialog(self)
        if dlg.exec_() == QDialog.Accepted:
            row = dlg._values
            self.store.rows.append(row)
            if self.filter_ids is not None:
                self.filter_ids.add(id(row))
            self.model.add_rows([row])
            self.store.save()
            self.update_count()
            self.table.scrollToBottom()

    def edit_row(self, *_):
        sel = self.selected_rows()
        if not sel:
            QMessageBox.information(self, "Edit", "Select a row first.")
            return
        row = sel[0]
        dlg = RowDialog(self, row)
        if dlg.exec_() == QDialog.Accepted:
            row[:] = dlg._values
            self.model.layoutChanged.emit()
            self.store.save()

    def delete_rows(self):
        sel = self.selected_rows()
        if not sel:
            QMessageBox.information(self, "Delete", "Select one or more rows first.")
            return
        if QMessageBox.question(self, "Delete", f"Delete {len(sel)} selected match(es)?") != QMessageBox.Yes:
            return
        gone = {id(r) for r in sel}
        self.store.rows = [r for r in self.store.rows if id(r) not in gone]
        if self.filter_ids is not None:
            self.filter_ids -= gone
        self.model.set_rows([r for r in self.view_rows if id(r) not in gone])
        self.store.save()
        self.update_count()

    def set_scrape_state(self, state):
        self.btn_start.setEnabled(state == "idle")
        self.btn_pause.setEnabled(state == "running")
        self.btn_resume.setEnabled(state == "paused")
        self.btn_stop.setEnabled(state in ("running", "paused"))
        self.target_spin.setEnabled(state == "idle")
        self.url_edit.setEnabled(state == "idle")

    def start_scrape(self):
        target = self.target_spin.value()
        have = len(self.store.rows)
        if have >= target:
            QMessageBox.information(self, "Scraper", f"You already have {have:,} matches. Raise the target to scrape more.")
            return
        self.progress.setMaximum(target)
        self.progress.setValue(have)
        self.scraper = ScraperThread(self.store.keys(), target - have, self.url_edit.text())
        self.scraper.batch.connect(self.on_batch)
        self.scraper.status.connect(self.log.appendPlainText)
        self.scraper.done.connect(self.on_scrape_done)
        self.log.appendPlainText("Started scraping ...")
        self.set_scrape_state("running")
        self.scraper.start()

    def pause_scrape(self):
        self.scraper.pause()
        self.log.appendPlainText("Paused.")
        self.set_scrape_state("paused")

    def resume_scrape(self):
        self.scraper.resume()
        self.log.appendPlainText("Resumed.")
        self.set_scrape_state("running")

    def stop_scrape(self):
        self.scraper.stop()
        self.log.appendPlainText("Stopping ...")

    def on_batch(self, rows):
        self.store.append(rows)
        if self.filter_ids is None:
            self.model.add_rows(rows)
        self.progress.setValue(min(len(self.store.rows), self.progress.maximum()))
        self.update_count()

    def on_scrape_done(self, msg):
        self.log.appendPlainText(msg)
        self.set_scrape_state("idle")

    def closeEvent(self, event):
        if self.scraper is not None and self.scraper.isRunning():
            self.scraper.stop()
            self.scraper.wait(5000)
        event.accept()


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    if not os.path.exists(UI_FILE):
        QMessageBox.critical(None, "App.ui not found",
                             f"Put App.ui in the same folder as app.py:\n{os.path.dirname(UI_FILE)}")
        sys.exit(1)
    win = MainWindow()
    win.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()