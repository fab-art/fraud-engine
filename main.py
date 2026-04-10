from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import ingestion

app = FastAPI(title="Pharma Counter Verification API")

# Configure CORS for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(ingestion.router, prefix="/api/v1/ingest", tags=["ingestion"])


@app.get("/health")
def health_check():
    return {"status": "healthy"}
