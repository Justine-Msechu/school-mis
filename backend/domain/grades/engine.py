"""
GradingEngine — pure domain logic, no DB access.

Converts raw marks to grade letters/GPA using a configurable scale.
Also computes class rankings with proper tie handling.
"""

from __future__ import annotations
from dataclasses import dataclass
from backend.core.exceptions import BusinessRuleError, ValidationError


@dataclass(frozen=True)
class GradeBand:
    label: str      # 'A', 'B', 'C', 'D', 'F'
    min_pct: float
    max_pct: float
    gpa_points: float
    remarks: str = ""


@dataclass
class GradeResult:
    percentage: float
    grade_label: str
    gpa_points: float
    remarks: str


@dataclass
class StudentScore:
    student_id: int
    marks: float
    total: float


@dataclass
class RankedScore:
    student_id: int
    marks: float
    total: float
    percentage: float
    grade_label: str
    gpa_points: float
    rank: int


# Default scale (used when no custom scale is configured in DB)
DEFAULT_SCALE = [
    GradeBand("A", 75.0, 100.0, 4.0, "Excellent"),
    GradeBand("B", 60.0,  74.9, 3.0, "Good"),
    GradeBand("C", 50.0,  59.9, 2.0, "Average"),
    GradeBand("D", 40.0,  49.9, 1.0, "Below Average"),
    GradeBand("F",  0.0,  39.9, 0.0, "Fail"),
]


class GradingEngine:
    def __init__(self, scale: list[GradeBand] | None = None):
        self.scale = sorted(scale or DEFAULT_SCALE, key=lambda b: b.min_pct, reverse=True)

    def grade(self, marks: float, total: float) -> GradeResult:
        if total <= 0:
            raise ValidationError("Total marks must be greater than zero", field="max_score")
        if marks < 0:
            raise ValidationError("Marks cannot be negative", field="score")
        if marks > total:
            raise BusinessRuleError(f"Marks ({marks}) cannot exceed total ({total})")

        pct = round((marks / total) * 100, 2)
        for band in self.scale:
            if pct >= band.min_pct:
                return GradeResult(
                    percentage=pct,
                    grade_label=band.label,
                    gpa_points=band.gpa_points,
                    remarks=band.remarks,
                )
        # Fallback — should never happen if scale includes 0.0 entry
        last = self.scale[-1]
        return GradeResult(pct, last.label, last.gpa_points, last.remarks)

    def rank(self, scores: list[StudentScore]) -> list[RankedScore]:
        """Rank students by percentage, handling ties (same % → same rank)."""
        if not scores:
            return []

        graded: list[tuple[float, StudentScore, GradeResult]] = []
        for s in scores:
            result = self.grade(s.marks, s.total)
            graded.append((result.percentage, s, result))

        # Sort descending by percentage
        graded.sort(key=lambda x: x[0], reverse=True)

        ranked: list[RankedScore] = []
        current_rank = 1
        for i, (pct, s, gr) in enumerate(graded):
            # Assign same rank if tied with previous
            if i > 0 and pct < graded[i - 1][0]:
                current_rank = i + 1
            ranked.append(RankedScore(
                student_id=s.student_id,
                marks=s.marks,
                total=s.total,
                percentage=pct,
                grade_label=gr.grade_label,
                gpa_points=gr.gpa_points,
                rank=current_rank,
            ))
        return ranked

    @classmethod
    def from_db_rows(cls, rows: list[dict]) -> "GradingEngine":
        """Build a GradingEngine from grade_scales rows fetched from the DB."""
        if not rows:
            return cls()
        bands = [
            GradeBand(
                label=r["label"],
                min_pct=r["min_pct"],
                max_pct=r["max_pct"],
                gpa_points=r.get("gpa_points") or 0.0,
                remarks=r.get("remarks") or "",
            )
            for r in rows
        ]
        return cls(bands)
