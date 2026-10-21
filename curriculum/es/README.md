# Spanish (`es`)

Canonical Spanish language pack. Metadata lives in `language.yaml`; level
content lives in the matching level directory.

## Current coverage

| Level | Grammar | Vocabulary | Scenarios | Locale overrides |
| --- | --- | --- | --- | --- |
| A1 | 10 rules | 40 words | 6 | 8 (`es_MX`) |

A2–C1 are planned. Do not add a level to `language.yaml` until its directory
contains real content.

## Locales

- `neutral`
- `es_ES`
- `es_MX`

Validate changes with:

```bash
uv run python tools/validate_curriculum.py
```
