"""The instance every screen renders against.

One endpoint, one payload. The timetable views need to turn a `Placement`
(session id, slot index, room id) into something readable, and the availability
grid needs the slot grid; both come from here rather than from a placement
payload, so a candidate stays exactly what the solver produced.
"""

from __future__ import annotations

from fastapi import APIRouter

from optiedt.api.deps import InstanceDep
from optiedt.api.schemas import InstanceOut

router = APIRouter(tags=["instance"])


@router.get("/instance", response_model=InstanceOut, summary="The reference instance")
def read_instance(instance: InstanceDep) -> InstanceOut:
    return InstanceOut.of(instance)
