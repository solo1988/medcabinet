from typing import Optional
from pydantic import BaseModel


class MedicineCreate(BaseModel):
    code: str
    name: str
    gtin: str
    serial_number: str
    expiration_date: str
    manufacturer: str
    symptoms: list[str] = []

class Application(BaseModel):
    id: Optional[int] = None
    name: str

class MedicineApplicationsUpdate(BaseModel):
    application_ids: list[int]

class QRRequest(BaseModel):
    qr_code: str

class CodeRequest(BaseModel):
    code: str
