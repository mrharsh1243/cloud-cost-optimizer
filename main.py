from fastapi import FastAPI
from scan_api import router as scan_router
from read_api import router as read_router

app = FastAPI()

app.include_router(scan_router)
app.include_router(read_router)

@app.get("/")
def health():
    return {"status": "Cloud Cost Optimizer running"}