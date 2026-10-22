# Desktop App

Planned Tauri-based desktop application for Windows, Linux, and macOS.

Not implemented yet. This directory only contains a `package.json` stub so the
pnpm workspace resolves; there is no Tauri project or source code. The stub's
`dev` and `build` scripts exit with a message pointing here:

```bash
pnpm --filter @polyglot-coach/desktop dev
pnpm --filter @polyglot-coach/desktop build
```

Until the desktop shell exists, use the web client served by the API
(`./run.sh` from the repository root).
