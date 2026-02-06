import stripe
from fastapi import FastAPI, Request, Header, HTTPException
from supabase import create_client
import os

app = FastAPI()

stripe.api_key = os.environ["STRIPE_API_KEY"]
WEBHOOK_SECRET = os.environ["STRIPE_WEBHOOK_SECRET"]

supabase = create_client(
    os.environ["SUPABASE_URL"],
    os.environ["SUPABASE_SERVICE_ROLE_KEY"],
)

@app.post("/stripe-webhook")
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(None),
):
    payload = await request.body()

    try:
        event = stripe.Webhook.construct_event(
            payload, stripe_signature, WEBHOOK_SECRET
        )
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    # =============================
    # SUBSCRIPTION CREATED / PAID
    # =============================
    if event["type"] in (
        "checkout.session.completed",
        "invoice.payment_succeeded",
    ):
        session = event["data"]["object"]
        email = session["customer_details"]["email"]

        supabase.table("users").update(
            {"tier": "Pro"}
        ).eq("email", email).execute()

    # =============================
    # SUBSCRIPTION CANCELED
    # =============================
    if event["type"] in (
        "customer.subscription.deleted",
        "invoice.payment_failed",
    ):
        customer = event["data"]["object"]
        email = customer.get("customer_email")

        if email:
            supabase.table("users").update(
                {"tier": "Free"}
            ).eq("email", email).execute()

    return {"status": "ok"}
