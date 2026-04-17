from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routes.chat import router as chat_router
from routes.doctor import router as doctor_router
from routes.metrics import router as metrics_router


app = FastAPI(title="Healthcare Medical Assistant API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router, prefix="/chat", tags=["chat"])
app.include_router(doctor_router, prefix="/doctor", tags=["doctor"])
app.include_router(metrics_router, prefix="/metrics", tags=["metrics"])


@app.get("/")
def health() -> dict:
    return {"status": "ok", "service": "healthcare-medical-assistant"}
