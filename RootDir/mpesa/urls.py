pythonfrom django.urls import path
from .views import STKPushView, MpesaCallbackView

app_name = "mpesa"

urlpatterns = [
    path("stk-push/", STKPushView.as_view(), name="stk-push"),
    path("callback/", MpesaCallbackView.as_view(), name="callback"),
]

Step 8 — myproject/urls.py
pythonfrom django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path("mpesa/", include("mpesa.urls", namespace="mpesa")),
]

Step 9 — Expose the callback publicly (sandbox testing)
Safaricom must reach your callback URL. Use ngrok locally:
bashpip install ngrok
ngrok http 8000
Copy the HTTPS URL (e.g. https://abc123.ngrok.io) and update .env:
envMPESA_CALLBACK_URL=https://abc123.ngrok.io/mpesa/callback/

Step 10 — Test the STK push
bashcurl -X POST http://localhost:8000/mpesa/stk-push/ \
  -H "Content-Type: application/json" \
  -d '{
    "phone_number": "254712345678",
    "amount": 1,
    "reference": "TestRef001",
    "description": "Demo Payment"
  }'
Expected response:
json{
  "message": "STK push sent. Check your phone.",
  "CheckoutRequestID": "ws_CO_...",
  "MerchantRequestID": "29115-..."
}
The sandbox test number must be a registered sandbox test number from developer.safaricom.co.ke → Test Credentials.
