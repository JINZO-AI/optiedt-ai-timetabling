# ADR 0011 — Student groups as a tree with partitions and conflict atoms

**Status:** Accepted

## Context

Programme-based institutions divide cohorts into tutorial groups and lab subgroups (the LMD
`CM/TD/TP` hierarchy), and also into orthogonal divisions such as language options or
elective tracks. Two groups conflict when they share students. A single strict hierarchy
(the original model) cannot express orthogonal divisions.

## Decision

- Student groups form a tree per term. Each child carries a **partition key**. Children of the
  same parent with the same key are disjoint; children with different keys may share students.
- Two groups conflict when one is an ancestor of the other, or when the children of their
  lowest common ancestor on each path have different partition keys.
- For the solver and the metrics, the tree is expanded into **conflict atoms**: every
  combination of one child per partition at each node. Each atom represents students with an
  identical set of group memberships; one at-most-one constraint per atom and period encodes
  all group conflicts exactly, and student idle-time metrics are computed per atom.

## Consequences

- LMD hierarchies, language options and elective tracks are expressed without per-student data.
- Many partitions under one node multiply atoms; identical atom session sets are merged, and
  the validation report warns when a cohort exceeds 256 atoms.
- Individual student enrolment optimization (student sectioning) is out of scope.
