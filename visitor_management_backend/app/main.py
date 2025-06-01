from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session
import uvicorn
import os

from app.database import engine, get_db
from app.models import user, visitor, visit_request, notification, blacklist
from app.api import auth, admin, resident, security, visitor as visitor_api
from app.config import settings

PORT = int(os.environ.get("PORT", 8000))

# Create database tables
user.Base.metadata.create_all(bind=engine)
visitor.Base.metadata.create_all(bind=engine)
visit_request.Base.metadata.create_all(bind=engine)
notification.Base.metadata.create_all(bind=engine)
blacklist.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Visitor Management System API",
    description="A comprehensive visitor management system for apartments and gated communities",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)



# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your Flutter app's domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security scheme
security = HTTPBearer()

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(admin.router, prefix="/api/admin", tags=["Admin"])
app.include_router(resident.router, prefix="/api/resident", tags=["Resident"])
app.include_router(security.router, prefix="/api/security", tags=["Security"])
app.include_router(visitor_api.router, prefix="/api/visitor", tags=["Visitor"])

@app.get("/")
async def root():
    return {
        "message": "Visitor Management System API",
        "version": "1.0.0",
        "status": "running",
        "docs_url": "/docs"
    }

@app.get("/health")
async def health_check(db: Session = Depends(get_db)):
    try:
        # Test database connection
        db.execute("SELECT 1")
        return {
            "status": "healthy",
            "database": "connected",
            "timestamp": "2025-05-31T00:00:00Z"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection failed"
        )

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=PORT,
        reload=False,
    )