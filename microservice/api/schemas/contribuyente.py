from pydantic import BaseModel


class Contribuyente(BaseModel):
    nit: str
    razon_social: str | None = None
    ciiu: str | None = None
    municipio: str | None = None
    estado: str | None = None
