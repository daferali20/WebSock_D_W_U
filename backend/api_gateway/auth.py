from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from core.config import settings

security = HTTPBearer()

async def verify_jwt_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """
    التحقق من صحة توكن JWT واستخراج البيانات منها
    """
    token = credentials.credentials
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="تعذر التحقق من اعتمادات الوصول (Invalid Token)",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(
            token, 
            settings.JWT_SECRET_KEY, 
            algorithms=[settings.JWT_ALGORITHM]
        )
        user_id: str = payload.get("sub")
        role: str = payload.get("role", "user")
        
        if user_id is None:
            raise credentials_exception
            
        return {"user_id": user_id, "role": role}
        
    except JWTError:
        raise credentials_exception
