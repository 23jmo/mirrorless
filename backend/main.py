from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from scraper.routes import router as scraper_router

app = FastAPI(title="Mirrorless API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(scraper_router)


@app.get("/health")
async def health():
    return {"status": "ok"}
