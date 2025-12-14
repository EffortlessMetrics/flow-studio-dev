"""
Pytest configuration for BDD tests.

This module ensures that BDD step definitions are discovered and registered.
"""

# Import step definitions to register them with pytest-bdd
from . import steps as _  # noqa: F401
