# core/mpesa.py
import requests
import base64
from datetime import datetime
from django.conf import settings


class MpesaClient:
    @staticmethod
    def get_access_token():
        #Generates a transient bearer access token valid for 3600 seconds.
        auth_string = f"{settings.MPESA_CONSUMER_KEY}:{settings.MPESA_CONSUMER_SECRET}"
        encoded_auth = base64.b64encode(auth_string.encode()).decode("utf-8")
        headers = {"Authorization": f"Basic {encoded_auth}"}

        try:
            res = requests.get(settings.MPESA_AUTH_URL, headers=headers, timeout=15)
            if res.status_code == 200:
                return res.json().get("access_token")
        except requests.exceptions.RequestException as e:
            print(f"Mpesa Token Generation Failed: {e}")
        return None

    @staticmethod
    def format_phone_number(phone):
        """Converts local formats (0712..., 0112..., +254...) to standard 254712..."""
        clean_phone = str(phone).strip().replace("+", "").replace(" ", "")
        if clean_phone.startswith("0"):
            return "254" + clean_phone[1:]
        elif clean_phone.startswith("254"):
            return clean_phone
        return clean_phone

    @classmethod
    def initiate_stk_push(cls, phone_number, amount, order_id, account_reference="Medroute"):
        """Sends an STK push popup directly to the client's phone."""
        access_token = cls.get_access_token()
        if not access_token:
            return False, "Failed to authenticate with Daraja Gateway."

        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        password_str = f"{settings.MPESA_SHORTCODE}{settings.MPESA_PASSKEY}{timestamp}"
        password = base64.b64encode(password_str.encode()).decode("utf-8")

        formatted_phone = cls.format_phone_number(phone_number)
        callback_url = f"{settings.MPESA_CALLBACK_BASE_URL}/api/v1/mpesa/callback/"

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

        # Safaricom requires integers for amounts (no cents)
        int_amount = int(float(amount))

        payload = {
            "BusinessShortCode": settings.MPESA_SHORTCODE,
            "Password": password,
            "Timestamp": timestamp,
            "TransactionType": "CustomerPayBillOnline" if len(settings.MPESA_SHORTCODE) > 5 else "CustomerBuyGoodsOnline",
            "Amount": int_amount,
            "PartyA": formatted_phone,
            "PartyB": settings.MPESA_SHORTCODE,
            "PhoneNumber": formatted_phone,
            "CallBackURL": callback_url,
            "AccountReference": account_reference[:12],
            "TransactionDesc": f"Payment for Order #{str(order_id)[:8]}"
        }

        try:
            res = requests.post(settings.MPESA_STK_URL, json=payload, headers=headers, timeout=30)
            data = res.json()
            if res.status_code == 200 and data.get("ResponseCode") == "0":
                return True, data
            return False, data.get("errorMessage", data.get("ResponseDescription", "STK Initiation Failed"))
        except requests.exceptions.RequestException as e:
            return False, f"Network timeout communicating with Safaricom: {str(e)}"