from fastapi import FastAPI

app = FastAPI(title="Finance-Tracker")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
