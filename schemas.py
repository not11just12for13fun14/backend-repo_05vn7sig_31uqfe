from pydantic import BaseModel, Field
from typing import Optional, List

class PeptideProduct(BaseModel):
    name: str = Field(..., description="Product name")
    code: str = Field(..., description="Catalog code")
    description: Optional[str] = Field(None, description="Short description")
    price: float = Field(..., ge=0, description="Price in USD")
    purity: str = Field(..., description="e.g., ≥98% (HPLC)")
    form: str = Field(..., description="e.g., Lyophilized powder")
    storage: str = Field(..., description="e.g., -20°C, desiccated")
    size: str = Field(..., description="e.g., 5 mg vial")
    in_stock: bool = Field(True, description="Inventory status")
    research_only: bool = Field(True, description="Research Use Only flag")

class OrderItem(BaseModel):
    product_id: str
    quantity: int = Field(ge=1, default=1)

class Order(BaseModel):
    items: List[OrderItem]
    customer_name: str
    email: str
    institution: Optional[str] = None
    country: str
    research_use_only_ack: bool
    age_over_21_ack: bool
    notes: Optional[str] = None
