# Web App

Static single-page chat client (`index.html`) served by the FastAPI app.

Current limitations:

- UI strings are English-only
- No build step or `package.json`; the workspace scripts in the repository
  root are placeholders until the frontend is packaged

Language, level, locale, and advanced-feature controls are populated from
`/api/v1/meta/languages`. The sidebar sends selected features with each tutor
request.

Run the API from the repository root and open <http://localhost:8000>.
