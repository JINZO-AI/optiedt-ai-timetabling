"""Entities, enums and value objects. PURE: no I/O, no ORM, no framework imports.

Imported by the solver, the analysis layer and the persistence layer alike, which
is why a framework import here would leak into all three.
"""
