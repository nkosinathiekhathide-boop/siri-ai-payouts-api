"""
SIRI-AI Payouts Engine
Telemetry-driven outgrower payouts over Pi Network and USDC
Version: 1.0.0
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import uuid
from datetime import datetime

app = FastAPI(
    title="SIRI-AI Payouts Engine",
    description="Telemetry-driven outgrower payouts over Pi Network and USDC",
    version="1.0.0"
)

# --- Allow Base44 to connect ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
# IN-MEMORY DATABASE (replace with PostgreSQL in production)
# ============================================================
outgrowers = {}
payouts = []
telemetry = []

# ============================================================
# MODELS
# ============================================================

class Outgrower(BaseModel):
    outgrower_id: str
    name: str
    phone: str
    location: str
    wallet_pi: Optional[str] = None
    wallet_usdc: Optional[str] = None

class TelemetryRecord(BaseModel):
    outgrower_id: str
    tonnes_delivered: float
    crop_type: str
    date: str

class PayoutRequest(BaseModel):
    outgrower_id: str
    amount: float
    currency: str  # "Pi" or "USDC"
    reason: str

class PayoutResponse(BaseModel):
    payout_id: str
    outgrower_id: str
    amount: float
    currency: str
    reason: str
    status: str
    timestamp: str

# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/")
def root():
    return {
        "status": "online",
        "service": "SIRI-AI Payouts Engine",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/health")
def health():
    return {"status": "healthy"}

# ============================================================
# OUTGROWERS
# ============================================================

@app.post("/outgrowers")
def create_outgrower(outgrower: Outgrower):
    if outgrower.outgrower_id in outgrowers:
        raise HTTPException(status_code=400, detail="Outgrower already exists")
    outgrowers[outgrower.outgrower_id] = outgrower.dict()
    return {"message": "Outgrower created", "outgrower": outgrower}

@app.get("/outgrowers")
def list_outgrowers():
    return {"count": len(outgrowers), "outgrowers": list(outgrowers.values())}

@app.get("/outgrowers/{outgrower_id}")
def get_outgrower(outgrower_id: str):
    if outgrower_id not in outgrowers:
        raise HTTPException(status_code=404, detail="Outgrower not found")
    return outgrowers[outgrower_id]

# ============================================================
# TELEMETRY
# ============================================================

@app.post("/telemetry")
def add_telemetry(record: TelemetryRecord):
    if record.outgrower_id not in outgrowers:
        raise HTTPException(status_code=404, detail="Outgrower not found")
    telemetry.append(record.dict())
    return {"message": "Telemetry recorded", "record": record}

@app.get("/telemetry/{outgrower_id}")
def get_telemetry(outgrower_id: str):
    records = [t for t in telemetry if t["outgrower_id"] == outgrower_id]
    return {"count": len(records), "records": records}

# ============================================================
# PAYOUTS
# ============================================================

@app.post("/payouts/quick", response_model=PayoutResponse)
def quick_payout(request: PayoutRequest):
    if request.outgrower_id not in outgrowers:
        raise HTTPException(status_code=404, detail="Outgrower not found")

    payout_id = str(uuid.uuid4())
    payout = {
        "payout_id": payout_id,
        "outgrower_id": request.outgrower_id,
        "amount": request.amount,
        "currency": request.currency,
        "reason": request.reason,
        "status": "completed",
        "timestamp": datetime.utcnow().isoformat()
    }
    payouts.append(payout)
    return payout

@app.post("/payouts/auto/{outgrower_id}", response_model=PayoutResponse)
def auto_payout(outgrower_id: str):
    """Auto-pay from telemetry data"""
    if outgrower_id not in outgrowers:
        raise HTTPException(status_code=404, detail="Outgrower not found")

    # Calculate from telemetry
    records = [t for t in telemetry if t["outgrower_id"] == outgrower_id]
    tonnes = sum(r["tonnes_delivered"] for r in records)
    rate_per_tonne = 150.0
    amount = tonnes * rate_per_tonne

    if amount == 0:
        amount = 300.0  # Default mock payment for testing

    payout_id = str(uuid.uuid4())
    payout = {
        "payout_id": payout_id,
        "outgrower_id": outgrower_id,
        "amount": amount,
        "currency": "Pi",
        "reason": f"Auto-pay from telemetry: {tonnes} tonnes",
        "status": "completed",
        "timestamp": datetime.utcnow().isoformat()
    }
    payouts.append(payout)
    return payout

@app.get("/payouts")
def list_payouts():
    return {"count": len(payouts), "payouts": payouts}

@app.get("/payouts/{outgrower_id}")
def get_outgrower_payouts(outgrower_id: str):
    user_payouts = [p for p in payouts if p["outgrower_id"] == outgrower_id]
    return {"count": len(user_payouts), "payouts": user_payouts}

# ============================================================
# REPORTS
# ============================================================

@app.get("/reports/monthly")
def monthly_report():
    total_paid = sum(p["amount"] for p in payouts)
    return {
        "month": datetime.utcnow().strftime("%B %Y"),
        "total_payouts": len(payouts),
        "total_amount": total_paid,
        "unique_outgrowers": len(set(p["outgrower_id"] for p in payouts))
    }

# ============================================================
# SEED DATA (for testing)
# ============================================================

@app.post("/seed")
def seed_data():
    """Create sample outgrowers and telemetry for testing"""
    sample_outgrowers = [
        {"outgrower_id": "OUT_00042", "name": "Sipho Dlamini", "phone": "+268 7612 3456", "location": "Ka-Mbhoke", "wallet_pi": "pi_sipho", "wallet_usdc": None},
        {"outgrower_id": "OUT_00043", "name": "Thandi Nkambule", "phone": "+268 7645 6789", "location": "Kubuta", "wallet_pi": "pi_thandi", "wallet_usdc": None},
        {"outgrower_id": "OUT_00044", "name": "Bongani Mamba", "phone": "+268 7689 0123", "location": "Ntuthuko", "wallet_pi": None, "wallet_usdc": "usdc_bongani"},
    ]
    for o in sample_outgrowers:
        outgrowers[o["outgrower_id"]] = o

    sample_telemetry = [
        {"outgrower_id": "OUT_00042", "tonnes_delivered": 2.0, "crop_type": "maize", "date": "2027-04-15"},
        {"outgrower_id": "OUT_00042", "tonnes_delivered": 1.5, "crop_type": "sorghum", "date": "2027-04-22"},
        {"outgrower_id": "OUT_00043", "tonnes_delivered": 3.0, "crop_type": "maize", "date": "2027-04-18"},
    ]
    for t in sample_telemetry:
        telemetry.append(t)

    return {
        "message": "Seed data created",
        "outgrowers": len(outgrowers),
        "telemetry_records": len(telemetry)
}
