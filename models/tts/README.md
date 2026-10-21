# Text To Speech Models

Polyglot Coach uses Piper TTS as the primary local speech synthesis engine.

## Voice manifest

`voices.yaml` is the source of truth for downloadable voices. Keys match the
`tts_voice` values in `curriculum/<code>/language.yaml`. Files are saved as
`<key>.onnx` and `<key>.onnx.json`.

| Key | Language | Locales served |
| --- | --- | --- |
| `es` | Spanish | `neutral`, `es_ES`, `es_MX` |
| `fr` | French | `neutral`, `fr_FR`, `fr_CA` |
| `de` | German | `neutral`, `de_DE` |

Japanese has no selected Piper voice yet.

## Download

```bash
uv run python tools/download_voices.py
# or
./run.sh --download-models
```

Voice model files are ignored by git.
