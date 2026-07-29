"""Enumerations of the domain.

French LMD terms keep their French codes. They are precise terms of art with no
clean English equivalent, and the catalogue, the instance CSVs and the
specification all use them. See docs/domain-model.md, "Canonical names".
"""

from __future__ import annotations

from enum import StrEnum


class SessionType(StrEnum):
    """The three kinds of teaching session in the LMD organisation.

    The hierarchy matters: a CM occupies the whole promotion, so no TD or TP of
    any of its groups or subgroups may share the slot. That relation is H12.
    """

    CM = "CM"  # cours magistral — lecture, whole promotion, lecture theatre
    TD = "TD"  # travaux dirigés — tutorial, one group, ordinary classroom
    TP = "TP"  # travaux pratiques — laboratory session, one subgroup, equipped room


class GroupLevel(StrEnum):
    """Position in the promotion → tutorial group → laboratory subgroup chain.

    Exactly one chain is admitted; see Group.parent_group.

    Values are the literals in ``groups.csv`` column ``group_type``.
    """

    PROMO = "PROMO"  # promotion — 6 in the reference instance
    TD = "TD"  # tutorial group — 15
    TP = "TP"  # laboratory subgroup — 30


class RoomType(StrEnum):
    """Values are the literals in ``rooms.csv`` column ``room_type``.

    Kept in French, matching the instance files and the constraint catalogue.
    Renaming them in code alone would create a translation layer between the
    application and its own data, for no benefit. See docs/domain-model.md.
    """

    AMPHI = "Amphi"  # lecture theatre — 2 rooms, 150 and 250 places
    SALLE = "Salle"  # ordinary classroom — 10
    LAB_INFO = "Lab_Info"  # computer laboratory — 6. ⚠️ 95% occupied
    LAB_SCIENCES = "Lab_Sciences"  # science laboratory — 2


class AvailabilityState(StrEnum):
    """⚠️ The instance schema does NOT carry this distinction.

    ``teacher_availability.csv`` has a boolean ``is_available``, and all 157
    rows are 0 — they are unavailability declarations, as documented.

    There is therefore **no way to express a preferred window in the current
    schema**, while S5 "Teacher preference" carries weight 0.20 — the second
    highest of the seven criteria. SRS §4.1 nonetheless specifies a grid whose
    slots are marked available, unavailable *or preferred*.

    Resolve C-12 before implementing S5 or the availability grid.
    """

    AVAILABLE = "AVAILABLE"
    UNAVAILABLE = "UNAVAILABLE"
    PREFERRED = "PREFERRED"  # feeds S5 — has no representation in the CSV yet


class DeclarationSource(StrEnum):
    """Origin of an availability row.

    SYNTHETIC marks a row produced by the generator. The distinction is a
    requirement, not a convenience: generated declarations exist only so the
    instance is solvable before any teacher has connected, and a generated
    declaration must never be mistaken for a real one.
    """

    TEACHER = "TEACHER"
    SYNTHETIC = "SYNTHETIC"


class TeacherRank(StrEnum):
    """Rank determines the maximum weekly load (9, 12, 18 or 24 hours).

    Values are the literals in ``teachers.csv`` column ``rank``. Note the
    unaccented spellings — the instance files carry them without diacritics.
    """

    PROFESSEUR = "Professeur"  # 7 in the reference instance
    MAITRE_DE_CONFERENCES = "Maitre de Conferences"  # 11
    MAITRE_ASSISTANT = "Maitre Assistant"  # 13
    ASSISTANT = "Assistant"  # 13


class ConstraintKind(StrEnum):
    HARD = "HARD"  # H1..H12: must hold in every accepted timetable
    SOFT = "SOFT"  # S2..S10: violation adds a penalty to the cost


class RunState(StrEnum):
    """Lifecycle of one generation run.

    PENDING → PREANALYSIS → SOLVING → SCORING → COMPLETED
                                    └→ INFEASIBLE → DIAGNOSING → DIAGNOSED
                                    └→ FAILED

    The diagnosis branch is entered ONLY when the optimisation run concludes
    that no timetable exists. See docs/architecture.md.
    """

    PENDING = "PENDING"
    PREANALYSIS = "PREANALYSIS"
    SOLVING = "SOLVING"
    SCORING = "SCORING"
    COMPLETED = "COMPLETED"
    INFEASIBLE = "INFEASIBLE"
    DIAGNOSING = "DIAGNOSING"
    DIAGNOSED = "DIAGNOSED"
    FAILED = "FAILED"


class RecommendationStatus(StrEnum):
    PROPOSED = "PROPOSED"
    ACCEPTED = "ACCEPTED"  # a new run was created
    REJECTED = "REJECTED"  # no run created, candidate unchanged


class UserRole(StrEnum):
    """Rights per SRS Table 2, which is authoritative.

    The flow descriptions in CdC §4.3 and SRS §3.3 say the ADMINISTRATOR loads
    department data; Table 2 gives that right to the PERSON_IN_CHARGE and limits
    the administrator to accounts and calendar. Table 2 wins — see C-8.
    """

    PERSON_IN_CHARGE = "PERSON_IN_CHARGE"  # all data, runs, comparison, publication
    TEACHER = "TEACHER"  # own availability, own timetable
    STUDENT = "STUDENT"  # timetable of own group
    ADMINISTRATOR = "ADMINISTRATOR"  # accounts, holidays, calendar
