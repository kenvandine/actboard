"""Simple local web server for the Actboard dashboard."""

import json
import mimetypes
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
        params = urllib.parse.parse_qs(parsed_path.query)

        if path == '/':
            self.send_file('web_dashboard.html', 'text/html')
        elif path == '/api/triage':
            date_param = params.get('date', [None])[0]
            self.send_triage_json(date=date_param)
        elif path == '/api/history':
            self.send_history_json()
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

    def _triage_files(self):
        return sorted(
            Path(self.triage_dir).glob('triage_output_*.json'),
            key=lambda p: p.name,
            reverse=True,
        )

    def send_history_json(self):
        files = self._triage_files()
        history = []
        for p in files:
            stem = p.stem  # triage_output_YYYY-MM-DD
            date_str = stem.replace('triage_output_', '')
            try:
                with open(p) as f:
                    data = json.load(f)
                act = monitor = handled = 0
                for key, val in data.items():
                    if key == 'generated_at' or key.startswith('_') or not isinstance(val, dict):
                        continue
                    act += len(val.get('act', []))
                    monitor += len(val.get('monitor', []))
                    handled += len(val.get('handled', []))
                history.append({
                    'date': date_str,
                    'generated_at': data.get('generated_at'),
                    'act': act,
                    'monitor': monitor,
                    'handled': handled,
                })
            except Exception:
                history.append({'date': date_str, 'generated_at': None, 'act': 0, 'monitor': 0, 'handled': 0})
        content = json.dumps(history).encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', len(content))
        self.send_header('Cache-Control', 'no-cache')
        self.end_headers()
        self.wfile.write(content)

    def send_triage_json(self, date=None):
        if date:
            json_path = Path(self.triage_dir) / f'triage_output_{date}.json'
            if not json_path.exists():
                self.send_error(404, f'No triage data for {date}.')
                return
        else:
            from datetime import date as _date
            today = _date.today().isoformat()
            json_path = Path(self.triage_dir) / f'triage_output_{today}.json'
            if not json_path.exists():
                files = self._triage_files()
                if files:
                    json_path = files[0]
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


def run_server(port=8080, host='localhost', triage_dir=None):
    """Start the local web dashboard server."""

    def handler(*args, **kwargs):
        return DashboardHandler(*args, triage_dir=triage_dir, **kwargs)

    server = HTTPServer((host, port), handler)
    display_host = f'[{host}]' if ':' in host else host
    print(f"Actboard Dashboard running at http://{display_host}:{port}")
    print("Press Ctrl+C to stop the server")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        server.shutdown()


if __name__ == '__main__':
    import sys
    import yaml
    _config_path = Path(__file__).parent / "config.yaml"
    _config = {}
    if _config_path.exists():
        with open(_config_path) as _f:
            _config = yaml.safe_load(_f) or {}
    _web_cfg = _config.get("web", {})
    port = _web_cfg.get("port", 8080)
    host = _web_cfg.get("host", "localhost")
    for i, arg in enumerate(sys.argv[1:], 1):
        if arg == "--port" and i + 1 < len(sys.argv):
            try:
                port = int(sys.argv[i + 1])
            except ValueError:
                print(f"Invalid port: {sys.argv[i + 1]}")
                sys.exit(1)
        elif arg == "--host" and i + 1 < len(sys.argv):
            host = sys.argv[i + 1]
    run_server(port, host=host)
