import os
import logging
from fastapi import FastAPI, Request, Header, HTTPException
from supabase import create_client
from dotenv import load_dotenv
import stripe

# =================================================
# LOAD ENVIRONMENT VARIABLES
# =================================================
load_dotenv()

STRIPE_API_KEY = os.getenv("STRIPE_API_KEY")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

# =================================================
# VALIDATE ENV VARIABLES
# =================================================
missing = [
    name for name, val in [
        ("STRIPE_API_KEY", STRIPE_API_KEY),
        ("STRIPE_WEBHOOK_SECRET", STRIPE_WEBHOOK_SECRET),
        ("SUPABASE_URL", SUPABASE_URL),
        ("SUPABASE_SERVICE_ROLE_KEY", SUPABASE_SERVICE_ROLE_KEY)
    ] if not val
]

if missing:
    raise RuntimeError(f"Missing environment variables: {', '.join(missing)}")

# =================================================
# INITIALIZE STRIPE & SUPABASE
# =================================================
stripe.api_key = STRIPE_API_KEY
supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

# =================================================
# FASTAPI APP
# =================================================
app = FastAPI()
logging.basicConfig(level=logging.INFO)

# =================================================
# STRIPE WEBHOOK ENDPOINT
# =================================================
@app.post("/stripe-webhook")
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(None, alias="Stripe-Signature")
):
    payload = await request.body()

    # Verify Stripe signature
    try:
        event = stripe.Webhook.construct_event(
            payload=payload,
            sig_header=stripe_signature,
            secret=STRIPE_WEBHOOK_SECRET,
        )
    except stripe.error.SignatureVerificationError:
        logging.warning("⚠️ Invalid Stripe signature")
        raise HTTPException(status_code=400, detail="Invalid Stripe signature")
    except ValueError:
        logging.warning("⚠️ Invalid payload")
        raise HTTPException(status_code=400, detail="Invalid payload")

    logging.info(f"✅ Received Stripe event: {event['type']}")

    data = event["data"]["object"]

    # -------------------------
    # Upgrade user to Pro
    # -------------------------
    if event["type"] in ("checkout.session.completed", "invoice.payment_succeeded"):
        email = (data.get("customer_details") or {}).get("email") or data.get("customer_email")
        if email:
            supabase.table("users").update({"tier": "Pro"}).eq("email", email).execute()
            logging.info(f"Upgraded {email} to Pro")

    # -------------------------
    # Downgrade user to Free
    # -------------------------
    if event["type"] in ("customer.subscription.deleted", "invoice.payment_failed"):
        email = data.get("customer_email")
        if email:
            supabase.table("users").update({"tier": "Free"}).eq("email", email).execute()
            logging.info(f"Downgraded {email} to Free")

    return {"status": "ok"}
