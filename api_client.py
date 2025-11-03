import requests
import time
import configparser
from urllib.parse import quote

# --- Configuration and Constants ---
BASE_URL = "https://www.pathofexile.com/api/"
TOKEN_URL = "https://www.pathofexile.com/oauth/token"
LEAGUES_URL = f"{BASE_URL}leagues"
LADDER_URL_TEMPLATE = f"{BASE_URL}ladders/{{league_id}}"

CHUNK_SIZE = 200
USER_AGENT = 'OAuth PoeLadderTracker/1.0 (contact: kqffe.github@gmail.com) - a project by KQFFE'

# --- Globals for Authentication ---
access_token = None
headers = {
    "User-Agent": USER_AGENT,
}

def get_access_token():
    """
    Fetches an access token using the Client Credentials grant type.
    """
    global access_token, headers

    config = configparser.ConfigParser()
    if not config.read('config.ini'):
        print("❌ FATAL: config.ini not found. Please create it with your GGG API credentials.")
        return False

    try:
        client_id = config['GGG_API']['client_id']
        client_secret = config['GGG_API']['client_secret']
    except KeyError:
        print("❌ FATAL: client_id or client_secret not found in config.ini.")
        return False

    if 'YOUR_CLIENT_ID' in client_id or 'YOUR_CLIENT_SECRET' in client_secret:
        print("❌ FATAL: Please replace placeholder credentials in config.ini with your actual GGG API credentials.")
        return False

    payload = {
        'client_id': client_id,
        'client_secret': client_secret,
        'grant_type': 'client_credentials',
        'scope': 'service:leagues service:leagues:ladder'
    }
    
    try:
        print("🔄 Requesting new access token...")
        response = requests.post(TOKEN_URL, data=payload, headers={"User-Agent": USER_AGENT})
        response.raise_for_status()
        token_data = response.json()
        
        access_token = token_data['access_token']
        headers['Authorization'] = f"Bearer {access_token}"
        
        print("✅ Access token obtained successfully.")
        return True
    except requests.exceptions.RequestException as e:
        print(f"❌ FATAL: Error obtaining access token: {e}")
        if e.response:
            print(f"Response content: {e.response.text}")
        return False

def _make_request(url):
    """
    Makes a request to the specified URL, handling token refresh if necessary.
    """
    if not access_token:
        if not get_access_token():
            return None # Stop if we can't get a token

    while True:
        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 429: # Rate limit
                retry_after = int(response.headers.get('Retry-After', 5))
                print(f"⚠️ Rate limit hit. Waiting for {retry_after} seconds...")
                time.sleep(retry_after + 1)
                continue
            
            response.raise_for_status()
            return response.json()

        except requests.exceptions.HTTPError as e:
            if e.response.status_code in (401, 403): # Unauthorized or Forbidden
                print("🔑 Access token expired or invalid. Fetching a new one.")
                if not get_access_token():
                    return None # Stop if we can't get a new token
                # Loop will retry the request with the new token
            else:
                print(f"❌ HTTP Error fetching data: {e}")
                return None
        except requests.exceptions.RequestException as e:
            print(f"❌ Network/Connection Error: {e}. Retrying in 5 seconds...")
            time.sleep(5)
            continue

def fetch_leagues():
    """
    Fetches a list of all available leagues from the PoE API.
    """
    data = _make_request(LEAGUES_URL)
    if data:
        return [league['id'] for league in data]
    return []

def fetch_ladder_chunk(league_id, offset):
    """
    Fetches a single chunk of ladder data from the API for a specific league.
    """
    encoded_league_id = quote(league_id)
    url = f"{LADDER_URL_TEMPLATE.format(league_id=encoded_league_id)}?limit={CHUNK_SIZE}&offset={offset}"
    
    data = _make_request(url)
    
    if data and 'entries' in data:
        return data['entries']
    elif data: # Handle cases where the response might just be a list
        return data
    
    print("❌ JSON structure unexpected or request failed.")
    return None
