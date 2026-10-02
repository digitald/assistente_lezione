"""Server web limitato al PC locale. Nessuna chiave viene inviata al browser."""
import argparse
import io
import os
import secrets
import threading
import webbrowser
from pathlib import Path

from flask import Flask, jsonify, request, send_file

try:
    import config
except ModuleNotFoundError:
    import config_template as config
from lesson_service import LessonService
from local_runtime import LocalRuntime
from app_errors import error_message
from version import __version__

PROJECT = Path(__file__).resolve().parent


def create_app(service=None, demo=False):
    app = Flask(__name__, static_folder="web/static", template_folder="web")
    # Gli asset statici sono letti dal disco a ogni richiesta: anche il template
    # deve aggiornarsi, altrimenti HTML vecchio e JavaScript nuovo si mescolano.
    app.config["TEMPLATES_AUTO_RELOAD"] = True
    app.config["MAX_CONTENT_LENGTH"] = 512 * 1024 * 1024
    app.config["DEMO"] = demo
    token = secrets.token_urlsafe(32)
    if service is None:
        service = LessonService(PROJECT / ("web-demo-data" if demo else "data"), os.getenv("OPENAI_API_KEY") or config.OPENAI_API_KEY,
                                local_runtime=LocalRuntime.from_config(config))
        if not demo:
            service.import_legacy(config.TRANSCRIPTS_DIR, config.NOTES_DIR)
    app.extensions["lessons"] = service

    @app.before_request
    def local_only():
        if request.host.split(":")[0] not in ("localhost", "127.0.0.1"):
            return jsonify(error="Questo pannello è accessibile solo dal PC locale."), 403
        if request.method in ("POST", "PUT", "DELETE", "PATCH"):
            if not secrets.compare_digest(request.headers.get("X-Local-Token", ""), token):
                return jsonify(error="La sessione locale è cambiata. Riprova il salvataggio.",
                               code="local_token_expired"), 403

    @app.after_request
    def response_headers(response):
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; media-src 'self'; frame-ancestors 'none'"
        return response

    @app.errorhandler(Exception)
    def handle_error(exc):
        from werkzeug.exceptions import HTTPException
        if isinstance(exc, HTTPException):
            return jsonify(error="File troppo grande (massimo 512 MB)." if exc.code == 413 else exc.description), exc.code
        if isinstance(exc, KeyError):
            return jsonify(error="Lezione non trovata."), 404
        return jsonify(error=str(exc) if isinstance(exc, ValueError) else error_message(exc)), 400

    def body():
        value = request.get_json(silent=True)
        if not isinstance(value, dict):
            raise ValueError("Dati del comando non validi.")
        return value

    @app.get("/")
    def index():
        from flask import render_template
        return render_template("index.html", version=__version__)

    @app.get("/api/state")
    def state():
        summaries = service.list_summaries()
        return jsonify(version=__version__, token=token, demo=demo, lessons=summaries, runtime=service.status(),
                       api_key_expires_on=getattr(config, "OPENAI_API_KEY_EXPIRES_ON", None))

    @app.get("/api/devices")
    def devices():
        return jsonify(devices=service.devices())

    @app.get("/api/profile")
    def profile():
        return jsonify(service.get_profile())

    @app.post("/api/profile")
    def save_profile():
        return jsonify(service.save_profile(body()))

    @app.post("/api/lessons")
    def create():
        fields = body()
        if demo:
            fields.update(engine="demo", model="demo")
        return jsonify(service.create(fields)), 201

    @app.get("/api/lessons/<lesson_id>")
    def detail(lesson_id):
        return jsonify(service.get(lesson_id))

    @app.post("/api/lessons/quick-start")
    def quick_start():
        return jsonify(service.quick_start(demo=demo)), 201

    @app.post("/api/lessons/<lesson_id>/metadata")
    def metadata(lesson_id):
        return jsonify(service.save_metadata(lesson_id, body()))

    @app.post("/api/lessons/<lesson_id>/start")
    def start(lesson_id):
        return jsonify(service.start(lesson_id, body().get("device")))

    @app.post("/api/lessons/<lesson_id>/move")
    def move(lesson_id):
        return jsonify(service.move(lesson_id, body().get("collection")))

    @app.delete("/api/lessons/<lesson_id>")
    def delete(lesson_id):
        service.delete_permanently(lesson_id)
        return jsonify(deleted=True)

    @app.post("/api/lessons/<lesson_id>/pause")
    def pause(lesson_id):
        return jsonify(service.pause(lesson_id))

    @app.post("/api/lessons/<lesson_id>/stop")
    def stop(lesson_id):
        return jsonify(service.stop(lesson_id))

    @app.post("/api/lessons/<lesson_id>/retry")
    def retry(lesson_id):
        return jsonify(service.enqueue(lesson_id, "transcribe"))

    @app.post("/api/lessons/<lesson_id>/notes")
    def notes(lesson_id):
        return jsonify(service.enqueue(lesson_id, "notes"))

    @app.post("/api/lessons/<lesson_id>/text")
    def save_text(lesson_id):
        fields = body()
        return jsonify(service.save_text(lesson_id, fields.get("transcript"), fields.get("notes")))

    @app.post("/api/lessons/<lesson_id>/import")
    def import_audio(lesson_id):
        if "audio" not in request.files:
            raise ValueError("Seleziona un file audio.")
        with service.lock:
            return jsonify(service.import_audio(lesson_id, request.files["audio"]))

    @app.get("/api/lessons/<lesson_id>/download/<kind>")
    def download(lesson_id, kind):
        lesson = service.get(lesson_id)
        if kind == "notes-markdown":
            if not lesson["notes"].strip():
                raise ValueError("Gli appunti non sono ancora disponibili.")
            return send_file(io.BytesIO(lesson["notes"].encode("utf-8")),
                             mimetype="text/markdown; charset=utf-8", as_attachment=True,
                             download_name=f"appunti_{lesson_id}.md")
        if kind == "audio":
            if not lesson["audio"]:
                raise ValueError("Questa lezione non contiene audio.")
            path = service.root / lesson_id / lesson["audio"]
        elif kind in ("transcript", "notes"):
            path = service.root / lesson_id / (kind + ".txt")
        else:
            raise KeyError()
        if not path.exists():
            raise ValueError("Il file non è ancora disponibile.")
        return send_file(path, as_attachment=request.args.get("play") != "1", download_name=f"{kind}_{lesson_id}{path.suffix}", conditional=True)

    return app


def run(demo=False, port=8765, open_browser=True):
    from waitress import serve
    url = f"http://127.0.0.1:{port}"
    import socket
    with socket.socket() as probe:
        probe.settimeout(1)
        if probe.connect_ex(("127.0.0.1", port)) == 0:
            print(f"La porta {port} è già in uso. Apri il pannello esistente: {url}")
            if open_browser:
                webbrowser.open(url)
            return
    app = create_app(demo=demo)
    print(f"Assistente Lezione web: {url}\nChiudi questa finestra o premi Ctrl+C per fermare il server.")
    if open_browser:
        threading.Timer(1, lambda: webbrowser.open(url)).start()
    try:
        serve(app, host="127.0.0.1", port=port, threads=6)
    finally:
        app.extensions["lessons"].close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Assistente Lezione web locale")
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument("--demo", action="store_true")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()
    run(args.demo, args.port, not args.no_browser)
