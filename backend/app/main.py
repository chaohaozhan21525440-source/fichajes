from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import auth, workers, checkins, export, audit
from app.config import settings

app = FastAPI(title="Employee Time Tracking API", version="1.0.0")

origins = [o.strip() for o in settings.allowed_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(workers.router)
app.include_router(checkins.router)
app.include_router(export.router)
app.include_router(audit.router)


@app.get("/health")
def health():
    return {"status": "ok"}
