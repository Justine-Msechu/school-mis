"""Results tab — view and print result reports for a class/exam."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QComboBox, QMessageBox, QAbstractItemView, QDialog,
    QTextEdit, QDialogButtonBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
try:
    from PyQt6.QtPrintSupport import QPrinter, QPrintPreviewDialog
    from PyQt6.QtGui import QTextDocument
    _PRINT_OK = True
except ImportError:
    _PRINT_OK = False

from database.db import fetch_all
from services.grades_service import grades_service
from services.base import ServiceError, PolicyViolation

BTN_PRIMARY = """QPushButton{background:#7C3AED;color:white;border:none;border-radius:7px;
    padding:8px 18px;font-size:13px;font-weight:600;}QPushButton:hover{background:#6D28D9;}
    QPushButton:disabled{background:#CBD5E1;color:#94A3B8;}"""
BTN_OUTLINE = """QPushButton{background:white;color:#374151;border:1px solid #D1D5DB;
    border-radius:7px;padding:8px 18px;font-size:13px;}QPushButton:hover{background:#F9FAFB;}"""
COMBO = """QComboBox{border:1px solid #D1D5DB;border-radius:6px;padding:6px 10px;
    font-size:13px;background:white;min-width:180px;}"""

GRADE_COLOURS = {"A": "#059669", "B": "#0891B2", "C": "#D97706", "D": "#EA580C", "F": "#DC2626"}


class ResultsTab(QWidget):
    def __init__(self):
        super().__init__()
        self._report = None
        self._build()
        self._load_selectors()

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 16, 0, 0)
        lay.setSpacing(12)

        sel = QHBoxLayout(); sel.setSpacing(10)
        self.exam_cb  = QComboBox(); self.exam_cb.setStyleSheet(COMBO)
        self.class_cb = QComboBox(); self.class_cb.setStyleSheet(COMBO)

        view_btn = QPushButton("View Results"); view_btn.setStyleSheet(BTN_OUTLINE)
        view_btn.clicked.connect(self._load_report)
        self.print_btn = QPushButton("Export / Print PDF")
        self.print_btn.setStyleSheet(BTN_PRIMARY)
        self.print_btn.setEnabled(False)
        self.print_btn.clicked.connect(self._print_report)

        for lbl, wgt in [("Exam:", self.exam_cb), ("Class:", self.class_cb)]:
            l = QLabel(lbl); l.setStyleSheet("font-size:13px;color:#374151;font-weight:600;")
            sel.addWidget(l); sel.addWidget(wgt)
        sel.addWidget(view_btn); sel.addStretch(); sel.addWidget(self.print_btn)
        lay.addLayout(sel)

        self.summary_bar = QLabel("")
        self.summary_bar.setVisible(False)
        self.summary_bar.setStyleSheet(
            "background:#F5F3FF;color:#5B21B6;border-radius:6px;padding:8px 12px;font-size:12px;"
        )
        lay.addWidget(self.summary_bar)

        self.table = QTableWidget()
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.setStyleSheet("""
            QTableWidget{border:1px solid #E5E7EB;border-radius:8px;
                gridline-color:#F3F4F6;font-size:12px;}
            QHeaderView::section{background:#F5F3FF;font-weight:600;
                padding:7px;border:none;border-bottom:1px solid #DDD6FE;color:#5B21B6;}
            QTableWidget::item{padding:5px 7px;}
        """)
        lay.addWidget(self.table)

    def _load_selectors(self):
        try:
            exams = grades_service.get_exams()
        except (ServiceError, PolicyViolation):
            exams = []
        self.exam_cb.clear()
        self.exam_cb.addItem("-- Select exam --", None)
        for e in exams:
            self.exam_cb.addItem(f"{e['name']} (T{e['term']}) — {e['year_label'] or ''}", e["id"])

        classes = fetch_all("SELECT id, name FROM classes WHERE is_active=1 ORDER BY name")
        self.class_cb.clear()
        self.class_cb.addItem("-- Select class --", None)
        for c in classes:
            self.class_cb.addItem(c["name"], c["id"])

    def _load_report(self):
        exam_id  = self.exam_cb.currentData()
        class_id = self.class_cb.currentData()
        if not exam_id or not class_id:
            QMessageBox.warning(self, "Required", "Select an exam and a class."); return

        try:
            report = grades_service.get_result_report(exam_id, class_id)
        except (ServiceError, PolicyViolation) as e:
            QMessageBox.warning(self, "Error", str(e)); return

        self._report = report
        self._fill_table(report)
        self.print_btn.setEnabled(True)

    def _fill_table(self, report: dict):
        subjects  = report["subjects"]
        rows      = report["rows"]

        # Columns: Rank | Student | Adm | [subject x N] | Total | Avg | Grade
        fixed = ["Rank", "Student", "Adm No"]
        subj_names = [s["name"] for s in subjects]
        all_cols = fixed + subj_names + ["Total", "Avg %", "Grade"]

        self.table.setColumnCount(len(all_cols))
        self.table.setHorizontalHeaderLabels(all_cols)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.setRowCount(len(rows))

        for r, row in enumerate(rows):
            def cell(v, align=Qt.AlignmentFlag.AlignLeft, fg=None):
                it = QTableWidgetItem(str(v))
                it.setFlags(Qt.ItemFlag.ItemIsEnabled)
                it.setTextAlignment(align | Qt.AlignmentFlag.AlignVCenter)
                if fg:
                    it.setForeground(QColor(fg))
                return it

            center = Qt.AlignmentFlag.AlignCenter

            self.table.setItem(r, 0, cell(row["rank"], center))
            self.table.setItem(r, 1, cell(row["student_name"]))
            self.table.setItem(r, 2, cell(row["admission_no"], center))

            for ci, subj in enumerate(subjects):
                sg = row["grades"].get(subj["id"])
                if sg and sg.get("score") is not None:
                    score = sg["score"]
                    letter = sg.get("grade_letter") or "—"
                    val = f"{score:.0f} ({letter})"
                    colour = GRADE_COLOURS.get(letter)
                else:
                    val = "—"
                    colour = "#9CA3AF"
                self.table.setItem(r, 3 + ci, cell(val, center, colour))

            n = len(subjects)
            self.table.setItem(r, 3 + n, cell(
                f"{row['total']:.0f}/{row['max_total']:.0f}" if row["max_total"] else "—",
                center
            ))
            self.table.setItem(r, 4 + n, cell(
                f"{row['average']:.1f}%" if row["average"] is not None else "—",
                center
            ))
            grade = row["overall_grade"]
            self.table.setItem(r, 5 + n, cell(
                grade, center, GRADE_COLOURS.get(grade)
            ))

        graded_rows = [r for r in rows if r["average"] is not None]
        avg_all = (sum(r["average"] for r in graded_rows) / len(graded_rows)) if graded_rows else 0
        self.summary_bar.setText(
            f"Exam: {report['exam']['name']}  |  Class: {report['class'].get('name','—')}  |  "
            f"Students: {len(rows)}  |  Class average: {avg_all:.1f}%"
        )
        self.summary_bar.setVisible(True)

    def _print_report(self):
        if not self._report:
            return
        if not _PRINT_OK:
            QMessageBox.warning(self, "Print Unavailable",
                                "Qt print support not installed. Install PyQt6-Qt6PrintSupport.")
            return

        html = self._build_html(self._report)
        doc = QTextDocument()
        doc.setHtml(html)

        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        printer.setPageMargins(
            __import__('PyQt6.QtCore', fromlist=['QMarginsF']).QMarginsF(15, 15, 15, 15),
            __import__('PyQt6.QtGui', fromlist=['QPageLayout']).QPageLayout.Unit.Millimeter
        )
        preview = QPrintPreviewDialog(printer, self)
        preview.paintRequested.connect(doc.print)
        preview.exec()

    @staticmethod
    def _build_html(report: dict) -> str:
        exam  = report["exam"]
        cls   = report["class"]
        subjs = report["subjects"]
        rows  = report["rows"]

        subj_heads = "".join(
            f"<th style='min-width:60px'>{s['name']}<br><small style='font-weight:normal'>"
            f"{s['code'] or ''}</small></th>"
            for s in subjs
        )
        table_rows = ""
        for row in rows:
            scores = ""
            for s in subjs:
                sg = row["grades"].get(s["id"])
                if sg and sg.get("score") is not None:
                    ltr = sg.get("grade_letter") or ""
                    colour = {"A":"#059669","B":"#0891B2","C":"#D97706",
                              "D":"#EA580C","F":"#DC2626"}.get(ltr, "#374151")
                    scores += (f"<td style='text-align:center'>"
                               f"<span style='color:{colour};font-weight:600'>{ltr}</span><br>"
                               f"<small>{sg['score']:.0f}</small></td>")
                else:
                    scores += "<td style='text-align:center;color:#9CA3AF'>—</td>"
            avg = f"{row['average']:.1f}%" if row["average"] is not None else "—"
            og  = row["overall_grade"]
            og_colour = {"A":"#059669","B":"#0891B2","C":"#D97706",
                         "D":"#EA580C","F":"#DC2626"}.get(og, "#374151")
            table_rows += (
                f"<tr>"
                f"<td style='text-align:center'>{row['rank']}</td>"
                f"<td>{row['student_name']}</td>"
                f"<td style='text-align:center'>{row['admission_no']}</td>"
                f"{scores}"
                f"<td style='text-align:center'>{row['total']:.0f}/{row['max_total']:.0f}</td>"
                f"<td style='text-align:center'>{avg}</td>"
                f"<td style='text-align:center;color:{og_colour};font-weight:700'>{og}</td>"
                f"</tr>"
            )

        graded = [r for r in rows if r["average"] is not None]
        class_avg = (sum(r["average"] for r in graded) / len(graded)) if graded else 0

        return f"""
        <html><body style='font-family:Arial,sans-serif;font-size:11pt;color:#111827'>
        <div style='text-align:center;margin-bottom:18px'>
            <h2 style='margin:0;font-size:16pt'>{exam["name"]} — Result Report</h2>
            <p style='margin:4px 0;color:#374151'>Class: {cls.get("name","—")} &nbsp;|&nbsp;
            Term {exam.get("term","—")} &nbsp;|&nbsp; {exam.get("year_label","")}</p>
            <p style='margin:4px 0;color:#374151'>
            Students: {len(rows)} &nbsp;|&nbsp; Class average: {class_avg:.1f}%</p>
        </div>
        <table border='0' cellspacing='0' cellpadding='5' width='100%'
               style='border-collapse:collapse;font-size:10pt'>
            <thead style='background:#F5F3FF'>
            <tr style='border-bottom:2px solid #DDD6FE'>
                <th>Rank</th><th style='text-align:left'>Student</th><th>Adm No</th>
                {subj_heads}
                <th>Total</th><th>Avg %</th><th>Grade</th>
            </tr>
            </thead>
            <tbody>{table_rows}</tbody>
        </table>
        <p style='margin-top:30px;font-size:9pt;color:#9CA3AF'>
            Generated by School MIS — {__import__('datetime').date.today().isoformat()}
        </p>
        </body></html>
        """

    def refresh(self):
        self._load_selectors()
