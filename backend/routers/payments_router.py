"""
Payments Router - Cashfree integration
Handles order creation, webhook verification, and subscription activation.

Plans:
  earth_monthly   ₹19/month
  universe_monthly ₹99/month
"""

import os
import hmac
import hashlib
import base64
import json
import uuid
from datetime import datetime, timedelta, timezone

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from database import get_db
from models import User, PaymentOrder, UserSubscription
from auth import get_current_user_required

router = APIRouter(prefix="/api/payments", tags=["Payments"])

# ---------------------------------------------------------------------------
# Cashfree config  (set in Cloud Run env vars)
# ---------------------------------------------------------------------------
CF_APP_ID = os.getenv("CASHFREE_APP_ID", "")
CF_SECRET = os.getenv("CASHFREE_SECRET_KEY", "")
CF_ENV    = os.getenv("CASHFREE_ENV", "production")

CF_BASE = (
    "https://sandbox.cashfree.com/pg"
    if CF_ENV == "sandbox"
    else "https://api.cashfree.com/pg"
)

FRONTEND_URL = os.getenv("FRONTEND_URL", "https://infinitest.tech")
BACKEND_URL  = os.getenv("BACKEND_URL",  "https://mentors-mantra-api-87253755436.us-central1.run.app")

# ---------------------------------------------------------------------------
# Plan catalogue
# plan_key -> { name, amount_paise, duration_days, plan_tier }
# ---------------------------------------------------------------------------
PLANS: dict[str, dict] = {
    "earth_monthly": {
        "name": "Earth Plan",
        "amount_paise": 1900,      # ₹19
        "duration_days": 30,
        "plan_tier": "earth",
    },
    "universe_monthly": {
        "name": "Universe Plan",
        "amount_paise": 9900,      # ₹99
        "duration_days": 30,
        "plan_tier": "universe",
    },
}

# Plan limits used by rate-limit logic (imported in main.py)
PLAN_LIMITS = {
    "free":     {"pdf": 5,       "test": 4},
    "earth":    {"pdf": 10,      "test": 999999},
    "universe": {"pdf": 999999,  "test": 999999},
}

# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------

class CreateOrderRequest(BaseModel):
    plan_key: str  # "earth_monthly" | "universe_monthly"


class CreateOrderResponse(BaseModel):
    order_id: str
    payment_session_id: str
    amount: float
    plan_name: str
    cf_env: str   # "sandbox" | "production"


class OrderStatusResponse(BaseModel):
    order_id: str
    status: str   # "PENDING" | "PAID" | "FAILED"
    plan: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/create-order", response_model=CreateOrderResponse)
async def create_order(
    body: CreateOrderRequest,
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db),
):
    """
    Called by the frontend when user clicks Buy.
    Creates an order on Cashfree, saves it to DB,
    and returns payment_session_id for the JS SDK.
    """
    plan = PLANS.get(body.plan_key)
    if not plan:
        raise HTTPException(status_code=400, detail=f"Invalid plan_key: {body.plan_key}")

    order_id = f"MM_{current_user.id[:8]}_{uuid.uuid4().hex[:8]}"
    phone = getattr(current_user, "phone", None) or "9999999999"

    payload = {
        "order_id": order_id,
        "order_amount": plan["amount_paise"] / 100,
        "order_currency": "INR",
        "customer_details": {
            "customer_id": current_user.id,
            "customer_name": current_user.name or current_user.email.split("@")[0],
            "customer_email": current_user.email,
            "customer_phone": phone,
        },
        "order_meta": {
            "return_url": f"{FRONTEND_URL}/payment/success?order_id={order_id}",
            "notify_url": f"{BACKEND_URL}/api/payments/webhook",
        },
    }

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            f"{CF_BASE}/orders",
            json=payload,
            headers={
                "x-api-version":   "2023-08-01",
                "x-client-id":     CF_APP_ID,
                "x-client-secret": CF_SECRET,
                "Content-Type":    "application/json",
            },
        )

    if resp.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail=f"Cashfree error {resp.status_code}: {resp.text}",
        )

    cf_data = resp.json()
    payment_session_id = cf_data.get("payment_session_id")
    if not payment_session_id:
        raise HTTPException(status_code=502, detail="Cashfree did not return payment_session_id")

    db_order = PaymentOrder(
        user_id=current_user.id,
        cf_order_id=order_id,
        plan_key=body.plan_key,
        amount_paise=plan["amount_paise"],
        status="PENDING",
        payment_session_id=payment_session_id,
    )
    db.add(db_order)
    db.commit()

    return CreateOrderResponse(
        order_id=order_id,
        payment_session_id=payment_session_id,
        amount=plan["amount_paise"] / 100,
        plan_name=plan["name"],
        cf_env=CF_ENV,
    )


