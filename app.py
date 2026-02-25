from tkinter import Tk, filedialog
import shutil
from flask import Flask, render_template, request
from skybox_generator import generate_skybox
import os

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def save_zip_dialog(zip_path):
    root = Tk()
    root.withdraw()

    save_path = filedialog.asksaveasfilename(
        defaultextension=".zip",
        filetypes=[("Zip file", "*.zip")],
        initialfile="skybox_pack.zip"
    )

    if save_path:
        shutil.copy(zip_path, save_path)

    root.destroy()


@app.route("/")
def index():
    return render_template("index.html")

@app.route("/upload", methods=["POST"])
def upload():

    uploaded_file = request.files.get("image")

    if not uploaded_file:
        return {"success": False}, 400

    temp_path = os.path.join(BASE_DIR, "pano.jpg")
    uploaded_file.save(temp_path)

    zip_path = generate_skybox(temp_path)


    save_zip_dialog(zip_path)

    return {"success": True}


if __name__ == "__main__":
    app.run(debug=False, use_reloader=False)