"""The comparison-grounded assistant route.

FR-24's `/question` is bounded to the run's own figures by design, and
correctly declines a comparative question — see `test_fr24.py`,
`test_the_context_is_bounded_by_the_run`. But that correctness surfaced as a
usability defect: the Compare screen offers suggestions like "why is this
candidate ranked first?", which the run-scoped route can never answer because
it was never handed a decomposition. It always knows both candidates, so this
route is the fix — the SAME `Decomposition` the comparison ledger renders
(`GET /runs/{id}/comparison`), handed to the assistant instead of withheld
from it. Invariant 4 still holds: the figure comes from `decomposition_for`,
in `services/runs.py`, never recomputed by the assistant.
"""

from __future__ import annotations

import pytest

from optiedt.api import deps
from optiedt.assistant.interfaces import ContextPayload
from optiedt.assistant.service import DefaultAssistant

pytestmark = pytest.mark.acceptance


class _Scripted:
    """A fake adapter — C-21. Records the context it was shown."""

    def __init__(self, reply: str = "") -> None:
        self.reply = reply
        self.seen: list[ContextPayload] = []

    @property
    def enabled(self) -> bool:
        return True

    def complete(self, context: ContextPayload, prompt: str, timeout_seconds: float) -> str:
        del prompt, timeout_seconds
        self.seen.append(context)
        return self.reply


@pytest.fixture
def run(application):
    return application.launch()


def _with_assistant(application, adapter):
    application.client.app.dependency_overrides[deps.get_assistant] = lambda: DefaultAssistant(
        adapter=adapter
    )


def _compare(application, run, a_id: str, b_id: str):
    path = f"/api/assistant/runs/{run['id']}/candidates/{a_id}/compare/{b_id}"
    return application.client.get(path)


def test_the_decomposition_reaches_the_assistant(application, run) -> None:
    """The one thing the run-scoped route could never do: the score difference
    and every per-criterion contribution are in the context, not withheld."""
    a, b = run["candidates"][0], run["candidates"][1]
    adapter = _Scripted(reply="This candidate leads on the criteria that matter most here.")
    _with_assistant(application, adapter)

    response = _compare(application, run, a["id"], b["id"])

    assert response.status_code == 200, response.text
    figures = adapter.seen[0].figures
    assert "score.difference" in figures
    assert any(key.startswith("contribution.") for key in figures)


def test_a_grounded_comparative_answer_is_returned(application, run) -> None:
    a, b = run["candidates"][0], run["candidates"][1]
    _with_assistant(application, _Scripted(reply="A is favoured by its idle-time contribution."))

    answer = _compare(application, run, a["id"], b["id"]).json()

    assert answer["generated"] is True
    assert "favoured" in answer["text"]


def test_a_candidate_cannot_be_compared_with_itself(application, run) -> None:
    a = run["candidates"][0]

    response = _compare(application, run, a["id"], a["id"])

    assert response.status_code == 422


def test_an_unknown_candidate_is_404(application, run) -> None:
    a = run["candidates"][0]

    assert _compare(application, run, a["id"], "does-not-exist").status_code == 404
    assert _compare(application, run, "does-not-exist", a["id"]).status_code == 404


def test_with_the_service_off_the_comparison_is_still_answered_honestly(application, run) -> None:
    """Invariant 5. No dependency override — the default configuration."""
    a, b = run["candidates"][0], run["candidates"][1]

    answer = _compare(application, run, a["id"], b["id"]).json()

    assert answer["generated"] is False
    assert "sum exactly to the difference in score" in answer["text"]


def test_an_invented_contribution_is_still_stopped(application, run) -> None:
    """The grounding check applies here exactly as it does to every other
    request kind — a comparative context does not get a pass."""
    a, b = run["candidates"][0], run["candidates"][1]
    _with_assistant(application, _Scripted(reply="The gap is exactly 4271 points."))

    answer = _compare(application, run, a["id"], b["id"]).json()

    assert answer["generated"] is False
    assert "4271" not in answer["text"]
