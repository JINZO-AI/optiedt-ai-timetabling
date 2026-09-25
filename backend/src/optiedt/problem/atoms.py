"""Conflict atoms: the distinct kinds of student within the group tree (ADR 0011).

An atom picks, at every group it belongs to, one child from each partition of that group (or
"none of them" when the partition does not cover every student). Two groups share students
exactly when some atom belongs to both, so one at-most-one constraint per atom and slot
expresses every student conflict, and an atom's day is what a student of that kind lives.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import product

from optiedt.problem.model import Group, Problem

MAX_ATOMS_PER_ROOT = 512


@dataclass(frozen=True, slots=True)
class Atom:
    index: int
    groups: frozenset[int]
    """Every group whose students include this atom's students."""
    size: float
    """Estimated number of students, assuming partitions are independent."""
    root: int


@dataclass(frozen=True, slots=True)
class _Partial:
    groups: frozenset[int]
    fraction: float


def _expand(groups: tuple[Group, ...], index: int, budget: list[int]) -> list[_Partial]:
    group = groups[index]
    partitions: dict[str, list[int]] = {}
    for child in group.children:
        partitions.setdefault(groups[child].partition, []).append(child)
    if not partitions:
        return [_Partial(frozenset({index}), 1.0)]

    options_per_partition: list[list[_Partial]] = []
    for key in sorted(partitions):
        children = partitions[key]
        options: list[_Partial] = []
        covered = 0
        for child in children:
            share = groups[child].size / group.size if group.size else 1.0 / len(children)
            covered += groups[child].size
            options.extend(
                _Partial(p.groups, p.fraction * share) for p in _expand(groups, child, budget)
            )
        if group.size and covered < group.size:
            options.append(_Partial(frozenset(), (group.size - covered) / group.size))
        options_per_partition.append(options)

    combined: list[_Partial] = []
    for choice in product(*options_per_partition):
        fraction = 1.0
        members: set[int] = {index}
        for part in choice:
            fraction *= part.fraction
            members |= part.groups
        combined.append(_Partial(frozenset(members), fraction))
        budget[0] -= 1
        if budget[0] < 0:
            raise TooManyAtomsError(group.code)
    return combined


class TooManyAtomsError(ValueError):
    def __init__(self, group_code: str) -> None:
        super().__init__(
            f"The subgroups of {group_code} combine into more than {MAX_ATOMS_PER_ROOT} kinds of "
            "student. Reduce the number of overlapping partitions."
        )
        self.group_code = group_code


def build_atoms(problem: Problem) -> list[Atom]:
    groups = problem.groups
    atoms: list[Atom] = []
    for root in (g for g in groups if g.parent is None):
        budget = [MAX_ATOMS_PER_ROOT]
        for partial in _expand(groups, root.index, budget):
            atoms.append(
                Atom(
                    index=len(atoms),
                    groups=partial.groups,
                    size=root.size * partial.fraction,
                    root=root.index,
                )
            )
    return atoms


def atoms_of_groups(atoms: list[Atom], n_groups: int) -> list[frozenset[int]]:
    """For each group, the atoms whose students it contains."""
    result: list[set[int]] = [set() for _ in range(n_groups)]
    for atom in atoms:
        for group in atom.groups:
            result[group].add(atom.index)
    return [frozenset(s) for s in result]
