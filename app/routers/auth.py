from fastapi import APIRouter, Depends, HTTPException, status
from app.schemas.auth import LoginRequest, TokenResponse, AdminResponse
from app.auth.security import verify_password, create_access_token
from app.auth.dependencies import get_current_admin
from app.database import get_admins_collection

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

@router.post("/login", response_model=TokenResponse)
async def login(credentials: LoginRequest):
    admins_col = get_admins_collection()
    admin = await admins_col.find_one({"email": credentials.email.lower().strip()})
    
    if not admin or not verify_password(credentials.password, admin["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    token = create_access_token({"sub": admin["email"]})
    return TokenResponse(access_token=token, admin_email=admin["email"])

@router.get("/me", response_model=AdminResponse)
async def get_current_admin_profile(current_admin: dict = Depends(get_current_admin)):
    return AdminResponse(email=current_admin["email"], name=current_admin.get("name", "Admin"))
