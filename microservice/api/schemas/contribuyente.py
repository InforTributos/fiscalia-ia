from pydantic import BaseModel
from typing import Optional


class Contribuyente(BaseModel):
    nit: str
    razon_social: Optional[str] = None
    ciiu: Optional[str] = None
    municipio: Optional[str] = None
    estado: Optional[str] = None
