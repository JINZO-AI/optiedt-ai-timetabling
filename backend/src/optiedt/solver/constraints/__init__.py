"""ConstraintBuilder registrations for H1 through H12.

Four of the twelve are real CP-SAT postings (overlap.py: H1, H12;
room_assignment.py: H3, H7). The other eight exist for catalogue
completeness and to answer C-6, but their apply() does nothing, for two
different reasons:

  - H4, H5, H6, H8, H9, H10 (domain_pruned.py) are domain restrictions.
    They are already enforced by the time a session's variables exist -
    see solver/variables.py, which is where the actual work happens.
    There is nothing left to post, and nothing an assumption literal
    could attach to: you cannot put an enforcement literal on a
    variable's initial domain the way you can on a posted constraint.

  - H2, H11 (noop.py) are subsumed by H12 and H3 respectively. Posting
    them again would be a redundant constraint achieving nothing the
    encompassing one doesn't already guarantee.

carries_assumption_literal is True only for H1, H3, H7, H12 - the four
constraints that are actually posted objects a literal can be attached
to. This is C-6, resolved.
"""

from optiedt.solver.constraints.domain_pruned import H4, H5, H6, H8, H9, H10
from optiedt.solver.constraints.noop import H2, H11
from optiedt.solver.constraints.overlap import H1, H12
from optiedt.solver.constraints.room_assignment import H3, H7

ALL_HARD_CONSTRAINTS = (
    H1(),
    H2(),
    H3(),
    H4(),
    H5(),
    H6(),
    H7(),
    H8(),
    H9(),
    H10(),
    H11(),
    H12(),
)
"""Registered in catalogue order. See solver/engine.py for how these are applied."""
