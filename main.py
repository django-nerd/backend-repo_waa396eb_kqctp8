import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

app = FastAPI(title="Transfreight API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class QuoteRequest(BaseModel):
    origin: str = Field(..., min_length=2, max_length=100)
    destination: str = Field(..., min_length=2, max_length=100)
    container: str = Field(..., pattern=r"^(FCL|LCL)$")


class QuoteResponse(BaseModel):
    estimate: str
    currency: str = "USD"
    transit_days: int
    breakdown: dict
    message: str


@app.get("/")
def read_root():
    return {"message": "Hello from FastAPI Backend!"}


@app.get("/api/hello")
def hello():
    return {"message": "Hello from the backend API!"}


@app.post("/api/quote", response_model=QuoteResponse)
def get_quote(payload: QuoteRequest):
    """Lightweight quote estimator to power the landing page CTA.
    This is a heuristic only and not a real rate engine.
    """
    # Very rough distance heuristic based on string difference and length
    seed = abs(len(payload.origin) - len(payload.destination)) + sum(
        abs(ord(a) - ord(b)) for a, b in zip(payload.origin.lower()[:3], payload.destination.lower()[:3])
    )

    base = 900 if payload.container == "LCL" else 2200
    variability = (seed % 900)  # 0..899
    fuel_surcharge = round(base * 0.12)
    security = 45 if payload.container == "LCL" else 60
    handling = 35 if payload.container == "LCL" else 50

    subtotal = base + variability + fuel_surcharge + security + handling

    # Simple transit time heuristic
    transit_days = 18 + (seed % 17)  # 18..34 days

    breakdown = {
        "base": base,
        "distance_factor": variability,
        "fuel_surcharge": fuel_surcharge,
        "security": security,
        "handling": handling,
    }

    return QuoteResponse(
        estimate=f"{subtotal:,}",
        currency="USD",
        transit_days=transit_days,
        breakdown=breakdown,
        message="Instant estimate generated. Final pricing may vary after verification.",
    )


@app.get("/test")
def test_database():
    """Test endpoint to check if database is available and accessible"""
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    
    try:
        # Try to import database module
        from database import db
        
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            
            # Try to list collections to verify connectivity
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]  # Show first 10 collections
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
            
    except ImportError:
        response["database"] = "❌ Database module not found (run enable-database first)"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"
    
    # Check environment variables
    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"
    
    return response


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
