import os
import requests
import time
from flask import Flask, jsonify, request
from dotenv import load_dotenv

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
token_cache = {
    "access_token": None,
    "token_expiry": 0
}

app = Flask(__name__)

@app.route('/')
def health_check():
    """A simple health check endpoint to confirm the server is running."""
    return jsonify({"status": "ok", "message": "PoeLadderTracker proxy is running."})

def get_access_token():
    """Fetches and caches a GGG API access token."""
    if token_cache["access_token"] and time.time() < token_cache["token_expiry"]:
        return token_cache["access_token"]

    print("PROXY: Requesting new GGG access token...")
    headers = {
        "User-Agent": f"OAuth2.0-Client/{CLIENT_ID} ({CONTACT_EMAIL})",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    payload = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "client_credentials",
        "scope": "service:leagues" # Correct scope for fetching league list
    }
    # New log to show exactly what credentials the server is using
    print(f"PROXY: Auth Payload: client_id='{payload['client_id']}', client_secret='{'*' * len(payload['client_secret'])}'")
    try:
        response = requests.post(TOKEN_URL, headers=headers, data=payload)
        response.raise_for_status()
        token_data = response.json()
        
        token_cache["access_token"] = token_data['access_token']
        # Handle cases where 'expires_in' might be present but null
        expires_in = token_data.get('expires_in') or 3600
        token_cache["token_expiry"] = time.time() + expires_in - 60
        
        print("PROXY: Access token obtained successfully.")
        return token_cache["access_token"]
    except requests.exceptions.RequestException as e:
        print(f"PROXY: Error fetching access token: {e}")
        if e.response is not None:
            print(f"PROXY: GGG API Response: {e.response.text}")
        return None

@app.route('/leagues', methods=['GET'])
def proxy_leagues():
    """Proxies the request to fetch all leagues."""
    token = get_access_token()
    if not token:
        return jsonify({"error": "Could not authenticate with GGG API"}), 500

    headers = {
        "Authorization": f"Bearer {token}",
        "User-Agent": f"OAuth2.0-Client/{CLIENT_ID} ({CONTACT_EMAIL})"
    }
    try:
        response = requests.get(f"{API_BASE_URL}/leagues", headers=headers)
        response.raise_for_status()
        return jsonify(response.json())
    except requests.exceptions.RequestException as e:
        print(f"PROXY: Error forwarding request to GGG /leagues: {e}")
        if e.response is not None:
            print(f"PROXY: GGG API Response: {e.response.text}")
        return jsonify({"error": str(e)}), e.response.status_code if e.response else 500

@app.route('/ladder/<path:league_id>', methods=['GET'])
def proxy_ladder(league_id):
    """Proxies the request to fetch ladder data. This is a public endpoint."""
    limit = request.args.get('limit', 200)
    offset = request.args.get('offset', 0)
    
    url = f"https://www.pathofexile.com/api/ladders/{league_id}?limit={limit}&offset={offset}"
    headers = {
        "User-Agent": f"OAuth PoeLadderTrackerProxy/1.0 (contact: {CONTACT_EMAIL})"
    }
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return jsonify(response.json())
    except requests.exceptions.RequestException as e:
        return jsonify({"error": str(e)}), e.response.status_code if e.response else 500

if __name__ == '__main__':
    # For production, use a proper WSGI server like Gunicorn or Waitress
    # Example: gunicorn --bind 0.0.0.0:5000 proxy_server:app
    app.run(host='0.0.0.0', port=5000, debug=True)