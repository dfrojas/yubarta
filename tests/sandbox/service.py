from http.server import BaseHTTPRequestHandler, HTTPServer


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"tomcat-like service healthy\n")


HTTPServer.allow_reuse_address = True
HTTPServer(("0.0.0.0", 8080), Handler).serve_forever()
