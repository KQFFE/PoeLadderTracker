import requests

# This is the URL of your local proxy server.
PROXY_BASE_URL = "http://127.0.0.1:5000"

class _GGGAPIClient:
    """
    A client to interact with the local proxy server, which in turn
    communicates with the GGG API. This is implemented as a singleton
    to avoid creating multiple instances.
    """
    def __init__(self):
        self.session = requests.Session()

    def fetch_leagues(self):
        """
        Fetches all public leagues from the local proxy server.
        """
        try:
            # The proxy server exposes a /leagues endpoint
            response = self.session.get(f"{PROXY_BASE_URL}/leagues")
            response.raise_for_status()
            # The proxy server correctly returns a JSON object with a 'result' key
            # based on the GGG API v2 spec.
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"API Client Error: Could not connect to proxy server to fetch leagues: {e}")
            # Try to parse a JSON error from the response body first
            if e.response is not None:
                try:
                    return e.response.json()
                except requests.exceptions.JSONDecodeError:
                    # If body is not JSON, create a generic HTTP error
                    return {"error": "http_error", "message": f"Server returned status {e.response.status_code}"}
            # Handle connection errors specifically
            elif isinstance(e, requests.exceptions.ConnectionError):
                return {"error": "connection_failed", "message": f"Connection to proxy at {PROXY_BASE_URL} failed. Is the internal server running?"}
            # Fallback for other request exceptions
            else:
                return {"error": "request_failed", "message": str(e)}

    def fetch_ladder(self, league_id, limit=200, offset=0, deep_search=False):
        """
        Fetches ladder data from the local proxy server.
        It decides which endpoint to use based on the 'deep_search' flag.
        """
        params = {'limit': limit, 'offset': offset}

        if deep_search:
            # Use the authenticated endpoint for deep searches (beyond rank 15,000)
            # This requires the proxy to have valid OAuth credentials.
            endpoint = f"/ladder/{league_id}"
        else:
            # Use the public, unauthenticated endpoint for standard searches.
            endpoint = f"/public-ladder/{league_id}"

        try:
            response = self.session.get(f"{PROXY_BASE_URL}{endpoint}", params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"API Client Error: Failed to fetch ladder data from proxy: {e}")
            # Try to parse a JSON error from the response body first
            if e.response is not None:
                try:
                    return e.response.json()
                except requests.exceptions.JSONDecodeError:
                    return {"error": "http_error", "message": f"Server returned status {e.response.status_code}"}
            # Handle connection errors specifically
            elif isinstance(e, requests.exceptions.ConnectionError):
                return {"error": "connection_failed", "message": f"Connection to proxy at {PROXY_BASE_URL} failed. Is the internal server running?"}
            # Fallback for other request exceptions
            else:
                return {"error": "request_failed", "message": str(e)}

# Create a single instance of the client to be used throughout the application.
# This is the "singleton" pattern. When other files import GGGAPIClient,
# they will all get this same instance.
GGGAPIClient = _GGGAPIClient()