# Playbook Update Suggestions

## Observed Patterns
- Small, low-risk endpoints are frequently requested and often miss tests.

## Proposed Changes
- Update Flow 2 template to include a default `health` test snippet.
- Add a Gate check that `build_receipt.json` includes `requirements_covered` field.
