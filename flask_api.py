from flask import Flask, request, jsonify
import os
import time
import base64
from werkzeug.utils import secure_filename

app = Flask(__name__)
UPLOAD_FOLDER = "uploads"
PROCESSED_FOLDER = os.path.expanduser("~/Desktop/processed")  # Masaüstünde processed dizini
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PROCESSED_FOLDER, exist_ok=True)

def wait_for_processed_file(filename, timeout=60):
    """processed klasöründe aynı isimli dosya var mı, timeout kadar bekle"""
    processed_path = os.path.join(PROCESSED_FOLDER, filename)
    start_time = time.time()
    while time.time() - start_time < timeout:
        if os.path.exists(processed_path):
            return processed_path
        time.sleep(1)  # Her saniye kontrol et
    return None

@app.route("/upload", methods=["POST"])
def upload_image():
    if "file" not in request.files:
        return jsonify({"error": "file alanı eksik"}), 400

    file = request.files["file"]
    filename = secure_filename(file.filename)
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    file.save(filepath)

    # --- processed klasörünü bekle ---
    processed_file = wait_for_processed_file(filename, timeout=60)
    if not processed_file:
        return jsonify({"error": "İşlenmiş dosya zamanında oluşmadı!"}), 504  # Gateway Timeout

    # İşlenmiş dosyayı base64'e çevir ve gönder
    with open(processed_file, "rb") as imgf:
        img_bytes = imgf.read()
        img_base64 = base64.b64encode(img_bytes).decode("utf-8")

    # Hata değeri döndürmek için (örneğin dosya ismindeki hata kodu, veya dosya içine gömülü değer olabilir)
    error_value = 0  # İsterseniz işleyici kod işlenmiş dosya ismine hata ekleyip (capture_52_err3.jpg gibi) buradan çıkarabilirsiniz.

    return jsonify({
        "image_base64": img_base64,
        "error_value": error_value
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
