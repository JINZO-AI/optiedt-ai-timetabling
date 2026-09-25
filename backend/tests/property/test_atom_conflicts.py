"""Conflict atoms must agree with the direct definition of two groups sharing students."""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from optiedt.problem.atoms import atoms_of_groups, build_atoms
from tests.snapshot_builder import SnapshotBuilder


def _share_students(
    parents: dict[int, int | None], partitions: dict[int, str], a: int, b: int
) -> bool:
    def chain(node: int) -> list[int]:
        result = [node]
        while parents[result[-1]] is not None:
            result.append(parents[result[-1]])  # type: ignore[arg-type]
        return result

    chain_a, chain_b = chain(a), chain(b)
    if a in chain_b or b in chain_a:
        return True
    common = next((n for n in chain_a if n in chain_b), None)
    if common is None:
        return False
    child_a = chain_a[chain_a.index(common) - 1]
    child_b = chain_b[chain_b.index(common) - 1]
    return partitions[child_a] != partitions[child_b]


@st.composite
def group_trees(draw: st.DrawFn) -> tuple[dict[int, int | None], dict[int, str]]:
    count = draw(st.integers(min_value=1, max_value=12))
    parents: dict[int, int | None] = {0: None}
    partitions: dict[int, str] = {0: "default"}
    for node in range(1, count):
        parents[node] = draw(st.one_of(st.none(), st.integers(min_value=0, max_value=node - 1)))
        partitions[node] = draw(st.sampled_from(["a", "b", "c"]))
    return parents, partitions


@settings(max_examples=150, deadline=None)
@given(group_trees())
def test_atoms_match_direct_definition(tree: tuple[dict[int, int | None], dict[int, str]]) -> None:
    parents, partitions = tree
    builder = SnapshotBuilder()
    ids: dict[int, str] = {}
    for node in sorted(parents):
        parent = parents[node]
        ids[node] = builder.group(
            f"G{node}", 100, ids[parent] if parent is not None else None, partitions[node]
        )
    problem = builder.problem()
    group_atoms = atoms_of_groups(build_atoms(problem), len(problem.groups))
    index = {code: g.index for g in problem.groups for code in [g.code]}
    for a in parents:
        for b in parents:
            if a >= b:
                continue
            via_atoms = bool(group_atoms[index[f"G{a}"]] & group_atoms[index[f"G{b}"]])
            assert via_atoms == _share_students(parents, partitions, a, b), (a, b)
