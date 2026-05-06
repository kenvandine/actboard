"""Simple local web server for the Actboard dashboard."""

import json
import mimetypes
from datetime import date
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler
import urllib.parse


class DashboardHandler(SimpleHTTPRequestHandler):
    """HTTP request handler for the local dashboard."""

    def __init__(self, *args, triage_dir=None, **kwargs):
        self.triage_dir = triage_dir or Path(__file__).parent
        super().__init__(*args, **kwargs)

    def do_GET(self):
        parsed_path = urllib.parse.urlparse(self.path)
        path = parsed_path.path

        if path == '/':
            self.send_file('web_dashboard.html', 'text/html')
        elif path == '/api/triage':
            self.send_triage_json()
        else:
            self.send_error(404, 'Not Found')

    def send_file(self, filename, content_type):
        file_path = Path(__file__).parent / filename
        try:
            with open(file_path, 'rb') as f:
                content = f.read()
            self.send_response(200)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', len(content))
            self.end_headers()
            self.wfile.write(content)
        except FileNotFoundError:
            self.send_error(404, f'File not found: {filename}')

    def send_triage_json(self):
        # Find the most recent triage_output_*.json file
        today = date.today().isoformat()
        json_path = Path(self.triage_dir) / f'triage_output_{today}.json'

        # If today's file doesn't exist, try to find the most recent one
        if not json_path.exists():
            json_files = sorted(
                Path(self.triage_dir).glob('triage_output_*.json'),
                key=lambda p: p.stat().st_mtime,
                reverse=True
            )
            if json_files:
                json_path = json_files[0]
            else:
                self.send_error(404, 'No triage data found. Run the triage first.')
                return

        try:
            with open(json_path, 'r') as f:
                data = json.load(f)
            content = json.dumps(data).encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', len(content))
            self.send_header('Cache-Control', 'no-cache')
            self.end_headers()
            self.wfile.write(content)
        except Exception as e:
            self.send_error(500, f'Error reading triage data: {e}')

    def log_message(self, format, *args):
        # Suppress default logging
        pass


def run_server(port=8080, triage_dir=None):
    """Start the local web dashboard server."""
    parent_dir = str(Path(__file__).parent)

    def handler(*args, **kwargs):
        return DashboardHandler(*args, triage_dir=triage_dir, **kwargs)

    server = HTTPServer(('localhost', port), handler)
    print(f"Actboard Dashboard running at http://localhost:{port}")
    print("Press Ctrl+C to stop the server")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        server.shutdown()


if __name__ == '__main__':
    import sys
    port = 8080
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            print(f"Invalid port: {sys.argv[1]}")
            sys.exit(1)
    run_server(port)
