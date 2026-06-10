from fastapi import Header, HTTPException, Depends
from config import settings


async def verify_api_key(x_api_key: str = Header(...)):
    if x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="API Key inválida")
    return x_api_key


AuthDep = Depends(verify_api_key)
