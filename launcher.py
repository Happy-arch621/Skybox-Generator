import threading
import webview
from app import app


def run_flask():
    app.run(port=5000, debug=False, use_reloader=False)


t = threading.Thread(target=run_flask)
t.daemon = True
t.start()

webview.create_window(
    "Skybox Generator",
    "http://127.0.0.1:5000",
    width=1000,
    height=700
)

webview.start()