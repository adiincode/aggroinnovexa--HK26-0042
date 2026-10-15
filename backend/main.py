from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from db import Base, engine
import models  # noqa: F401  (tables register hone ke liye)
from routers import assignments, integrity
from routers import text as text_router
from routers import video as video_router
from routers import code as code_router

Base.metadata.create_all(bind=engine)

app = FastAPI(title="TrueWrite API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(assignments.router)
app.include_router(integrity.router)
app.include_router(text_router.router)
app.include_router(video_router.router)
app.include_router(code_router.router)


@app.get("/")
def root():
    return {"message": "TrueWrite API is running"}


@app.get("/health")
def health():
    return {"status": "ok"}