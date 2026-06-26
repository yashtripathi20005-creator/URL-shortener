from sqlalchemy.orm import Session
from sqlalchemy import and_
from app import models, schemas
import random
import string
from datetime import datetime, timedelta

def generate_short_code(length=6):
    """Generate a random short code"""
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(length))

def create_url(db: Session, url: schemas.URLCreate):
    """Create a new shortened URL"""
    # Generate or use custom code
    if url.custom_code:
        # Check if custom code is available
        existing = db.query(models.URL).filter(models.URL.short_code == url.custom_code).first()
        if existing:
            return None, "Custom code already taken"
        short_code = url.custom_code
    else:
        # Generate unique code
        short_code = generate_short_code()
        while db.query(models.URL).filter(models.URL.short_code == short_code).first():
            short_code = generate_short_code()
    
    # Calculate expiration date if provided
    expires_at = None
    if url.expires_in_days:
        expires_at = datetime.utcnow() + timedelta(days=url.expires_in_days)
    
    db_url = models.URL(
        original_url=str(url.original_url),
        short_code=short_code,
        expires_at=expires_at
    )
    
    db.add(db_url)
    db.commit()
    db.refresh(db_url)
    return db_url, None

def get_url_by_code(db: Session, short_code: str):
    """Get URL by short code"""
    return db.query(models.URL).filter(
        and_(
            models.URL.short_code == short_code,
            models.URL.is_active == True
        )
    ).first()

def increment_clicks(db: Session, url: models.URL):
    """Increment click count for a URL"""
    url.clicks += 1
    db.commit()
    db.refresh(url)
    return url

def get_url_stats(db: Session, short_code: str):
    """Get statistics for a URL"""
    return db.query(models.URL).filter(models.URL.short_code == short_code).first()

def delete_url(db: Session, short_code: str):
    """Soft delete a URL"""
    url = db.query(models.URL).filter(models.URL.short_code == short_code).first()
    if url:
        url.is_active = False
        db.commit()
        return True
    return False

def get_all_urls(db: Session, skip: int = 0, limit: int = 100):
    """Get all URLs with pagination"""
    return db.query(models.URL).filter(models.URL.is_active == True).offset(skip).limit(limit).all()
