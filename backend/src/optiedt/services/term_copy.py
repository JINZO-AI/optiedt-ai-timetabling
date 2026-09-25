"""Copying a term's structure into a new term (groups, activities, availability, rules,
objective profiles). Periods are matched by position and days by weekday."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from typing import Any

from sqlalchemy import delete, insert, select
from sqlalchemy.orm import Session

from optiedt.errors import Conflict, InvalidInput
from optiedt.models import (
    Activity,
    ActivityRoom,
    AvailabilityGrid,
    ConstraintRule,
    FixedPlacement,
    ObjectiveProfile,
    Period,
    StudentGroup,
    activity_features,
    activity_groups,
    activity_instructors,
)
from optiedt.security.permissions import Permission, Principal
from optiedt.services import audit
from optiedt.services.terms import get_term


def copy_term(
    db: Session,
    principal: Principal,
    target_id: uuid.UUID,
    source_id: uuid.UUID,
    include: Sequence[str],
) -> tuple[dict[str, int], list[str]]:
    principal.require_everywhere(Permission.TERM_DATA_MANAGE)
    if source_id == target_id:
        raise InvalidInput("Choose a different term to copy from.")
    source = get_term(db, source_id)
    target = get_term(db, target_id)
    if "groups" in include and db.scalar(
        select(StudentGroup.id).where(StudentGroup.term_id == target_id).limit(1)
    ):
        raise Conflict("The target term already has student groups.", code="not_empty")

    source_periods = list(
        db.scalars(select(Period).where(Period.term_id == source_id).order_by(Period.position))
    )
    target_periods = list(
        db.scalars(select(Period).where(Period.term_id == target_id).order_by(Period.position))
    )
    period_map = {s.id: t.id for s, t in zip(source_periods, target_periods, strict=False)}
    weekdays = set(target.weekdays)
    copied: dict[str, int] = {}
    skipped: list[str] = []

    def map_cells(cells: list[dict[str, Any]]) -> list[dict[str, Any]]:
        result = []
        for cell in cells:
            period = period_map.get(uuid.UUID(cell["period_id"]))
            if period is None or cell["weekday"] not in weekdays:
                continue
            result.append({**cell, "period_id": str(period)})
        return result

    group_map: dict[uuid.UUID, uuid.UUID] = {}
    if "groups" in include:
        groups = list(db.scalars(select(StudentGroup).where(StudentGroup.term_id == source_id)))
        by_id = {g.id: g for g in groups}

        def depth(group: StudentGroup) -> int:
            level, current = 0, group
            while current.parent_id is not None:
                level += 1
                current = by_id[current.parent_id]
            return level

        for group in sorted(groups, key=depth):
            clone = StudentGroup(
                term_id=target_id,
                code=group.code,
                name=group.name,
                parent_id=group_map.get(group.parent_id) if group.parent_id else None,
                partition_key=group.partition_key,
                size=group.size,
                programme_id=group.programme_id,
                notes=group.notes,
            )
            db.add(clone)
            db.flush()
            group_map[group.id] = clone.id
        copied["groups"] = len(group_map)

    activity_map: dict[uuid.UUID, uuid.UUID] = {}
    if "activities" in include:
        for activity in db.scalars(select(Activity).where(Activity.term_id == source_id)):
            activity_clone = Activity(
                term_id=target_id,
                course_id=activity.course_id,
                activity_type_id=activity.activity_type_id,
                label=activity.label,
                duration=min(activity.duration, len(target_periods)),
                sessions_per_week=activity.sessions_per_week,
                different_days=activity.different_days,
                delivery_mode=activity.delivery_mode,
                room_type_id=activity.room_type_id,
                min_capacity=activity.min_capacity,
                campus_id=activity.campus_id,
                building_id=activity.building_id,
                notes=activity.notes,
            )
            db.add(activity_clone)
            db.flush()
            activity_map[activity.id] = activity_clone.id
        if activity_map:
            old_ids = list(activity_map)
            group_rows = db.execute(
                select(activity_groups.c.activity_id, activity_groups.c.group_id).where(
                    activity_groups.c.activity_id.in_(old_ids)
                )
            ).all()
            if group_rows:
                db.execute(
                    insert(activity_groups),
                    [
                        {
                            "term_id": target_id,
                            "activity_id": activity_map[a],
                            "group_id": group_map[g],
                        }
                        for a, g in group_rows
                    ],
                )
            for table, column in (
                (activity_instructors, "instructor_id"),
                (activity_features, "feature_id"),
            ):
                rows = db.execute(
                    select(table.c.activity_id, table.c[column]).where(
                        table.c.activity_id.in_(old_ids)
                    )
                ).all()
                if rows:
                    db.execute(
                        insert(table),
                        [{"activity_id": activity_map[a], column: v} for a, v in rows],
                    )
            for link in db.scalars(
                select(ActivityRoom).where(ActivityRoom.activity_id.in_(old_ids))
            ):
                db.add(
                    ActivityRoom(
                        activity_id=activity_map[link.activity_id],
                        room_id=link.room_id,
                        kind=link.kind,
                    )
                )
            for fixed in db.scalars(
                select(FixedPlacement).where(FixedPlacement.activity_id.in_(old_ids))
            ):
                period = period_map.get(fixed.period_id)
                if period is None or fixed.weekday not in weekdays:
                    skipped.append(
                        f"A fixed placement (occurrence {fixed.occurrence}) has no matching slot "
                        "in the new term."
                    )
                    continue
                db.add(
                    FixedPlacement(
                        activity_id=activity_map[fixed.activity_id],
                        occurrence=fixed.occurrence,
                        weekday=fixed.weekday,
                        period_id=period,
                        room_id=fixed.room_id,
                    )
                )
        copied["activities"] = len(activity_map)

    if "availability" in include:
        count = 0
        for grid in db.scalars(
            select(AvailabilityGrid).where(AvailabilityGrid.term_id == source_id)
        ):
            group_id = group_map.get(grid.group_id) if grid.group_id else None
            activity_id = activity_map.get(grid.activity_id) if grid.activity_id else None
            if (grid.group_id and group_id is None) or (grid.activity_id and activity_id is None):
                continue
            db.add(
                AvailabilityGrid(
                    term_id=target_id,
                    instructor_id=grid.instructor_id,
                    room_id=grid.room_id,
                    group_id=group_id,
                    activity_id=activity_id,
                    cells=map_cells(grid.cells),
                    source="staff",
                    updated_by_id=principal.user_id,
                )
            )
            count += 1
        copied["availability"] = count

    if "rules" in include:
        count = 0
        for rule in db.scalars(select(ConstraintRule).where(ConstraintRule.term_id == source_id)):
            mapped = _map_rule(rule, group_map, activity_map, period_map, weekdays)
            if mapped is None:
                skipped.append(f"Rule '{rule.name}' refers to records that were not copied.")
                continue
            params, scope = mapped
            db.add(
                ConstraintRule(
                    term_id=target_id,
                    rule_type=rule.rule_type,
                    name=rule.name,
                    enforcement=rule.enforcement,
                    tier=rule.tier,
                    weight=rule.weight,
                    params=params,
                    scope=scope,
                    is_enabled=rule.is_enabled,
                    notes=rule.notes,
                )
            )
            count += 1
        copied["rules"] = count

    if "profiles" in include:
        db.execute(delete(ObjectiveProfile).where(ObjectiveProfile.term_id == target_id))
        profiles = list(
            db.scalars(select(ObjectiveProfile).where(ObjectiveProfile.term_id == source_id))
        )
        for profile in profiles:
            db.add(
                ObjectiveProfile(
                    term_id=target_id,
                    code=profile.code,
                    name=profile.name,
                    description=profile.description,
                    objectives=profile.objectives,
                    position=profile.position,
                )
            )
        copied["profiles"] = len(profiles)

    db.flush()
    audit.record(
        db,
        principal,
        action="term.copy",
        entity_type="term",
        entity_id=target_id,
        term_id=target_id,
        summary=f"Copied {', '.join(include)} from {source.code} into {target.code}",
        changes={"copied": [None, copied]},
    )
    return copied, skipped


def _map_rule(
    rule: ConstraintRule,
    group_map: dict[uuid.UUID, uuid.UUID],
    activity_map: dict[uuid.UUID, uuid.UUID],
    period_map: dict[uuid.UUID, uuid.UUID],
    weekdays: set[int],
) -> tuple[dict[str, Any], dict[str, Any]] | None:
    def mapped(ids: list[str], table: dict[uuid.UUID, uuid.UUID]) -> list[str] | None:
        result = []
        for value in ids:
            new = table.get(uuid.UUID(value))
            if new is None:
                return None
            result.append(str(new))
        return result

    scope = dict(rule.scope)
    params = dict(rule.params)
    for key, table in (("group_ids", group_map), ("activity_ids", activity_map)):
        if scope.get(key):
            new = mapped(scope[key], table)
            if new is None:
                return None
            scope[key] = new
    for key in ("first_activity_id", "second_activity_id"):
        if scope.get(key):
            new = mapped([scope[key]], activity_map)
            if new is None:
                return None
            scope[key] = new[0]
    if params.get("period_ids"):
        new = mapped(params["period_ids"], period_map)
        if new is None:
            return None
        params["period_ids"] = new
    if params.get("period_id"):
        new = mapped([params["period_id"]], period_map)
        if new is None:
            return None
        params["period_id"] = new[0]
    if params.get("slots"):
        slots = []
        for slot in params["slots"]:
            new = mapped([slot["period_id"]], period_map)
            if new is None or slot["weekday"] not in weekdays:
                continue
            slots.append({"weekday": slot["weekday"], "period_id": new[0]})
        if not slots:
            return None
        params["slots"] = slots
    return params, scope
