"""Run the API server with uvicorn."""

import uvicorn

if __name__ == "__main__":
    uvicorn.run("polyglot_coach_api.main:app", host="0.0.0.0", port=8004, reload=True)
