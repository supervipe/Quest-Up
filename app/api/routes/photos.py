from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.models.user import User

router = APIRouter(prefix="/photos", tags=["photos"])


@router.post("/upload-url")
async def upload_url(current_user: User = Depends(get_current_user)):
    return {"upload_url": f"local://uploads/{current_user.id}/photo.jpg", "method": "mock"}


@router.post("/metadata")
async def metadata(payload: dict, current_user: User = Depends(get_current_user)):
    return {"user_id": current_user.id, "metadata": payload}
