from flask import Flask, render_template, jsonify, request
from module.summarizer import summarize_text

app = Flask(__name__)

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

if __name__ == '__main__':
    app.run(debug=True)