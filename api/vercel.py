"""
Vercel-specific handler configuration.
"""

from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs
import json
from io import BytesIO
import asyncio
from api.index import app

def make_handler():
    """Create a handler class for Vercel."""
    
    class VercelHandler(BaseHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            
        def _read_body(self):
            """Read and return the request body."""
            content_length = int(self.headers.get('Content-Length', 0))
            return self.rfile.read(content_length)
            
        def _to_asgi_scope(self, body: bytes):
            """Convert the request to an ASGI scope."""
            # Parse query string
            query_string = b''
            if '?' in self.path:
                path, query = self.path.split('?', 1)
                query_string = query.encode()
            else:
                path = self.path
                
            # Build headers
            headers = []
            for key, value in self.headers.items():
                headers.append(
                    (key.lower().encode(), value.encode())
                )
                
            # Build scope
            return {
                'type': 'http',
                'asgi': {'version': '3.0'},
                'http_version': '1.1',
                'method': self.command,
                'scheme': 'https',
                'path': path,
                'raw_path': path.encode(),
                'query_string': query_string,
                'headers': headers,
                'client': ('127.0.0.1', 0),
                'server': ('vercel', 443),
                'extensions': {},
            }
            
        async def _handle_request(self, scope, body):
            """Handle the ASGI request."""
            response_body = []
            response_headers = []
            response_status = None
            
            async def send(message):
                nonlocal response_body, response_headers, response_status
                if message['type'] == 'http.response.start':
                    response_status = message['status']
                    response_headers = message['headers']
                elif message['type'] == 'http.response.body':
                    if message.get('body'):
                        response_body.append(message['body'])
                        
            async def receive():
                return {
                    'type': 'http.request',
                    'body': body,
                    'more_body': False,
                }
                
            await app(scope, receive, send)
            return response_status, response_headers, b''.join(response_body)
            
        def _handle_asgi(self):
            """Process the request through FastAPI."""
            try:
                # Read request body
                body = self._read_body()
                
                # Convert to ASGI scope
                scope = self._to_asgi_scope(body)
                
                # Run the ASGI application
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                status, headers, body = loop.run_until_complete(
                    self._handle_request(scope, body)
                )
                loop.close()
                
                # Send response
                self.send_response(status)
                for name, value in headers:
                    self.send_header(name.decode(), value.decode())
                self.end_headers()
                self.wfile.write(body)
                
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({
                    'error': str(e)
                }).encode())
                
        def do_GET(self):
            """Handle GET requests."""
            self._handle_asgi()
            
        def do_POST(self):
            """Handle POST requests."""
            self._handle_asgi()
            
        def do_OPTIONS(self):
            """Handle OPTIONS requests."""
            self._handle_asgi()
            
    return VercelHandler

# Create the handler class
Handler = make_handler() 