import os
import requests
import time
from flask import Flask, jsonify, request, render_template, send_from_directory
from dotenv import load_dotenv
from urllib.parse import urlencode

# Load environment variables from a .env file if it exists.
# This should be called before accessing any environment variables.
load_dotenv()
 
# --- Configuration ---
# For a real server, set these as environment variables for security.
# For local testing, you can replace the "your_..." values directly.
CLIENT_ID = os.environ.get("GGG_CLIENT_ID", "your_client_id_here")
CLIENT_SECRET = os.environ.get("GGG_CLIENT_SECRET", "your_client_secret_here")
CONTACT_EMAIL = os.environ.get("GGG_CONTACT_EMAIL", "your.email@example.com")

# --- GGG API Details ---
TOKEN_URL = "https://www.pathofexile.com/oauth/token"
API_BASE_URL = "https://api.pathofexile.com"

# --- In-memory Token Cache ---
# We will cache tokens separately for each scope, as GGG's API
# seems to require different tokens for different services.
token_cache = {}

app = Flask(__name__)

# --- Web App Routes ---

@app.route('/')
def index():
    """Serves the main HTML page of the web application."""
    # This assumes you have an 'index.html' in a 'templates' folder.
    return render_template('index.html')

@app.route('/static/<path:path>')
def send_static(path):
    """Serves static files like CSS and JavaScript."""
    # This assumes you have your css/js in a 'static' folder.
    return send_from_directory('static', path)


# --- API Proxy Routes ---

def get_access_token(scope="service:leagues"):
    """Fetches and caches a GGG API access token. Defaults to the primary working scope."""
    cache_entry = token_cache.get(scope, {})
    if cache_entry.get("access_token") and time.time() < cache_entry.get("token_expiry", 0):
        return cache_entry["access_token"]

    print(f"PROXY: Requesting new GGG access token for scope: '{scope}'")
    headers = {
        "User-Agent": f"OAuth2.0-Client/{CLIENT_ID} ({CONTACT_EMAIL})",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    # A standard dictionary payload with a single scope.
    payload = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "client_credentials",
        "scope": scope
    }
    # New log to show exactly what credentials the server is using
    print(f"PROXY: Auth Payload: client_id='{CLIENT_ID}', client_secret='{'*' * len(CLIENT_SECRET)}'")
    
    try:
        # The requests library correctly URL-encodes dictionary data.
        response = requests.post(TOKEN_URL, headers=headers, data=payload)
        response.raise_for_status()
        token_data = response.json()
        
        new_cache_entry = {
            "access_token": token_data['access_token'],
            "token_expiry": 0
        }
        # Handle cases where 'expires_in' might be present but null
        expires_in = token_data.get('expires_in') or 3600
        new_cache_entry["token_expiry"] = time.time() + expires_in - 60
        token_cache[scope] = new_cache_entry
        
        print("PROXY: Access token obtained successfully.")
        return new_cache_entry["access_token"]
    except requests.exceptions.RequestException as e:
        print(f"PROXY: Error fetching access token: {e}")
        if e.response is not None:
            print(f"PROXY: GGG API Response: {e.response.text}")
        return None

@app.route('/leagues', methods=['GET'])
def proxy_leagues():
    """Proxies the request to fetch all leagues."""
    token = get_access_token() # Uses the default working scope
    if not token:
        return jsonify({"error": "Could not authenticate with GGG API"}), 500

    headers = {
        "Authorization": f"Bearer {token}",
        "User-Agent": f"OAuth2.0-Client/{CLIENT_ID} ({CONTACT_EMAIL})"
    }
    try:
        # Implement retry logic for rate limiting
        for attempt in range(3): # Try up to 3 times
            response = requests.get(f"{API_BASE_URL}/leagues", headers=headers)
            if response.status_code == 429:
                # Rate limit exceeded, wait and retry
                retry_after = int(response.headers.get("Retry-After", 5)) # Default to 5s
                print(f"PROXY: Rate limit hit on /leagues. Waiting for {retry_after} seconds...")
                time.sleep(retry_after)
                continue # Go to the next attempt
            
            response.raise_for_status() # Raise an exception for other bad statuses
            return jsonify(response.json()) # Success

        # If all retries fail, return the last error response
        return jsonify({"error": "Rate limit exceeded after multiple retries"}), 429

    except requests.exceptions.RequestException as e:
        print(f"PROXY: Error forwarding request to GGG /leagues: {e}")
        if e.response is not None:
            print(f"PROXY: GGG API Response: {e.response.text}")
        return jsonify({"error": str(e)}), e.response.status_code if e.response else 500

@app.route('/ladder/<path:league_id>', methods=['GET'])
def proxy_ladder(league_id):
    """Proxies the request to fetch ladder data using the authenticated GGG endpoint."""
    token = get_access_token("service:leagues:ladder") # Dedicated token for deep search
    if not token:
        return jsonify({"error": "Could not authenticate with GGG API"}), 500

    limit = request.args.get('limit', 200, type=int)
    offset = request.args.get('offset', 0, type=int)

    # Use the official, authenticated endpoint to access the full ladder.
    url = f"{API_BASE_URL}/ladder/{league_id}?limit={limit}&offset={offset}"
    headers = {
        "Authorization": f"Bearer {token}",
        "User-Agent": f"OAuth2.0-Client/{CLIENT_ID} ({CONTACT_EMAIL})"
    }
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return jsonify(response.json())
    except requests.exceptions.RequestException as e:
        print(f"PROXY: Error forwarding request to GGG /ladder: {e}")
        if e.response is not None:
            print(f"PROXY: GGG API Response: {e.response.text}")
        return jsonify({"error": str(e)}), e.response.status_code if e.response else 500

@app.route('/public-ladder/<path:league_id>', methods=['GET'])
def proxy_public_ladder(league_id):
    """Proxies the request to the public, unauthenticated ladder endpoint."""
    limit = request.args.get('limit', 200, type=int)
    offset = request.args.get('offset', 0, type=int)
    url = f"https://www.pathofexile.com/api/ladders/{league_id}?limit={limit}&offset={offset}"
    headers = {"User-Agent": f"PoeLadderTrackerProxy/1.0 (contact: {CONTACT_EMAIL})"}
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return jsonify(response.json())
    except requests.exceptions.RequestException as e:
        print(f"PROXY: Error forwarding request to public GGG /ladders: {e}")
        if e.response is not None:
            print(f"PROXY: GGG API Response: {e.response.text}")
        return jsonify({"error": str(e)}), e.response.status_code if e.response else 500

if __name__ == '__main__':
    # For production, use a proper WSGI server like Gunicorn or Waitress
    # Example: gunicorn --bind 0.0.0.0:5000 proxy_server:app
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)