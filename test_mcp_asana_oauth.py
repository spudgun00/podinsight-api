import asyncio
import json
import os
import aiohttp
import base64
import webbrowser
import urllib.parse
from datetime import datetime, timedelta
from aiohttp import web
import threading

class AsanaMCPClient:
    def __init__(self, config_file='mcp_asana_oauth_config.json'):
        with open(config_file, 'r') as f:
            self.config = json.load(f)
        self.token_info = self.load_saved_token()
        self.session = None
        self.auth_code = None
        self.auth_complete = asyncio.Event()

    def load_saved_token(self):
        """Load saved token from file if it exists"""
        try:
            if os.path.exists('.asana_token.json'):
                with open('.asana_token.json', 'r') as f:
                    return json.load(f)
        except:
            pass
        return {}

    def save_token(self):
        """Save token to file"""
        if self.token_info:
            with open('.asana_token.json', 'w') as f:
                json.dump(self.token_info, f)

    async def get_access_token(self):
        # Check if we have a valid token
        if self.token_info.get('access_token') and \
           datetime.now().timestamp() < self.token_info.get('expires_at', 0):
            return self.token_info['access_token']
        
        # If we have a refresh token, try to refresh
        if self.token_info.get('refresh_token'):
            try:
                await self.refresh_token()
                return self.token_info['access_token']
            except Exception as e:
                print(f"Failed to refresh token: {e}")
        
        # Otherwise, we need to get a new token
        return await self.authenticate()

    async def authenticate(self):
        """OAuth flow with browser authentication"""
        print("\n🔐 Starting OAuth authentication flow...")
        
        # Start local server to receive callback
        app = web.Application()
        app.router.add_get('/callback', self.oauth_callback)
        
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, 'localhost', 8080)
        
        server_task = asyncio.create_task(site.start())
        
        # Build authorization URL
        auth_url = (
            'https://app.asana.com/-/oauth_authorize?'
            f'client_id={self.config["auth"]["client_id"]}'
            f'&redirect_uri={urllib.parse.quote(self.config["auth"]["redirect_uri"])}'
            '&response_type=code'
            f'&scope={" ".join(self.config["scopes"])}'
        )
        
        print(f"\n📋 Opening browser for authentication...")
        print(f"If browser doesn't open automatically, please visit:\n{auth_url}\n")
        
        # Open browser
        webbrowser.open(auth_url)
        
        # Wait for callback
        print("⏳ Waiting for authorization callback...")
        await self.auth_complete.wait()
        
        # Clean up server
        await runner.cleanup()
        
        if not self.auth_code:
            raise Exception("No authorization code received")
        
        # Exchange code for token
        print("\n🔄 Exchanging authorization code for access token...")
        await self.exchange_code_for_token(self.auth_code)
        
        return self.token_info['access_token']

    async def oauth_callback(self, request):
        """Handle OAuth callback"""
        code = request.query.get('code')
        error = request.query.get('error')
        
        if error:
            print(f"\n❌ Authorization error: {error}")
            self.auth_complete.set()
            return web.Response(text=f"Authorization failed: {error}", status=400)
        
        if code:
            print(f"\n✅ Authorization code received!")
            self.auth_code = code
            self.auth_complete.set()
            
            html = """
            <html>
            <head><title>Authorization Successful</title></head>
            <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
                <h1>✅ Authorization Successful!</h1>
                <p>You can now close this window and return to the terminal.</p>
                <script>setTimeout(function(){window.close();}, 2000);</script>
            </body>
            </html>
            """
            return web.Response(text=html, content_type='text/html')
        
        return web.Response(text="No authorization code received", status=400)

    async def exchange_code_for_token(self, code):
        """Exchange authorization code for access token"""
        token_url = 'https://app.asana.com/-/oauth_token'
        
        # Prepare auth header
        auth_header = base64.b64encode(
            f"{self.config['auth']['client_id']}:{self.config['auth']['client_secret']}".encode()
        ).decode()
        
        headers = {
            'Authorization': f'Basic {auth_header}',
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        data = {
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': self.config['auth']['redirect_uri']
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(token_url, headers=headers, data=data) as response:
                if response.status == 200:
                    token_data = await response.json()
                    self.token_info = {
                        'access_token': token_data['access_token'],
                        'refresh_token': token_data.get('refresh_token'),
                        'expires_at': datetime.now().timestamp() + token_data.get('expires_in', 3600)
                    }
                    self.save_token()
                    print("✅ Access token obtained successfully!")
                else:
                    error = await response.text()
                    raise Exception(f"Failed to get access token: {response.status} - {error}")

    async def refresh_token(self):
        """Refresh the access token"""
        token_url = 'https://app.asana.com/-/oauth_token'
        
        auth_header = base64.b64encode(
            f"{self.config['auth']['client_id']}:{self.config['auth']['client_secret']}".encode()
        ).decode()
        
        headers = {
            'Authorization': f'Basic {auth_header}',
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        data = {
            'grant_type': 'refresh_token',
            'refresh_token': self.token_info['refresh_token']
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(token_url, headers=headers, data=data) as response:
                if response.status == 200:
                    token_data = await response.json()
                    self.token_info['access_token'] = token_data['access_token']
                    self.token_info['expires_at'] = datetime.now().timestamp() + token_data.get('expires_in', 3600)
                    self.save_token()
                else:
                    raise Exception("Failed to refresh token")

    async def connect_to_mcp(self):
        """Connect to MCP server"""
        print("\n🔌 Connecting to MCP server...")
        
        # Get access token
        access_token = await self.get_access_token()
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Accept': 'text/event-stream',
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.config['server_url'],
                    headers=headers,
                    timeout=30
                ) as response:
                    if response.status != 200:
                        error = await response.text()
                        print(f"❌ Failed to connect to MCP server: {response.status} - {error}")
                        return
                    
                    print("✅ Successfully connected to MCP server!")
                    print("\n📡 Listening for events...")
                    
                    # Read events
                    async for line in response.content:
                        if line:
                            data = line.decode('utf-8').strip()
                            if data.startswith('data: '):
                                event_data = data[6:]
                                if event_data == '[DONE]':
                                    print("\n✅ Stream completed")
                                    break
                                try:
                                    event = json.loads(event_data)
                                    print(f"\n📨 Event received: {json.dumps(event, indent=2)}")
                                except json.JSONDecodeError:
                                    print(f"📝 Raw event: {event_data}")
                            elif data.startswith('event: '):
                                print(f"📌 Event type: {data[7:]}")
                            
        except asyncio.TimeoutError:
            print("\n⏱️ Connection timeout - this might be normal if no events are being sent")
        except Exception as e:
            print(f"\n❌ Connection error: {e}")

async def main():
    print("🚀 Asana MCP Client Test (OAuth Flow)")
    print("=" * 50)
    
    # Check if OAuth config exists
    if not os.path.exists('mcp_asana_oauth_config.json'):
        print("\n❌ OAuth config file not found!")
        print("Please update mcp_asana_oauth_config.json with your Asana app credentials:")
        print("  - client_id: Your Asana app client ID")
        print("  - client_secret: Your Asana app client secret")
        print("\nYou can create an Asana app at: https://app.asana.com/0/developer-console")
        return
    
    # Load config to check if credentials are set
    with open('mcp_asana_oauth_config.json', 'r') as f:
        config = json.load(f)
    
    if config['auth']['client_id'] == 'YOUR_ASANA_CLIENT_ID':
        print("\n⚠️  Please update mcp_asana_oauth_config.json with your actual Asana app credentials!")
        print("\nYou can create an Asana app at: https://app.asana.com/0/developer-console")
        print("\n1. Create a new app")
        print("2. Add 'http://localhost:8080/callback' as a redirect URI")
        print("3. Copy the client ID and client secret to mcp_asana_oauth_config.json")
        return
    
    client = AsanaMCPClient()
    await client.connect_to_mcp()

if __name__ == "__main__":
    asyncio.run(main())