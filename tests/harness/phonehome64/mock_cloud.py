# Fake cloud server for testing phonehome.py on a box (fix 64). Logs every request.
import http.server, json, sys
LOG = open('/tmp/mock_cloud.log', 'a')
class H(http.server.BaseHTTPRequestHandler):
    def _done(self, body):
        n = int(self.headers.get('Content-Length') or 0)
        data = self.rfile.read(n).decode('utf-8', 'replace') if n else ''
        LOG.write(json.dumps({'method': self.command, 'path': self.path,
                              'auth': self.headers.get('Authorization'), 'body': data[:2000]}) + '\n'); LOG.flush()
        b = json.dumps(body).encode()
        self.send_response(200); self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(b))); self.end_headers(); self.wfile.write(b)
    def do_GET(self):
        self._done([] if self.path.startswith('/chathost/settings') else {'ok': True})
    def do_POST(self): self._done({'ok': True})
    def do_DELETE(self): self._done({'ok': True})
    def log_message(self, *a): pass
http.server.HTTPServer(('127.0.0.1', 8099), H).serve_forever()
