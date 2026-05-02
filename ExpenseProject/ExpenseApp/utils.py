import ssl
import json
import urllib.request
from decimal import Decimal

def get_exchange_rate(from_curr, to_curr):
    """
    Fetches the current exchange rate using exchangerate-api.com.
    Returns the rate as a Decimal. If it fails, falls back to 1.0 to prevent hard blocking.
    """
    if not from_curr or not to_curr or from_curr.upper() == to_curr.upper():
        return Decimal('1.0')
    
    from_curr = from_curr.upper()
    to_curr = to_curr.upper()
    
    url = f"https://api.exchangerate-api.com/v4/latest/{from_curr}"
    
    try:
        context = ssl._create_unverified_context()
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, context=context, timeout=5) as response:
            data = json.loads(response.read().decode())
            rates = data.get('rates', {})
            rate = rates.get(to_curr)
            if rate:
                return Decimal(str(rate))
    except Exception as e:
        print(f"[ERROR] Failed to fetch exchange rate for {from_curr}->{to_curr}: {e}")
    
    # Fallback if API fails (could also raise an error depending on strictness)
    return Decimal('1.0')
