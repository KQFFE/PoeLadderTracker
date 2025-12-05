# PoeLadderTracker

![PoeLadderTracker Screenshot](https://snipboard.io/w0BXzr.jpg)

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

1.  **Prerequisites**: Ensure you have Python 3 installed. It's recommended to use a virtual environment.
    ```bash
    python -m venv venv
    .\venv\Scripts\Activate.ps1
    ```

2.  **Install dependencies**:
    ```bash
    pip install customtkinter requests
    ```

3.  **Run the application**:
    ```bash
    python main.py
    ```
    *No API key configuration is needed for end-users.*

## Setup for the Developer (Hosting the Proxy)

1.  **Install `flyctl`**: First, install the `fly.io` command-line tool by running the following command in PowerShell:
    ```powershell
    iwr https://fly.io/install.ps1 -useb | iex
    ```
    After installation, **restart your terminal**.

2.  **Get GGG API Credentials**: Create an application on your Path of Exile account page to get a `Client ID` and `Client Secret`.

3.  **Install Proxy Dependencies**:
    ```bash
    pip install Flask gunicorn requests
    ```

4.  **Create `Procfile` and `requirements.txt`**:
    - Create a file named `Procfile` (no extension) with the content: `web: gunicorn --bind 0.0.0.0:$PORT proxy_server:app`
    - In your activated venv, run `pip freeze | Out-File -Encoding utf8 requirements.txt` to create the requirements file.

5.  **Set API Secrets on Fly.io**: Run the following commands in your terminal (outside the venv), replacing the placeholders with your actual GGG API credentials. This keeps your keys secure.
    ```bash
    fly secrets set GGG_CLIENT_ID="your_client_id_here"
    fly secrets set GGG_CLIENT_SECRET="your_client_secret_here"
    fly secrets set GGG_CONTACT_EMAIL="your.email@example.com"
    ```

6.  **Deploy the Proxy Server**:
    ```bash
    fly deploy
    ```
    After deployment, your proxy will be live at `https://poeladdertracker.fly.dev`.

## Usage

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

## Building the Executable (for Developers)

To package the desktop application into a single `.exe` file for distribution on Windows, use PyInstaller.

1.  **Activate the virtual environment**:
    ```powershell
    .\venv\Scripts\Activate.ps1
    ```

2.  **Install PyInstaller**:
    ```bash
    pip install pyinstaller
    ```

3.  **Run the build command**:
    This command bundles the app and all necessary `customtkinter` assets into a single file.
    ```bash
    pyinstaller --name PoeLadderTracker --onefile --windowed --add-data "venv\Lib\site-packages\customtkinter;customtkinter" main.py
    ```

4.  **Find the executable**: The final `PoeLadderTracker.exe` will be located in the `dist` folder.
