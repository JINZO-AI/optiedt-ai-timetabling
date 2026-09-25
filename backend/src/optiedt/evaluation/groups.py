"""Which student groups share students, computed directly from the group tree.

Deliberately not derived from conflict atoms: hard student conflicts are checked here by a
second, independent route (ADR 0009).
"""

from __future__ import annotations

from functools import lru_cache

from optiedt.problem.model import Problem


class GroupOverlap:
    def __init__(self, problem: Problem) -> None:
        self._problem = problem
        self._chains = [self._chain(g.index) for g in problem.groups]

    def _chain(self, index: int) -> tuple[int, ...]:
        chain = [index]
        seen = {index}
        while (parent := self._problem.groups[chain[-1]].parent) is not None and parent not in seen:
            chain.append(parent)
            seen.add(parent)
        return tuple(chain)

    @lru_cache(maxsize=65536)  # noqa: B019 - one instance per problem, released with it
    def share_students(self, a: int, b: int) -> bool:
        if a == b:
            return True
        chain_a, chain_b = self._chains[a], self._chains[b]
        if a in chain_b or b in chain_a:
            return True
        set_b = set(chain_b)
        common = next((node for node in chain_a if node in set_b), None)
        if common is None:
            return False
        below_a = chain_a[chain_a.index(common) - 1]
        below_b = chain_b[chain_b.index(common) - 1]
        groups = self._problem.groups
        return groups[below_a].partition != groups[below_b].partition

    def sessions_share_students(self, groups_a: tuple[int, ...], groups_b: tuple[int, ...]) -> bool:
        return any(self.share_students(a, b) for a in groups_a for b in groups_b)
