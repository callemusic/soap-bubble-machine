#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Ultra-simple test server"""

from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
import json

class TestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/health':
            response = json.dumps({'status': 'ok', 'pi': 'test'})
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Content-Length', str(len(response)))
            self.end_headers()
            self.wfile.write(response)
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        print("%s - %s" % (self.address_string(), format % args))

if __name__ == '__main__':
    server = HTTPServer(('', 5000), TestHandler)
    print("Test server starting on port 5000...")
    server.serve_forever()





