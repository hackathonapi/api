from fastapi import FastAPI

from src.accessibility import router as accessibility_router

app = FastAPI(title="Accessibility API", version="0.1.0")


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "Accessibility API is running"}


app.include_router(accessibility_router)
