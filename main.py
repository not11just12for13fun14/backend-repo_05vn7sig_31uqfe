import os
from typing import List, Optional, Any, Dict
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from bson import ObjectId

app = FastAPI(title="Peptide Research E‑commerce API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----- Database helpers -----
try:
    from database import db, create_document, get_documents
except Exception:
    db = None
    create_document = None
    get_documents = None


def to_str_id(doc: Dict[str, Any]) -> Dict[str, Any]:
    if not doc:
        return doc
    d = dict(doc)
    if d.get("_id") is not None:
        d["id"] = str(d.pop("_id"))
    return d


# ----- Schemas -----
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
    research_use_only_ack: bool = Field(..., description="Customer acknowledges RUO")
    age_over_21_ack: bool = Field(..., description="Customer confirms age as required")
    notes: Optional[str] = None


# ----- Routes -----
@app.get("/")
def read_root():
    return {"message": "Peptide Research API running"}


@app.get("/api/hello")
def hello():
    return {"message": "Hello from the backend API!"}


@app.get("/api/disclaimer")
def disclaimer():
    return {
        "title": "Research Use Only",
        "content": (
            "All products are intended for laboratory research use only. "
            "Not for human or veterinary use, diagnostics, or therapeutic applications. "
            "By proceeding, you confirm you are a qualified researcher in compliance with applicable laws and regulations."
        ),
    }


@app.get("/api/products")
def list_products() -> List[Dict[str, Any]]:
    if db is None:
        # Return an empty list if DB not configured; frontend will handle gracefully
        return []
    docs = get_documents("peptideproduct")
    return [to_str_id(d) for d in docs]


@app.get("/api/products/{product_id}")
def get_product(product_id: str) -> Dict[str, Any]:
    if db is None:
        raise HTTPException(status_code=404, detail="Product not found")
    try:
        oid = ObjectId(product_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid product id")
    doc = db["peptideproduct"].find_one({"_id": oid})
    if not doc:
        raise HTTPException(status_code=404, detail="Product not found")
    return to_str_id(doc)


@app.post("/api/products", status_code=201)
def create_product(product: PeptideProduct) -> Dict[str, Any]:
    if db is None:
        raise HTTPException(status_code=500, detail="Database not available")
    inserted_id = create_document("peptideproduct", product)
    return {"id": inserted_id}


@app.post("/api/orders", status_code=201)
def create_order(order: Order) -> Dict[str, Any]:
    if not order.research_use_only_ack or not order.age_over_21_ack:
        raise HTTPException(status_code=400, detail="Compliance acknowledgements are required")
    if db is None:
        # Accept but do not persist if DB isn't configured
        return {
            "status": "received",
            "persisted": False,
        }
    inserted_id = create_document("order", order)
    return {"status": "received", "persisted": True, "id": inserted_id}


@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    try:
        from database import db as _db
        if _db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
            response["database_name"] = _db.name if hasattr(_db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            try:
                collections = _db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"
    return response


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
