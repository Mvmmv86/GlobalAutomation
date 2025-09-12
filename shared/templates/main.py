from fastapi import FastAPI

app = FastAPI(title="GlobalAutomations AI Service Template")

@app.get("/")
async def health_check():
    return {"status": "healthy", "service": "service-template"}

@app.get("/health")
async def health():
    return {"status": "ok"}