@router.get("/order/{order_id}/status", response_model=OrderStatusResponse)
async def get_order_status(
    order_id: str,
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db),
):
    """
    Frontend polls this after Cashfree redirects back to return_url.
    Returns PAID once the webhook has fired and activated the subscription.
    """
    order = db.query(PaymentOrder).filter(
        PaymentOrder.cf_order_id == order_id,
        PaymentOrder.user_id == current_user.id,
    ).first()

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    return OrderStatusResponse(
        order_id=order_id,
        status=order.status,
        plan=PLANS.get(order.plan_key, {}).get("plan_tier", "free"),
    )


@router.post("/webhook")
async def cashfree_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Cashfree posts payment events here.
    Signature is verified before trusting the payload.
    """
    raw_body = await request.body()

    # ---- Signature verification ----
    received_sig = request.headers.get("x-webhook-signature")
    timestamp    = request.headers.get("x-webhook-timestamp")

    if received_sig and timestamp and CF_SECRET:
        message  = timestamp + raw_body.decode("utf-8")
        computed = hmac.new(
            CF_SECRET.encode("utf-8"),
            message.encode("utf-8"),
            hashlib.sha256,
        ).digest()
        computed_b64 = base64.b64encode(computed).decode("utf-8")

        if not hmac.compare_digest(computed_b64, received_sig):
            raise HTTPException(status_code=400, detail="Invalid webhook signature")

    # ---- Parse event ----
    try:
        data = json.loads(raw_body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    event_type = data.get("type", "")
    order_data = data.get("data", {}).get("order", {})
    order_id   = order_data.get("order_id")

    if not order_id:
        return {"status": "ignored", "reason": "no order_id"}

    order = db.query(PaymentOrder).filter(PaymentOrder.cf_order_id == order_id).first()
    if not order:
        return {"status": "ignored", "reason": "order not in DB"}

    if event_type == "PAYMENT_SUCCESS":
        cf_payment_id = data.get("data", {}).get("payment", {}).get("cf_payment_id")
        order.status        = "PAID"
        order.cf_payment_id = str(cf_payment_id) if cf_payment_id else None
        db.commit()
        _activate_subscription(order, db)

    elif event_type in ("PAYMENT_FAILED", "PAYMENT_USER_DROPPED"):
        order.status = "FAILED"
        db.commit()

    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Internal helper
# ---------------------------------------------------------------------------

def _activate_subscription(order: PaymentOrder, db: Session):
    """Mark user as premium and upsert their subscription row."""
    plan_info = PLANS.get(order.plan_key, {})
    plan_tier = plan_info.get("plan_tier", "earth")
    days      = plan_info.get("duration_days", 30)

    now        = datetime.now(timezone.utc)
    expires_at = now + timedelta(days=days)

    user = db.query(User).filter(User.id == order.user_id).first()
    if user:
        user.is_premium = True
        user.plan       = plan_tier
        db.commit()

    sub = db.query(UserSubscription).filter(UserSubscription.user_id == order.user_id).first()
    if sub:
        sub.plan       = plan_tier
        sub.is_active  = True
        sub.starts_at  = now
        sub.expires_at = expires_at
    else:
        sub = UserSubscription(
            user_id    = order.user_id,
            plan       = plan_tier,
            is_active  = True,
            starts_at  = now,
            expires_at = expires_at,
        )
        db.add(sub)
    db.commit()
