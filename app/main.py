from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.responses import RedirectResponse, HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from datetime import datetime
import os
from dotenv import load_dotenv

from app.database import engine, get_db, Base
from app import crud, schemas

load_dotenv()

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="URL Shortener API",
    description="A simple URL shortener service with analytics",
    version="1.0.0"
)

# Setup templates
templates = Jinja2Templates(directory="templates")

BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Home page with UI"""
    return templates.TemplateResponse("index.html", {"request": request, "base_url": BASE_URL})

@app.post("/api/shorten", response_model=schemas.URLResponse, status_code=status.HTTP_201_CREATED)
async def shorten_url(
    url: schemas.URLCreate,
    db: Session = Depends(get_db)
):
    """
    Create a shortened URL
    
    - **original_url**: The URL to shorten (must be valid HTTP/HTTPS)
    - **custom_code**: Optional custom short code (3-20 chars, alphanumeric, -_ only)
    - **expires_in_days**: Optional expiration in days (1-365)
    """
    db_url, error = crud.create_url(db, url)
    
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )
    
    return schemas.URLResponse(
        id=db_url.id,
        original_url=db_url.original_url,
        short_code=db_url.short_code,
        short_url=f"{BASE_URL}/{db_url.short_code}",
        created_at=db_url.created_at,
        expires_at=db_url.expires_at,
        clicks=db_url.clicks,
        is_active=db_url.is_active
    )

@app.get("/{short_code}")
async def redirect_to_url(short_code: str, db: Session = Depends(get_db)):
    """
    Redirect to the original URL
    """
    db_url = crud.get_url_by_code(db, short_code)
    
    if not db_url:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Short URL not found or has been deactivated"
        )
    
    # Check if URL has expired
    if db_url.expires_at and db_url.expires_at < datetime.utcnow():
        db_url.is_active = False
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="This URL has expired"
        )
    
    # Increment click count
    crud.increment_clicks(db, db_url)
    
    return RedirectResponse(url=db_url.original_url, status_code=status.HTTP_302_FOUND)

@app.get("/api/stats/{short_code}", response_model=schemas.URLStatsResponse)
async def get_url_stats(short_code: str, db: Session = Depends(get_db)):
    """
    Get statistics for a shortened URL
    """
    db_url = crud.get_url_stats(db, short_code)
    
    if not db_url:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Short URL not found"
        )
    
    return schemas.URLStatsResponse(
        original_url=db_url.original_url,
        short_code=db_url.short_code,
        short_url=f"{BASE_URL}/{db_url.short_code}",
        created_at=db_url.created_at,
        expires_at=db_url.expires_at,
        clicks=db_url.clicks,
        is_active=db_url.is_active
    )

@app.delete("/api/{short_code}")
async def delete_url(short_code: str, db: Session = Depends(get_db)):
    """
    Deactivate a shortened URL (soft delete)
    """
    success = crud.delete_url(db, short_code)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Short URL not found"
        )
    
    return {"message": "URL deactivated successfully"}

@app.get("/api/urls", response_model=list[schemas.URLResponse])
async def list_urls(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    List all active shortened URLs with pagination
    """
    urls = crud.get_all_urls(db, skip=skip, limit=limit)
    
    return [
        schemas.URLResponse(
            id=url.id,
            original_url=url.original_url,
            short_code=url.short_code,
            short_url=f"{BASE_URL}/{url.short_code}",
            created_at=url.created_at,
            expires_at=url.expires_at,
            clicks=url.clicks,
            is_active=url.is_active
        )
        for url in urls
    ]

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail}
    )
