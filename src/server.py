"""
server.py — Flask 后端
提供 REST API 和页面渲染
"""

import os
import tempfile
from flask import Flask, render_template, request, jsonify

# Project root (one level up from src/)
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

from src.pipeline import run_pipeline, is_demo_mode
from src.utils import load_sample, get_sample_names
from src.database import init_db, save_result, get_history, get_record, delete_record, clear_history

app = Flask(
    __name__,
    template_folder=os.path.join(PROJECT_ROOT, "templates"),
    static_folder=os.path.join(PROJECT_ROOT, "static"),
)
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024  # 10MB
init_db()


def _extract_text_from_file(filepath: str, filename: str) -> str:
    """从 PDF 或 DOCX 文件中提取文本"""
    ext = os.path.splitext(filename)[1].lower()

    if ext == ".pdf":
        import pdfplumber
        text_parts = []
        with pdfplumber.open(filepath) as pdf:
            for page in pdf.pages[:30]:  # 最多 30 页
                t = page.extract_text()
                if t:
                    text_parts.append(t)
        return "\n\n".join(text_parts)

    elif ext == ".docx":
        from docx import Document
        doc = Document(filepath)
        return "\n".join(p.text for p in doc.paragraphs if p.text.strip())

    elif ext == ".txt":
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()

    else:
        raise ValueError(f"Unsupported file type: {ext}")


# ---- 页面 ----
@app.route("/")
def index():
    return render_template("index.html")


# ---- API ----
@app.route("/api/mode")
def api_mode():
    return jsonify({"demo": is_demo_mode()})


@app.route("/api/samples")
def api_samples():
    return jsonify(get_sample_names())


@app.route("/api/sample/<name>")
def api_sample(name):
    text = load_sample(name)
    if not text:
        return jsonify({"error": "Sample not found"}), 404
    return jsonify({"name": name, "text": text})


@app.route("/api/generate", methods=["POST"])
def api_generate():
    data = request.get_json(silent=True) or {}
    text = data.get("text", "").strip()
    sample_name = data.get("sample_name", "")

    if not text:
        return jsonify({"error": "Please paste a campus brief first."}), 400

    result = run_pipeline(text, sample_name=sample_name)

    # 持久化
    task_type = result.get("task_type", "notice")
    record_id = save_result(text, task_type, result)
    result["id"] = record_id

    return jsonify(result)


@app.route("/api/upload", methods=["POST"])
def api_upload():
    """上传 PDF / DOCX / TXT 文件，提取文本返回"""
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    f = request.files["file"]
    if not f.filename:
        return jsonify({"error": "Empty filename"}), 400

    allowed = {".pdf", ".docx", ".txt"}
    ext = os.path.splitext(f.filename)[1].lower()
    if ext not in allowed:
        return jsonify({"error": f"Unsupported format. Please upload: {', '.join(allowed)}"}), 400

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
    try:
        f.save(tmp.name)
        tmp.close()
        text = _extract_text_from_file(tmp.name, f.filename)

        if not text.strip():
            return jsonify({"error": "Could not extract text from file. The file may be image-based."}), 400

        return jsonify({"text": text, "filename": f.filename, "chars": len(text)})
    except Exception as e:
        return jsonify({"error": f"Failed to process file: {str(e)}"}), 500
    finally:
        try:
            os.unlink(tmp.name)
        except OSError:
            pass


@app.route("/api/history")
def api_history():
    return jsonify(get_history())


@app.route("/api/history/<int:rid>")
def api_history_detail(rid):
    record = get_record(rid)
    if not record:
        return jsonify({"error": "Not found"}), 404
    return jsonify(record)


@app.route("/api/history/<int:rid>", methods=["DELETE"])
def api_history_delete(rid):
    delete_record(rid)
    return jsonify({"ok": True})


@app.route("/api/history", methods=["DELETE"])
def api_history_clear():
    clear_history()
    return jsonify({"ok": True})



