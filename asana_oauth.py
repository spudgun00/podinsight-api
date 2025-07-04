import json
import webbrowser
import http.server
import socketserver
import urllib.parse
from http import HTTPStatus

class OAuthCallbackHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        # Parse the query parameters
        query = urllib.parse.urlparse(self.path).query
        params = urllib.parse.parse_qs(query)
        
        # Get the authorization code
        if 'code' in params:
            self.server.auth_code = params['code'][0]
            self.send_response(HTTPStatus.OK)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(b'<html><body><h1>Authentication successful! You can close this window.</h1></body></html>')
            # Shutdown the server after handling the request
            self.server.shutdown()
        else:
            self.send_error(HTTPStatus.BAD_REQUEST, "Missing authorization code")

def get_auth_url():
    # Load configuration
    with open('mcp_asana_config.json', 'r') as f:
        config = json.load(f)
    
    # Build the authorization URL
    auth_url = (
        'https://app.asana.com/-/oauth_authorize?'
        f'client_id={config["auth"]["client_id"]}'
        f'&redirect_uri={urllib.parse.quote(config["auth"]["redirect_uri"])}'
        '&response_type=code'
        f'&scope={" ".join(config["scopes"])}'
    )
    return auth_url

def get_auth_code():
    # Start a simple HTTP server to handle the OAuth callback
    with socketserver.TCPServer(("localhost", 8080), OAuthCallbackHandler) as httpd:
        print("Opening browser for Asana OAuth authentication...")
        auth_url = get_auth_url()
        webbrowser.open(auth_url)
        print(f"If browser doesn't open, visit this URL: {auth_url}")
        
        # Wait for the OAuth callback
        httpd.handle_request()
        
        # Return the authorization code
        return httpd.auth_code

if __name__ == "__main__":
    auth_code = get_auth_code()
    print(f"\nAuthorization code: {auth_code}")
    print("\nUse this code to get an access token.")
