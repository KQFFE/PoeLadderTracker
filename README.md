# PoeLadderTracker

A simple desktop application for tracking and viewing Path of Exile ladder standings for public and private leagues.

## Features

- Fetches and displays ladder data for any public league.
- **Supports private leagues** by allowing users to enter the league's exact name.
- Filters the ladder to show the top characters for a specific Ascendancy.
- Searches the entire ladder for a specific character to find their global and ascendancy rank.
- "Show More" functionality to progressively load more characters for a selected ascendancy.

## Setup

1.  **Prerequisites**: Ensure you have Python 3 installed.

2.  **Clone the repository**:
    ```bash
    git clone <your-repository-url>
    cd PoeLadderTracker
    ```

3.  **Install dependencies**:
    ```bash
    pip install customtkinter requests
    ```

4.  **Create `config.ini`**:
    You must create a `config.ini` file in the root directory of the project. This file stores your GGG API credentials.

    *   Go to your Path of Exile account page.
    *   Create a new application.
        *   **Application Name**: `PoeLadderTracker` (or anything you prefer).
        *   **Redirect URL**: `http://localhost/` (this is required but not used by the app).
        *   **Description**: A brief description.
    *   Once created, you will get a `Client ID` and a `Client Secret`.

    Now, create the `config.ini` file with the following content, replacing the placeholder values with your credentials:

    ```ini
    [GGG_API]
    client_id = YOUR_CLIENT_ID
    client_secret = YOUR_CLIENT_SECRET
    contact = your.email@example.com
    ```

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