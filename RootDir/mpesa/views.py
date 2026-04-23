import json
import logging

from django.http import JsonResponse
from django.shortcuts import render
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from .models import MpesaTransaction
from .utils import initiate_stk_push

logger = logging.getLogger(__name__)


def normalize_phone(phone: str) -> str:
    phone = phone.strip().replace(" ", "").replace("-", "")
    if phone.startswith("+"):
        phone = phone[1:]
    if phone.startswith("07") or phone.startswith("01"):
        phone = "254" + phone[1:]
    return phone


def payment_page(request):
    return render(request, "mpesa/payment.html")


class STKPushView(View):
    def post(self, request, *args, **kwargs):
        try:
            body = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)

        phone = body.get("phone_number", "").strip()
        amount = body.get("amount")
        reference = body.get("reference", "DemoPayment")
        description = body.get("description", "STK Demo")

        if not phone or not amount:
            return JsonResponse(
                {"error": "phone_number and amount are required"}, status=400
            )

        try:
            amount = int(amount)
            if amount < 1:
                raise ValueError
        except (ValueError, TypeError):
            return JsonResponse(
                {"error": "amount must be a positive integer"}, status=400
            )

        phone = normalize_phone(phone)
        response = initiate_stk_push(phone, amount, reference, description)

        if "error" in response:
            return JsonResponse({"error": response["error"]}, status=502)

        if response.get("ResponseCode") != "0":
            return JsonResponse(
                {"error": response.get("errorMessage", "STK push rejected by Safaricom")},
                status=400,
            )

        MpesaTransaction.objects.create(
            phone_number=phone,
            amount=amount,
            reference=reference,
            description=description,
            merchant_request_id=response.get("MerchantRequestID", ""),
            checkout_request_id=response.get("CheckoutRequestID", ""),
        )

        return JsonResponse(
            {
                "message": "STK push sent. Check your phone.",
                "CheckoutRequestID": response.get("CheckoutRequestID"),
                "MerchantRequestID": response.get("MerchantRequestID"),
            },
            status=200,
        )


@method_decorator(csrf_exempt, name="dispatch")
class MpesaCallbackView(View):
    def post(self, request, *args, **kwargs):
        try:
            body = json.loads(request.body)
        except json.JSONDecodeError:
            logger.error("Invalid JSON in M-Pesa callback")
            return JsonResponse({"ResultCode": 1, "ResultDesc": "Bad request"})

        try:
            stk_callback = body["Body"]["stkCallback"]
            checkout_request_id = stk_callback["CheckoutRequestID"]
            result_code = str(stk_callback["ResultCode"])
            result_desc = stk_callback.get("ResultDesc", "")

            transaction = MpesaTransaction.objects.get(
                checkout_request_id=checkout_request_id
            )

            transaction.status = (
                MpesaTransaction.Status.SUCCESS
                if result_code == "0"
                else MpesaTransaction.Status.FAILED
            )
            transaction.result_code = result_code
            transaction.result_description = result_desc
            transaction.save(
                update_fields=["status", "result_code", "result_description", "updated_at"]
            )

        except MpesaTransaction.DoesNotExist:
            logger.warning("Callback for unknown CheckoutRequestID")
        except Exception as e:
            logger.error("Error processing M-Pesa callback: %s", e)

        return JsonResponse({"ResultCode": 0, "ResultDesc": "Accepted"})
