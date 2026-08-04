"""The instance every screen renders against.

One endpoint, one payload. The timetable views need to turn a `Placement`
(session id, slot index, room id) into something readable, and the availability
grid needs the slot grid; both come from here rather than from a placement
payload, so a candidate stays exactly what the solver produced.
"""

from __future__ import annotations

from fastapi import APIRouter

from optiedt.api.deps import CurrentUserDep, InstanceDep
from optiedt.api.schemas import InstanceOut

router = APIRouter(tags=["instance"])


@router.get("/instance", response_model=InstanceOut, summary="The reference instance")
def read_instance(instance: InstanceDep, _user: CurrentUserDep) -> InstanceOut:
    """Any signed-in account may read the instance.

    ⚠️ It is not scoped per role, and that is a decision rather than an
    oversight: every screen needs the slot grid, the rooms and the group
    hierarchy to render anything at all, and none of it is personal data - the
    425 students are deliberately not loaded (`domain/instance.py`). What IS
    scoped is a teacher's availability and, in time, a published timetable.
    """
    return InstanceOut.of(instance)
