"""
Executable BDD scenarios for the selftest system.

These scenarios are defined in features/selftest.feature.
pytest-bdd auto-discovers all scenarios via the scenarios() call below.

The step definitions are in tests/bdd/steps/selftest_steps.py
and will be auto-discovered by pytest-bdd.

Running:
    # Run all BDD scenarios
    pytest tests/test_selftest_bdd.py -v

    # Run only scenarios with @executable tag
    pytest tests/test_selftest_bdd.py -m executable -v

    # Run a specific scenario by name (auto-generated from scenario title)
    pytest tests/test_selftest_bdd.py::test_kernel_smoke_check_is_fast_and_reliable -v

Scenario naming:
    pytest-bdd auto-generates test function names from scenario titles:
    - "Kernel smoke check is fast and reliable" -> test_kernel_smoke_check_is_fast_and_reliable
    - "Selftest plan shows all steps with tiers" -> test_selftest_plan_shows_all_steps_with_tiers
"""

from pytest_bdd import scenarios

# Feature file path (relative to this test file)
FEATURE_FILE = "../features/selftest.feature"

# Auto-discover all scenarios from feature file
# pytest-bdd creates test functions for each scenario automatically
# Scenario titles become test function names (lowercase, underscored)
scenarios(FEATURE_FILE)
