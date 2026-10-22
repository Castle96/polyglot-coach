# Web App

Static single-page chat client (`index.html`) served by the FastAPI app.

Current limitations:

- UI strings are English-only
- No build step; the package exists for workspace tooling and a static lint
  check (`pnpm --filter @polyglot-coach/web lint`), which verifies that element
  ids, selectors, fetch routes, and structural tags in `index.html` resolve

Language, level, locale, and advanced-feature controls are populated from
`/api/v1/meta/languages`. The sidebar sends selected features with each tutor
request.

## Speech controls

The microphone button records a short clip with `MediaRecorder` and sends it to
`/api/v1/speech/transcribe`. The transcript is placed in the message box for
editing; it is not sent automatically. Recording stops when the button is
clicked again.

“Speak tutor replies” sends each tutor response to
`/api/v1/speech/synthesize` and plays the returned WAV audio. Playback stops
when a new message is sent or another reply starts.

Both controls are disabled when `/health` reports that STT or TTS is
unavailable. Text chat is unaffected. Browser support requires
`navigator.mediaDevices.getUserMedia` and `MediaRecorder`; microphone access
must be granted for the API origin (or localhost).

Run the API from the repository root and open <http://localhost:8000>.
