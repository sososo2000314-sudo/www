from http.server import HTTPServer, SimpleHTTPRequestHandler
import os

PORT = 8000

os.chdir(os.path.dirname(os.path.abspath(__file__)))

server = HTTPServer(("0.0.0.0", PORT), SimpleHTTPRequestHandler)

print(f"サーバー起動: http://localhost:{PORT}")
server.serve_forever()
