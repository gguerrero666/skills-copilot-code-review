"""
Announcements endpoints for the High School Management System API
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List
from datetime import datetime, timezone
from pydantic import BaseModel, Field

from ..database import announcements_collection, teachers_collection

router = APIRouter(
    prefix="/announcements",
    tags=["announcements"]
)


class AnnouncementCreate(BaseModel):
    message: str = Field(..., min_length=1, max_length=500)
    start_date: str | None = None
    expiration_date: str


class AnnouncementUpdate(BaseModel):
    message: str | None = Field(None, min_length=1, max_length=500)
    start_date: str | None = None
    expiration_date: str | None = None


@router.get("")
def get_active_announcements() -> List[Dict[str, Any]]:
    """Get all active announcements (within date range)"""
    current_date = datetime.now(timezone.utc).isoformat()
    
    announcements = list(announcements_collection.find({}))
    
    # Filter active announcements
    active_announcements = []
    for announcement in announcements:
        # Check if announcement has started (if start_date is set)
        if announcement.get("start_date") and announcement["start_date"] > current_date:
            continue
        
        # Check if announcement has expired
        if announcement.get("expiration_date") and announcement["expiration_date"] < current_date:
            continue
        
        # Convert ObjectId to string
        announcement["_id"] = str(announcement["_id"])
        active_announcements.append(announcement)
    
    return active_announcements


@router.get("/all")
def get_all_announcements(username: str) -> List[Dict[str, Any]]:
    """Get all announcements (for management - requires authentication)"""
    # Verify user is authenticated
    teacher = teachers_collection.find_one({"_id": username})
    if not teacher:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    announcements = list(announcements_collection.find({}))
    
    # Convert ObjectId to string
    for announcement in announcements:
        announcement["_id"] = str(announcement["_id"])
    
    return announcements


@router.post("")
def create_announcement(announcement: AnnouncementCreate, username: str) -> Dict[str, Any]:
    """Create a new announcement (requires authentication)"""
    # Verify user is authenticated
    teacher = teachers_collection.find_one({"_id": username})
    if not teacher:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    # Validate dates
    try:
        if announcement.start_date:
            datetime.fromisoformat(announcement.start_date.replace('Z', '+00:00'))
        datetime.fromisoformat(announcement.expiration_date.replace('Z', '+00:00'))
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format")
    
    # Create announcement document
    announcement_doc = {
        "message": announcement.message,
        "start_date": announcement.start_date,
        "expiration_date": announcement.expiration_date,
        "created_by": username,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    result = announcements_collection.insert_one(announcement_doc)
    announcement_doc["_id"] = str(result.inserted_id)
    
    return announcement_doc


@router.put("/{announcement_id}")
def update_announcement(
    announcement_id: str,
    announcement: AnnouncementUpdate,
    username: str
) -> Dict[str, Any]:
    """Update an announcement (requires authentication)"""
    from bson import ObjectId
    
    # Verify user is authenticated
    teacher = teachers_collection.find_one({"_id": username})
    if not teacher:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    # Find the announcement
    try:
        existing_announcement = announcements_collection.find_one({"_id": ObjectId(announcement_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid announcement ID")
    
    if not existing_announcement:
        raise HTTPException(status_code=404, detail="Announcement not found")
    
    # Build update document
    update_doc = {}
    if announcement.message is not None:
        update_doc["message"] = announcement.message
    if announcement.start_date is not None:
        update_doc["start_date"] = announcement.start_date
    if announcement.expiration_date is not None:
        # Validate date format
        try:
            datetime.fromisoformat(announcement.expiration_date.replace('Z', '+00:00'))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format")
        update_doc["expiration_date"] = announcement.expiration_date
    
    if not update_doc:
        raise HTTPException(status_code=400, detail="No fields to update")
    
    # Update the announcement
    announcements_collection.update_one(
        {"_id": ObjectId(announcement_id)},
        {"$set": update_doc}
    )
    
    # Fetch updated announcement
    updated_announcement = announcements_collection.find_one({"_id": ObjectId(announcement_id)})
    updated_announcement["_id"] = str(updated_announcement["_id"])
    
    return updated_announcement


@router.delete("/{announcement_id}")
def delete_announcement(announcement_id: str, username: str) -> Dict[str, str]:
    """Delete an announcement (requires authentication)"""
    from bson import ObjectId
    
    # Verify user is authenticated
    teacher = teachers_collection.find_one({"_id": username})
    if not teacher:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    # Delete the announcement
    try:
        result = announcements_collection.delete_one({"_id": ObjectId(announcement_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid announcement ID")
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Announcement not found")
    
    return {"message": "Announcement deleted successfully"}
