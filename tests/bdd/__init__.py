# BDD test support for selftest feature file

# Import steps so pytest-bdd can discover them
from . import steps as _bdd_steps  # noqa: F401
