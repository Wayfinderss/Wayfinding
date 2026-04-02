from fastapi import APIRouter
router = APIRouter(prefix="/valhalla", tags=["valhalla"])

@router.get("/health")
def health():
    return {"status": "ok"}