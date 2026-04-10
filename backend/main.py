from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import ingestion

app = FastAPI(
    title="Pharmaceutical Counter Verification API",
    description="Backend for Post-Payment Fraud Audit SaaS",
    version="1.0.0"
)

# Configure CORS - allow all origins for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(ingestion.router)


@app.get("/", tags=["Health"])
async def health_check():
    """Simple health check endpoint."""
    return {"status": "healthy", "message": "Pharmaceutical Counter Verification API is running"}
