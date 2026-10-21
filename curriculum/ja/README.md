# Japanese (`ja`) — planned

Japanese is **not yet available**. There is no `language.yaml` and no N5
content, so the API does not load it and the web app should not offer it.

When the pack is ready it will use the JLPT framework (`N5`–`N1`) from
`curriculum/registry.yaml`. To enable it:

1. Add `ja/language.yaml` with `level_framework: jlpt`.
2. Add at least one complete level directory, starting with `N5/`.
3. Add `ja` to the `languages` list in `curriculum/registry.yaml`.
4. Remove `ja` from `planned_languages`.
5. Run `uv run python tools/validate_curriculum.py`.

Japanese needs script-aware handling (kana/kanji, readings, tokenization)
before it should be advertised as supported.
