from flask import Flask, render_template, request, send_file
from skybox_generator import generate_skybox
import os

app = Flask(__name__, static_folder='static', static_url_path='/static')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Guardar el último ZIP generado para descargarlo
last_zip_path = None


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/upload", methods=["POST"])
def upload():
    global last_zip_path
    
    uploaded_file = request.files.get("image")

    if not uploaded_file:
        return {"success": False}, 400

    try:
        # Guardar imagen temporal
        temp_path = os.path.join(BASE_DIR, "pano.jpg")
        uploaded_file.save(temp_path)

        # Generar skybox
        zip_path = generate_skybox(temp_path)
        
        # Guardar el path para descargar después
        last_zip_path = zip_path

        return {"success": True}, 200

    except Exception as e:
        print(f"Error: {e}")
        return {"success": False, "error": str(e)}, 500


@app.route("/download")
def download():
    global last_zip_path
    
    if not last_zip_path or not os.path.exists(last_zip_path):
        return {"error": "No skybox generated"}, 404

    try:
        return send_file(
            last_zip_path,
            as_attachment=True,
            download_name="skybox.zip"
        )
    except Exception as e:
        print(f"Error: {e}")
        return {"error": str(e)}, 500


if __name__ == "__main__":
    app.run(debug=False, use_reloader=False)
