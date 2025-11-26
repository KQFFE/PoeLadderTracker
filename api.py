import configparser
import requests
import time
from urllib.parse import quote

class GGGAPIClient:
    _instance = None
    
    TOKEN_URL = "https://www.pathofexile.com/oauth/token"
    API_BASE_URL = "https://api.pathofexile.com"
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(GGGAPIClient, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        
        config = configparser.ConfigParser()
        config.read('config.ini')

        self.client_id = config.get('GGG_API', 'client_id', fallback='poeladdertracker')
        self.client_secret = config.get('GGG_API', 'client_secret', fallback=None)
        self.contact_email = config.get('GGG_API', 'contact', fallback='dev@example.com')
        
        self.access_token = None
        self.token_expiry = 0
        
        self._initialized = True

    def _get_access_token(self):
        """Fetches a new access token from the GGG API."""
        if self.access_token and time.time() < self.token_expiry:
            return self.access_token

        print("🔄 Requesting new access token...")
        
        if not self.client_id or not self.client_secret:
            print("❌ Client ID or Client Secret not configured in config.ini")
            return None

        headers = {
            "User-Agent": f"OAuth2.0-Client/{self.client_id} ({self.contact_email})",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        # The key fix is here: scopes must be space-separated.
        payload = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "client_credentials",
            "scope": "service:leagues service:leagues:ladder" 
        }

        try:
            response = requests.post(self.TOKEN_URL, headers=headers, data=payload)
            response.raise_for_status()
            token_data = response.json()
            # Handle cases where 'expires_in' might not be in the response
            expires_in = token_data.get('expires_in') or 3600 # Default to 1 hour if not provided
            self.access_token = token_data['access_token']
            self.token_expiry = time.time() + expires_in - 60  # 60s buffer
            print("✅ Access token obtained successfully.")
            return self.access_token
        except requests.exceptions.RequestException as e:
            print(f"❌ Error fetching access token: {e}")
            if e.response:
                print(f"    Response: {e.response.text}")
            return None

    def _make_request(self, endpoint_or_url, use_new_base=True, authenticated=True):
        """Makes an authenticated request to the GGG API."""
        headers = {
            "User-Agent": f"OAuth2.0-Client/{self.client_id} ({self.contact_email})"
        }

        if authenticated:
            token = self._get_access_token()
            if not token:
                return None
            headers["Authorization"] = f"Bearer {token}"
        else:
            # The old /api/ladders endpoint does not use bearer token authentication
            pass

        url = endpoint_or_url
        if use_new_base:
            url = f"{self.API_BASE_URL}/{endpoint_or_url}"

        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"❌ Error fetching data from {url}: {e}")
            return None

    @classmethod
    def fetch_leagues(cls):
        """Fetches a list of all leagues."""
        return cls()._make_request("leagues", authenticated=True)

    @classmethod
    def fetch_ladder(cls, league_id, limit=200, offset=0):
        """Fetches a chunk of the ladder for a given league."""
        # URL-encode the league_id to handle spaces and special characters
        # The quote function can be too aggressive. A simple space replacement is safer.
        encoded_league_id = league_id.replace(' ', '%20')
        # The ladder endpoint is on the old base URL, not the new api.pathofexile.com
        url = f"https://www.pathofexile.com/api/ladders/{encoded_league_id}?limit={limit}&offset={offset}"
        return cls()._make_request(url, use_new_base=False, authenticated=False)
