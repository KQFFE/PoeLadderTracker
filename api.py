import os
import requests
import sys
import certifi

# The proxy server will handle authentication and API keys.
# It defaults to the deployed server on Fly.io.
# For local testing, you can set an environment variable:
# $env:PROXY_URL="http://127.0.0.1:5000"
PROXY_BASE_URL = os.environ.get("PROXY_URL", "https://poeladdertracker.fly.dev")

# --- Debug Flag ---
DEBUG = os.environ.get("APP_DEBUG") == "1"

def get_ssl_cert_path():
    """
    Gets the definitive path to the SSL certificate file.
    - If running as a packaged PyInstaller app, it constructs the path to the
      certificate file bundled by the 'hook-certifi.py' hook.
    - If running as a normal script, it uses the standard certifi path.
    """
    if getattr(sys, 'frozen', False):
        # Path to certs in the temporary _MEIPASS directory of the packaged app
        path = os.path.join(sys._MEIPASS, 'certifi', 'cacert.pem')
        if DEBUG: print(f"DEBUG: Using frozen cert path: {path}")
        return os.path.join(sys._MEIPASS, 'certifi', 'cacert.pem')
    return certifi.where()

class GGGAPIClient:
    @staticmethod
    def _make_request(endpoint):
        """Makes a request to the proxy server."""
        url = f"{PROXY_BASE_URL}/{endpoint}"
        try:
            if DEBUG: print(f"DEBUG: Attempting to fetch from: {url}")
            response = requests.get(url, timeout=15, verify=get_ssl_cert_path())
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"❌ Detailed Error: {type(e).__name__} - {e}")
            return None

    @classmethod
    def fetch_leagues(cls):
        """Fetches a list of all leagues."""
        # No longer needs authentication details, just calls the proxy endpoint
        return cls._make_request("leagues")

    @classmethod
    def fetch_ladder(cls, league_id, limit=200, offset=0, deep_search=False):
        """Fetches a chunk of the ladder for a given league."""
        if deep_search:
            # Use the authenticated endpoint for deep searches (public leagues only)
            endpoint = f"ladder/{league_id}?limit={limit}&offset={offset}"
        else:
            # Use the public endpoint for shallow searches (works with private league names)
            endpoint = f"public-ladder/{league_id}?limit={limit}&offset={offset}"
        return cls._make_request(endpoint)
