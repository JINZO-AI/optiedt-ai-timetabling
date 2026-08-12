"""Build an `ExamSession` from an `Instance`. FR-20's inputs, derived.

**Why derivation rather than import.** SRS §3.2 Table 19 gives FR-20's input as
*"Examinations, students, rooms, period of the session and supervisors"*. Of
those five, the repository supplies students and rooms; **SRS Table 25 defines
no Examination entity, no Supervisor entity and no examination-period entity**,
and the word "supervisor" appears in the whole SRS only inside X4's own
statement. So three of the five inputs had no source. The specification is
silent, exactly as it was silent about a second dataset load (C-22) — and the
answer is the same shape: a project decision, recorded rather than assumed.
See **C-23** and **ADR-013**.

The three rules, each backed by a measurement rather than a preference:

1. **One examination per course.** Measured on the reference instance: **no
   course spans more than one promotion** (0 of 32) and a course's own
   `programme`/`level` agrees with its sessions' promotion in every case (0
   mismatches). So "one per course" and "one per (course, promotion)" name the
   same 32 examinations here, and the simpler rule is the one that cannot be
   wrong about this data. ⚠️ If a future instance shares a course between
   promotions, `derive_examination_session` refuses rather than guessing which
   promotion the examination belongs to.

2. **The supervisor is the course's CM teacher.** Measured: a course has **3 to
   13 distinct teachers** once TD and TP groups are counted, and **exactly one
   CM** (32 of 32). "The course teacher" is therefore ambiguous and "the CM
   teacher" is not. The CdC grants a teacher *"consultation of the personal
   timetable and of the examinations supervised"*, so a teacher IS a
   supervisor; which one is what the data had to settle.

3. **The period is two calendar-configuration keys**, `exam_period_start` and
   `exam_period_days` — the smallest addition that satisfies FR-20's "period of
   the session", and configuration rather than constraint, which is invariant 7.

⚠️ **A slot that X3 excludes is never built.** A day outside the period, a
Sunday under `days_per_week = 6`, or a blocking holiday produces no `ExamSlot`
at all, so "inside the period and outside the holidays" holds by construction —
the same technique H9 uses weekly. A constraint posted afterwards would be
weaker and slower.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from optiedt.domain.enums import SessionType
from optiedt.domain.examination import Examination, ExamSession, ExamSlot
from optiedt.domain.instance import Instance

_START_KEY = "exam_period_start"
_DAYS_KEY = "exam_period_days"


class ExaminationNotDerivableError(Exception):
    """The instance cannot yield an examination session, with the reason.

    Raised rather than returning a half-built session: an examination timetable
    solved against zero candidates or zero slots would be a valid-looking
    answer to a question nobody could have asked. The message names what is
    missing, because the interface shows it to the person in charge verbatim.
    """


@dataclass(frozen=True, slots=True)
class _CourseFacts:
    promotion: str
    supervisor: str


def _course_facts(instance: Instance) -> dict[str, _CourseFacts]:
    """Promotion and CM teacher per course, refusing anything ambiguous."""
    promotion_of_group = {g.id: g.promotion for g in instance.groups}

    promotions: dict[str, set[str]] = {}
    lecturers: dict[str, set[str]] = {}
    for session in instance.sessions:
        promotion = promotion_of_group.get(session.group)
        if promotion is None:
            raise ExaminationNotDerivableError(
                f"session {session.id} names group {session.group}, which does not exist"
            )
        promotions.setdefault(session.course, set()).add(promotion)
        if session.type is SessionType.CM:
            lecturers.setdefault(session.course, set()).add(session.teacher)

    facts: dict[str, _CourseFacts] = {}
    for course in instance.courses:
        reached = promotions.get(course.id, set())
        if not reached:
            # A course nobody teaches has no examination. Skipped rather than
            # refused: it is a gap in the timetable, not in the examination.
            continue
        if len(reached) > 1:
            raise ExaminationNotDerivableError(
                f"course {course.id} is taught to {len(reached)} promotions "
                f"({', '.join(sorted(reached))}); one examination per course is "
                "ambiguous for it, so the derivation rule of C-23 does not apply. "
                "Deriving one examination per (course, promotion) is a decision "
                "for the project owner, not for this function"
            )
        cm = lecturers.get(course.id, set())
        if len(cm) != 1:
            raise ExaminationNotDerivableError(
                f"course {course.id} has {len(cm)} CM teachers; the supervisor of "
                "its examination is the CM teacher (C-23) and that requires exactly one"
            )
        facts[course.id] = _CourseFacts(promotion=reached.pop(), supervisor=cm.pop())
    return facts


def _exam_slots(instance: Instance) -> tuple[ExamSlot, ...]:
    """X3, applied by building only the slots that satisfy it."""
    config = instance.calendar_config
    raw_start = config.get(_START_KEY, "").strip()
    raw_days = config.get(_DAYS_KEY, "").strip()
    if not raw_start or not raw_days:
        raise ExaminationNotDerivableError(
            f"the calendar configuration states no examination period: "
            f"{_START_KEY} and {_DAYS_KEY} are both required"
        )
    try:
        start = date.fromisoformat(raw_start)
        days = int(raw_days)
    except ValueError as exc:
        raise ExaminationNotDerivableError(
            f"the examination period is not readable ({_START_KEY}={raw_start!r}, "
            f"{_DAYS_KEY}={raw_days!r}): {exc}"
        ) from exc
    if days <= 0:
        raise ExaminationNotDerivableError(f"{_DAYS_KEY} must be positive, not {days}")

    periods_per_day = int(config.get("periods_per_day", "5"))
    days_per_week = int(config.get("days_per_week", "6"))
    blocked = {h.date for h in instance.holidays if h.blocking}

    slots: list[ExamSlot] = []
    for offset in range(days):
        day = start + timedelta(days=offset)
        if day.weekday() >= days_per_week:
            continue  # Sunday, when the week is Monday-Saturday
        if day in blocked:
            continue  # X3 — outside the holidays
        for period in range(periods_per_day):
            slots.append(
                ExamSlot(
                    index=len(slots),
                    day_index=offset,
                    period_index=period,
                    day=day,
                )
            )
    if not slots:
        raise ExaminationNotDerivableError(
            "the examination period contains no open slot once Sundays and holidays are withdrawn"
        )
    return tuple(slots)


def derive_examination_session(
    instance: Instance,
    seed: int = 42,
    deterministic_budget: float = 30.0,
) -> ExamSession:
    """FR-20's inputs, assembled from the instance. See the module docstring.

    Raises `ExaminationNotDerivableError` naming what is missing — most often
    an empty roster, which is what a dataset supplied through FR-1 always has.
    """
    if not instance.students:
        raise ExaminationNotDerivableError(
            "the instance carries no students, and an examination session needs "
            "them: X1 forbids two examinations of one student in one slot, and "
            "X2 sizes the rooms on the number of candidates. A dataset supplied "
            "through the import screen carries no roster — students.csv is not "
            "one of the eleven files that contract admits"
        )
    if not instance.rooms:
        raise ExaminationNotDerivableError("the instance carries no rooms")

    facts = _course_facts(instance)
    if not facts:
        raise ExaminationNotDerivableError(
            "no course of the instance has any session, so there is nothing to examine"
        )

    by_promotion: dict[str, list[str]] = {}
    for student in instance.students:
        by_promotion.setdefault(student.promotion, []).append(student.id)

    examinations: list[Examination] = []
    for course_id in sorted(facts):
        fact = facts[course_id]
        candidates = tuple(sorted(by_promotion.get(fact.promotion, ())))
        if not candidates:
            raise ExaminationNotDerivableError(
                f"course {course_id} is taught to promotion {fact.promotion}, "
                "which has no student in the roster"
            )
        examinations.append(
            Examination(
                id=f"X-{course_id}",
                course=course_id,
                promotion=fact.promotion,
                supervisor=fact.supervisor,
                candidates=candidates,
            )
        )

    return ExamSession(
        examinations=tuple(examinations),
        slots=_exam_slots(instance),
        seed=seed,
        deterministic_budget=deterministic_budget,
    )


__all__ = ["ExaminationNotDerivableError", "derive_examination_session"]
