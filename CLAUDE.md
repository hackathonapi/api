# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

**Setup**
```bash
python -m venv .venv
source .venv/Scripts/activate  # Windows (bash)
pip install -r requirements.txt
```

**Run the API**
```bash
uvicorn src.main:app --reload
```

**Access interactive docs**
- Swagger UI: http://127.0.0.1:8000/docs
- ReDoc: http://127.0.0.1:8000/redoc

## Architecture

This is a **FastAPI** boilerplate for HackIllinois. The project is in early stages with a single entrypoint:

- [src/main.py](src/main.py) — All routes and Pydantic models live here. FastAPI app is instantiated as `app`.

Key dependencies: FastAPI + Uvicorn (ASGI server), Pydantic v2 for request/response validation, `python-dotenv` for environment config, `sentry-sdk` for error tracking, `httpx` for async HTTP calls.

As the project grows, the expected pattern is to expand `src/` with separate modules for routes, models, and services.
