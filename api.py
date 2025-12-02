import requests

# The proxy server will handle authentication and API keys.
# The client application only needs to know the proxy's address.
# For local testing, this will be http://127.0.0.1:5000
# When you deploy your proxy, change this to your server's public URL.
PROXY_BASE_URL = "https://poeladdertracker.fly.dev"

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
    def fetch_ladder(cls, league_id, limit=200, offset=0):
        """Fetches a chunk of the ladder for a given league."""
        # The proxy handles URL encoding and correct GGG endpoint.
        # We pass the raw league_id; Flask and requests will handle encoding.
        endpoint = f"ladder/{league_id}?limit={limit}&offset={offset}"
        return cls._make_request(endpoint)
