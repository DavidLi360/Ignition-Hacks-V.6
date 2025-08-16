from flask import Flask, render_template, jsonify, request
from module.summarizer import summarize_text, docx_to_sentences
from werkzeug.utils import secure_filename
import os

app = Flask(__name__)
UPLOAD_FOLDER = "uploads"
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route('/')
def home():
    return render_template('index.html')

@app.route("/summarize", methods=["POST"])
def summarize():
    try:
        data = request.get_json()
        text = data.get("text", "")
        summary = summarize_text(text)
        return jsonify(summary)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@app.route("/summarize-docx", methods=["POST"])
def summarize_docx():
    file = request.files.get("file")
    if not file or not file.filename.endswith(".docx"):
        return jsonify({"error": "Please upload a DOCX file"}), 400

    file_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(file.filename))
    file.save(file_path)

    # Convert DOCX → sentences
    sentences = docx_to_sentences(file_path)

    # Optional: summarize
    summary = summarize_text(" ".join(sentences))
    return jsonify(summary)

if __name__ == '__main__':
    app.run(debug=True)