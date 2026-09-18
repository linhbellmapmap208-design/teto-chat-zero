from http.server import BaseHTTPRequestHandler
import json
import os
import httpx
import google.generativeai as genai
import base64
import traceback

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GLM_API_KEY = os.environ.get("GLM_API_KEY", "")

genai.configure(api_key=GEMINI_API_KEY)


def chat_gemini(messages, model_name="gemini-2.0-flash", image_data=None, file_data=None):
    model = genai.GenerativeModel(model_name)

    contents = []
    for msg in messages:
        role = "user" if msg["role"] == "user" else "model"
        parts = []

        if isinstance(msg["content"], list):
            for part in msg["content"]:
                if part["type"] == "text":
                    parts.append(part["text"])
                elif part["type"] == "image":
                    img_bytes = base64.b64decode(part["data"])
                    parts.append({
                        "mime_type": part.get("mime_type", "image/png"),
                        "data": img_bytes
                    })
                elif part["type"] == "file":
                    parts.append(f"[File: {part['filename']}]\n{part['content']}")
        else:
            parts.append(msg["content"])

        contents.append({"role": role, "parts": parts})

    response = model.generate_content(contents)
    return response.text


def chat_glm(messages, model_name="glm-4-flash"):
    url = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {GLM_API_KEY}"
    }

    glm_messages = []
    for msg in messages:
        content = ""
        if isinstance(msg["content"], list):
            for part in msg["content"]:
                if part["type"] == "text":
                    content += part["text"]
                elif part["type"] == "image":
                    content += "[Image attached]"
                elif part["type"] == "file":
                    content += f"[File: {part['filename']}]\n{part['content']}"
        else:
            content = msg["content"]
        glm_messages.append({"role": msg["role"], "content": content})

    payload = {
        "model": model_name,
        "messages": glm_messages,
        "temperature": 0.7,
        "max_tokens": 4096
    }

    with httpx.Client(timeout=60) as client:
        resp = client.post(url, headers=headers, json=payload)
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            data = json.loads(body)

            messages = data.get("messages", [])
            model = data.get("model", "gemini-2.0-flash")
            provider = data.get("provider", "gemini")

            if provider == "glm":
                result = chat_glm(messages, model)
            else:
                result = chat_gemini(messages, model)

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({
                "response": result,
                "model": model,
                "provider": provider
            }).encode())

        except Exception as e:
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({
                "error": str(e),
                "traceback": traceback.format_exc()
            }).encode())

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
