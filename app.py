import os
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import yt_dlp

app = Flask(__name__)
CORS(app)

TMP_DIR = "/tmp/downloads"
os.makedirs(TMP_DIR, exist_ok=True)

QUALITY_CONFIG = {
    "high": {"bitrate": "320", "rate": "48000"},
    "medium": {"bitrate": "192", "rate": "44100"},
    "low": {"bitrate": "96", "rate": "32000"}
}

@app.route("/", methods=["GET"])
def health():
    return jsonify({"status": "running"}), 200

@app.route("/api/download", methods=["POST"])
def download_audio():
    data = request.get_json() or {}
    url = data.get("url", "").strip()
    quality = data.get("quality", "high").lower()

    if not url:
        return jsonify({"error": "YouTube URL is required."}), 400

    config = QUALITY_CONFIG.get(quality, QUALITY_CONFIG["high"])
    output_template = os.path.join(TMP_DIR, "%(id)s.%(ext)s")

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": output_template,
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": config["bitrate"],
        }],
        "postprocessor_args": ["-ar", config["rate"]],
        "quiet": True,
        "no_warnings": True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            video_id = info.get("id")
            title = "".join(c for c in info.get("title", "audio") if c.isalnum() or c in (" ", "_", "-")).rstrip()
            mp3_path = os.path.join(TMP_DIR, f"{video_id}.mp3")

            if os.path.exists(mp3_path):
                response = send_file(
                    mp3_path,
                    as_attachment=True,
                    download_name=f"{title}_{quality}.mp3",
                    mimetype="audio/mpeg"
                )
                # Clean up temporary file after sending
                @response.call_on_close
                def cleanup():
                    if os.path.exists(mp3_path):
                        os.remove(mp3_path)
                return response
            return jsonify({"error": "Conversion failed."}), 500
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
