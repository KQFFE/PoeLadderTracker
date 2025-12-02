# PoeLadderTracker

A desktop application for tracking and viewing Path of Exile ladder standings for public and private leagues. This application uses a proxy server to protect API credentials.

## Features

- Fetches and displays ladder data for any public league.
- **Supports private leagues** by allowing users to enter the league's exact name.
- Filters the ladder to show the top characters for a specific Ascendancy.
- Searches the entire ladder for a specific character to find their global and ascendancy rank.
- "Show More" functionality to progressively load more characters for a selected ascendancy.

## How it Works

This project is split into two parts:
1.  **Desktop App (`main.py`)**: The GUI that users interact with. It contains no API keys.
2.  **Proxy Server (`proxy_server.py`)**: A simple web server that you host. It securely stores your GGG API keys and makes requests to the GGG API on behalf of the desktop app.

This design ensures your API credentials are never exposed to end-users.

## Setup for Users

1.  **Prerequisites**: Ensure you have Python 3 installed.

2.  **Install dependencies**:
    ```bash
    pip install customtkinter requests
    ```

3.  **Run the application**:
    Double-click the executable (once created) or run from the command line:
    ```bash
    python main.py
    ```
    *No API key configuration is needed for end-users.*

## Setup for the Developer (Hosting the Proxy)

1.  **Get GGG API Credentials**: If you haven't already, create an application on your Path of Exile account page to get a `Client ID` and `Client Secret`.

2.  **Configure the Proxy**: Open `proxy_server.py` and replace the placeholder values for `CLIENT_ID`, `CLIENT_SECRET`, and `CONTACT_EMAIL` with your actual credentials. For a production environment, it is strongly recommended to set these as environment variables instead of hardcoding them.

3.  **Install Proxy Dependencies**:
    ```bash
    pip install Flask requests
    ```

4.  **Run the Proxy Server**:
    ```bash
    python proxy_server.py
    ```
    This will start the proxy on `http://127.0.0.1:5000`. For public access, you will need to deploy this to a hosting service (like Heroku, DigitalOcean, etc.) and update the `PROXY_BASE_URL` in `api.py` to your public server's URL.

## How to Use

1.  Run the application:
    ```bash
    python main.py
    ```

### Fetching Public Leagues

- The application will automatically load all current public leagues into the "Ladder" dropdown.
- Select the desired league and an ascendancy (or "All").
- Click **Fetch Characters**.

### Fetching Private Leagues

- To fetch a private league ladder, check the **Use Private League** checkbox.
- This will disable the public league dropdown and enable the text input field.
- Enter the **exact name** of your private league (e.g., `My Awesome League (PL12345)`).
- Click **Fetch Characters**.
- If the league name is incorrect or the league is empty, an error message will be displayed.

## Disclaimer

This product isn't affiliated with or endorsed by Grinding Gear Games in any way.