__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

import os
from urllib.parse import urlencode


class Constants:
    """
    A class containing useful constants. Extend and override with ``constants_class`` in the config:

    .. code-block:: python

        from amazonorders.conf import AmazonOrdersConfig

        config = AmazonOrdersConfig(data={"constants_class": "my_module.MyConstants"})
    """

    ##########################################################################
    # Region-specific settings
    ##########################################################################

    # Get region from environment variable
    REGION = os.environ.get("AMAZON_REGION", "us").lower()
    
    # Region-specific configurations
    REGION_CONFIGS = {
        "us": {
            "base_url": "https://www.amazon.com",
            "assoc_handle": "usflex",
            "language": "en-US,en;q=0.9",
            "currency_symbol": "$"
        },
        "ca": {
            "base_url": "https://www.amazon.ca",
            "assoc_handle": "caflex", 
            "language": "en-CA,en;q=0.9",
            "currency_symbol": "C$"
        }
    }
    
    # Get region config, default to US if region not supported
    REGION_CONFIG = REGION_CONFIGS.get(REGION, REGION_CONFIGS["us"])

    ##########################################################################
    # General URL
    ##########################################################################

    # Allow AMAZON_BASE_URL to override region's base URL for backward compatibility
    BASE_URL = os.environ.get("AMAZON_BASE_URL") or REGION_CONFIG["base_url"]

    ##########################################################################
    # URLs for AmazonSession
    ##########################################################################

    SIGN_IN_URL = f"{BASE_URL}/ap/signin"
    SIGN_IN_QUERY_PARAMS = {"openid.pape.max_auth_age": "0",
                            "openid.return_to": f"{BASE_URL}/?ref_=nav_custrec_signin",
                            "openid.identity": "http://specs.openid.net/auth/2.0/identifier_select",
                            "openid.assoc_handle": REGION_CONFIG["assoc_handle"],
                            "openid.mode": "checkid_setup",
                            "openid.claimed_id": "http://specs.openid.net/auth/2.0/identifier_select",
                            "openid.ns": "http://specs.openid.net/auth/2.0"}
    SIGN_OUT_URL = f"{BASE_URL}/gp/flex/sign-out.html"

    ##########################################################################
    # URLs for Orders
    ##########################################################################

    ORDER_HISTORY_URL = f"{BASE_URL}/your-orders/orders"
    ORDER_DETAILS_URL = f"{BASE_URL}/gp/your-account/order-details"
    HISTORY_FILTER_QUERY_PARAM = "timeFilter"

    ##########################################################################
    # URLs for Transactions
    ##########################################################################

    TRANSACTION_HISTORY_ROUTE = "/cpe/yourpayments/transactions"
    TRANSACTION_HISTORY_URL = f"{BASE_URL}{TRANSACTION_HISTORY_ROUTE}"

    ##########################################################################
    # Headers
    ##########################################################################

    BASE_HEADERS = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,"
                  "application/signed-exchange;v=b3;q=0.7",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Accept-Language": REGION_CONFIG["language"],
        "Cache-Control": "max-age=0",
        "Dpr": "2",
        "Ect": "4g",
        "Origin": BASE_URL,
        "Host": BASE_URL.strip("https://"),
        "Priority": "u=0, i",
        "Referer": f"{SIGN_IN_URL}?{urlencode(SIGN_IN_QUERY_PARAMS)}",
        "Rtt": "50",
        "Sec-Ch-Dpr": "2",
        "Sec-Ch-Ua": "\"Google Chrome\";v=\"135\", \"Not-A.Brand\";v=\"8\", \"Chromium\";v=\"135\"",
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": "macOS",
        "Sec-Ch-Ua-Platform-Version": "15.3.2",
        "Sec-Ch-Viewport-Width": "1181",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/135.0.0.0 Safari/537.36",
        "Viewport-Width": "1181"
    }

    ##########################################################################
    # Authentication
    ##########################################################################

    COOKIES_SET_WHEN_AUTHENTICATED = ["x-main"]
    JS_ROBOT_TEXT_REGEX = r"[.\s\S]*verify that you're not a robot[.\s\S]*Enable JavaScript[.\s\S]*"

    ##########################################################################
    # Currency
    ##########################################################################

    CURRENCY_SYMBOL = os.environ.get("AMAZON_CURRENCY_SYMBOL", REGION_CONFIG["currency_symbol"])

    def format_currency(self,
                        amount: float) -> str:
        formatted_amt = "{currency_symbol}{amount:,.2f}".format(currency_symbol=self.CURRENCY_SYMBOL,
                                                                amount=abs(amount))
        if round(amount, 2) < 0:
            return f"-{formatted_amt}"
        return formatted_amt
