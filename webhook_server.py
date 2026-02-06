import os
import stripe
from fastapi import FastAPI, Request, Header, HTTPException
from supabase import create_client
from dotenv import load_dotenv

# ========================================
# Load environment variables from .env
# ========================================
load_dotenv()

# ========================================
# App & Stripe setup
# ========================================
app = FastAPI()

stripe.api_key = os.getenv("STRIPE_API_KEY")
WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")

if not stripe.api_key or not WEBHOOK_SECRET:
    raise RuntimeError("Stripe environment variables not set")

# ========================================
# Supabase client
# ========================================
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
    raise RuntimeError("Supabase environment variables not set")

supabase = create_client(
    SUPABASE_URL,
    SUPABASE_SERVICE_ROLE_KEY,
)

# ========================================
# Stripe Webhook Endpoint
# ========================================
@app.post("/stripe-webhook")
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(None),
):
    payload = await request.body()

    # Verify webhook signature
    try:
        event = stripe.Webhook.construct_event(
            payload,
            stripe_signature,
            WEBHOOK_SECRET,
        )
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid Stripe signature")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")

    # ====================================
    # Subscription activated / payment OK
    # ====================================
    if event["type"] in (
        "checkout.session.completed",
        "invoice.payment_succeeded",
    ):
        data = event["data"]["object"]

        email = (
            data.get("customer_details", {}) or {}
        ).get("email") or data.get("customer_email")

        if email:
            supabase.table("users").update(
                {"tier": "Pro"}
            ).eq("email", email).execute()

    # ====================================
    # Subscription canceled / payment failed
    # ====================================
    if event["type"] in (
        "customer.subscription.deleted",
        "invoice.payment_failed",
    ):
        data = event["data"]["object"]
        email = data.get("customer_email")

        if email:
            supabase.table("users").update(
                {"tier": "Free"}
            ).eq("email", email).execute()

    return {"status": "ok"}
