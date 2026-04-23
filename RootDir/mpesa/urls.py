from django.urls import path
from .views import STKPushView, MpesaCallbackView

app_name = "mpesa"

urlpatterns = [
    path("stk-push/", STKPushView.as_view(), name="stk-push"),
    path("callback/", MpesaCallbackView.as_view(), name="callback"),
    path("", payment_page, name="payment-page"),
    path("stk-push/", STKPushView.as_view(), name="stk-push"),
    
]
