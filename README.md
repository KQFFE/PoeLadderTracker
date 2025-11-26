# PoE Ladder Tracker

This project is a Python script that fetches and displays Path of Exile ladder information.

<img width="700" height="826" alt="image" src="https://github.com/user-attachments/assets/4727d55d-57f6-4241-9ccc-dcafec8bcf74" />


## Prerequisites

- Python 3.x installed and added to your system's PATH. You can download it from [python.org](https://www.python.org/downloads/).

## Installation

1.  **Clone the repository.**
    ```bash
    git clone https://github.com/KQFFE/PoELadderTracker.git
    cd PoELadderTracker
    ```

2.  **Create and activate a virtual environment.**
    - On Windows:
      ```bash
      python -m venv venv
      venv\Scripts\activate
      ```
    - On macOS and Linux:
      ```bash
      python3 -m venv venv
      source venv/bin/activate
      ```

3.  **Install the required dependencies.**
    ```bash
    pip install -r requirements.txt
    ```

## Configuration

This application requires API credentials from Grinding Gear Games (GGG) to function.

1.  **Register an application with GGG:** Follow the instructions in the [GGG developer documentation](https://www.pathofexile.com/developer/docs/authorization) to register a "Confidential Client". You will receive a `client_id` and a `client_secret`.

2.  **Create the environment file:** In the root of the project, create a new file named `.env`. You can do this by copying the provided example file:
    - On Windows (Command Prompt):
      ```bash
      copy .env.example .env
      ```
    - On macOS and Linux:
      ```bash
      cp .env.example .env
      ```

3.  **Add your credentials:** Open the new `.env` file and replace the placeholder values with the credentials you received from GGG:

    ```
    POE_CLIENT_ID="YOUR_CLIENT_ID"
    POE_CLIENT_SECRET="YOUR_CLIENT_SECRET"
    ```

    **Note:** The `.env` file is included in `.gitignore` and will not be committed to the repository, keeping your credentials safe.

## Running the Application

Once the setup and configuration are complete, you can run the ladder tracker:

```bash
python main.py
```

---

This product isn't affiliated with or endorsed by Grinding Gear Games in any way.
