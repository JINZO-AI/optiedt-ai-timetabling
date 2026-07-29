"""Reads data/instance/ into typed domain objects.

The only thing in the backend allowed to open the 13 CSVs. Depends on
domain/ only, so it stays a leaf: solver/, preanalysis/ and (later)
analysis/ can all depend on it without violating any existing layer
contract, since none of them may depend on each other directly.

Deliberately separate from data/verification/verify_instance.py, which
reads the same files but is kept standalone on purpose, with zero
dependency on this backend, so it can guard the data contract
independently of whatever the application code does.
"""
