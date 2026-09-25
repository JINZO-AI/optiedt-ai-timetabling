"""Data-quality checks on a compiled problem.

These concern consistency of the data itself. Whether sessions can be placed at all is the
solver pre-check's job (``optiedt.solver.precheck``); the two reports are shown together.
"""

from __future__ import annotations

from optiedt.problem.atoms import TooManyAtomsError, build_atoms
from optiedt.problem.issues import Issue
from optiedt.problem.model import Problem


def check_data(problem: Problem) -> list[Issue]:
    issues: list[Issue] = []
    snapshot = problem.snapshot

    if not problem.activities:
        issues.append(Issue("error", "no_activities", "The term has no activities to schedule."))

    for instructor in problem.instructors:
        if not instructor.active:
            affected = [a.id for a in problem.activities if instructor.index in a.instructors]
            issues.append(
                Issue(
                    "error",
                    "inactive_instructor",
                    f"{instructor.name} is deactivated but still teaches "
                    f"{len(affected)} activit{'y' if len(affected) == 1 else 'ies'}.",
                    "instructor",
                    (instructor.id,),
                )
            )
        load = problem.instructor_load.get(instructor.index, 0)
        if instructor.max_weekly_periods is not None and load > instructor.max_weekly_periods:
            issues.append(
                Issue(
                    "warning",
                    "instructor_overload",
                    f"{instructor.name} teaches {load} periods a week, above the maximum of "
                    f"{instructor.max_weekly_periods}.",
                    "instructor",
                    (instructor.id,),
                    {"load": load, "maximum": instructor.max_weekly_periods},
                )
            )

    for activity in problem.activities:
        if not activity.instructors:
            issues.append(
                Issue(
                    "warning",
                    "no_instructor",
                    f"{activity.title} has no instructor.",
                    "activity",
                    (activity.id,),
                )
            )
        empty = [problem.groups[g] for g in activity.groups if problem.groups[g].size == 0]
        if empty:
            issues.append(
                Issue(
                    "warning",
                    "empty_group",
                    f"{activity.title} is attended by "
                    f"{', '.join(g.code for g in empty)}, which has no students.",
                    "activity",
                    (activity.id,),
                )
            )

    by_parent: dict[tuple[int, str], list[int]] = {}
    for group in problem.groups:
        if group.parent is not None:
            by_parent.setdefault((group.parent, group.partition), []).append(group.index)
    for (parent, key), members in sorted(by_parent.items()):
        total = sum(problem.groups[m].size for m in members)
        parent_group = problem.groups[parent]
        if total > parent_group.size:
            issues.append(
                Issue(
                    "warning",
                    "partition_oversized",
                    f"The '{key}' subgroups of {parent_group.code} have {total} students, more "
                    f"than the {parent_group.size} of the group itself.",
                    "group",
                    (parent_group.id,),
                )
            )

    try:
        build_atoms(problem)
    except TooManyAtomsError as error:
        issues.append(Issue("error", "too_many_atoms", str(error), "group"))

    for rule in problem.rules:
        if not (rule.instructor_ids or rule.group_ids or rule.activity_ids):
            issues.append(
                Issue(
                    "warning",
                    "rule_without_targets",
                    f"Rule '{rule.name}' applies to nothing in this term and has no effect.",
                    "constraint_rule",
                    (rule.id,),
                )
            )
        if rule.type == "campus_travel" and problem.campus_count > 1:
            missing = [
                (a, b)
                for a in range(problem.campus_count)
                for b in range(a + 1, problem.campus_count)
                if (a, b) not in problem.travel_minutes
            ]
            if missing:
                names = [
                    f"{snapshot.campuses[a].code}/{snapshot.campuses[b].code}" for a, b in missing
                ]
                issues.append(
                    Issue(
                        "warning",
                        "missing_travel_time",
                        f"Rule '{rule.name}' needs travel times, missing for: "
                        f"{', '.join(names)}. Those pairs are treated as reachable.",
                        "constraint_rule",
                        (rule.id,),
                    )
                )
    return issues
