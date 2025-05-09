# backend/app.py
from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os
from dotenv import load_dotenv

load_dotenv()  # <-- load .env Failed

app = Flask(__name__)
CORS(app)

# Use environment variable or fallback
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"

def engineer_prompt(user_input):
    return (
        "You are a Kubernetes troubleshooting assistant.\n"
        "A user has asked the following:\n\n"
        f"\"{user_input}\"\n\n"
        "Your task is to return short, actionable remediation steps ONLY.\n"
        "Do NOT explain the issue. DO NOT include anything other than Kubernetes-related solutions.\n"
        "Return the response in bullet points like:\n"
        "- Check CPU resource limits.\n"
        "- Scale up the node pool.\n"
        "- Restart the affected pod.\n"
    )

@app.route('/')
def index():
    return 'Backend is up 🎉'

@app.route("/k8s-chat", methods=["POST"])
def k8s_chat():
    data = request.get_json()
    user_query = data.get("userQuery", "")

    headers = {
        "Content-Type": "application/json"
    }

    payload = {
        "contents": [
            {
                "parts": [
                    {"text": engineer_prompt(user_query)}
                ]
            }
        ]
    }

    response = requests.post(
        GEMINI_URL + f"?key={GEMINI_API_KEY}",
        headers=headers,
        json=payload
    )

    if response.status_code == 200:
        gemini_response = response.json()
        reply = gemini_response['candidates'][0]['content']['parts'][0]['text']
        return jsonify({"reply": reply})
    else:
        return jsonify({"error": "Failed to get response from Gemini", "details": response.text}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, host='0.0.0.0', port=port)
