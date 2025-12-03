import os
import requests

# The proxy server will handle authentication and API keys.
# It defaults to the deployed server on Fly.io.
# For local testing, you can set an environment variable:
# $env:PROXY_URL="http://127.0.0.1:5000"
PROXY_BASE_URL = os.environ.get("PROXY_URL", "https://poeladdertracker.fly.dev")

class GGGAPIClient:
    @staticmethod
    def _make_request(endpoint):
        """Makes a request to the proxy server."""
        url = f"{PROXY_BASE_URL}/{endpoint}"
        try:
            response = requests.get(url)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"❌ Error fetching data from proxy at {url}: {e}")
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
