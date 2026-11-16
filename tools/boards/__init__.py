"""Board descriptions for tools/mkadt.py.

Each module defines BOARD, a dict of the physical facts the Apple Device Tree
needs. A value of None means "not known yet": mkadt.py refuses to build for a
board with None in a field it uses, and lists the missing fields.
Fill them from the phone's live FDT (tools/fdt-scan.py).
"""
import importlib

NAMES = ('sweet', 'alioth')


def load(name):
    if name not in NAMES:
        raise SystemExit(f'unknown board {name!r}; known: {", ".join(NAMES)}')
    return importlib.import_module(f'boards.{name}').BOARD


def missing(board, keys):
    return [k for k in keys if board.get(k) is None]
