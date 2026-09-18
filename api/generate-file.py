from http.server import BaseHTTPRequestHandler
import json
import os
import google.generativeai as genai
import traceback

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
genai.configure(api_key=GEMINI_API_KEY)


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            data = json.loads(body)

            prompt = data.get("prompt", "")
            filename = data.get("filename", "output.py")

            model = genai.GenerativeModel("gemini-2.0-flash")
            response = model.generate_content(
                f"Generate the content for a file named '{filename}' based on this request: {prompt}. "
                f"Return ONLY the file content, no markdown code blocks, no explanations."
            )

            file_content = response.text
            if file_content.startswith("```"):
                lines = file_content.split("\n")
                file_content = "\n".join(lines[1:-1]) if lines[-1].strip() == "```" else "\n".join(lines[1:])

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({
                "content": file_content,
                "filename": filename
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
