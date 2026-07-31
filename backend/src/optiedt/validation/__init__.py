"""Validation against published benchmark instances. NOT product code.

`docs/testing-strategy.md` §1 makes this one of the project's four verifications,
and the one that answers "is the model correct?": an engine validated only on the
instance it was built around has demonstrated nothing.

⚠️ **Nothing in `optiedt` may import this package.** It exists to run *against*
the product, not inside it, and `.importlinter`'s `benchmark-validation-is-not-
product-code` contract fails the build if that ever changes. It lives under
`src/` rather than under `tests/` for one reason: everything under `src/` is
type-checked by mypy --strict and linted by ruff, and a validation harness whose
arithmetic is wrong would report a wrong verdict with full confidence.

The data it reads (`data/reference/`) is **gitignored**. Every entry point here
must degrade to a clear "archives absent" rather than an ImportError or a stack
trace, so a fresh clone can still run the test suite.
"""

from __future__ import annotations
