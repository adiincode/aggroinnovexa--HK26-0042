from fastapi import FastAPI

app = FastAPI(title="TrueWrite API")


@app.get("/health")
def health():
    return {"status": "ok"}