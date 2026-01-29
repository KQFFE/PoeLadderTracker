import threading
from gui import App
from proxy_server import app as flask_app

def run_proxy():
    # Start the Flask server on localhost.
    # debug=False and use_reloader=False are required for running in a thread.
    flask_app.run(host='127.0.0.1', port=5000, debug=False, use_reloader=False)

if __name__ == "__main__":
    # Start the proxy server in a daemon thread so it shuts down with the app
    threading.Thread(target=run_proxy, daemon=True).start()

    app = App()
    app.mainloop()
