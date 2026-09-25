from fastapi import FastAPI

app = FastAPI(title="Copiloto de Certificación QA", version="0.1.0")


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
