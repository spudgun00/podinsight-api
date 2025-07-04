import asyncio
import json
import os
import aiohttp
import base64
import webbrowser
import urllib.parse
from datetime import datetime, timedelta
from sse_starlette.sse import EventSourceResponse

class AsanaMCPClient:
    def __init__(self, config_file='mcp_asana_config.json'):
        with open(config_file, 'r') as f:
            self.config = json.load(f)
        self.token_info = {}
        self.session = None

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
        # This is a simplified version - in a real app, you'd want to handle this properly
        print("Please authenticate with Asana...")
        auth_url = (
            'https://app.asana.com/-/oauth_authorize?'
            f'client_id={self.config["auth"]["client_id"]}'
            f'&redirect_uri={urllib.parse.quote(self.config["auth"]["redirect_uri"])}'
            '&response_type=code'
            f'&scope={" ".join(self.config["scopes"])}'
        )
        print(f"Please visit this URL to authorize the application:\n{auth_url}")
        auth_code = input("Enter the authorization code from the URL: ")
        
        token_url = 'https://app.asana.com/-/oauth_token'
        auth_header = base64.b64encode(
            f"{self.config['auth']['client_id']}:{self.config['auth']['client_secret']}"
            .encode('utf-8')
        ).decode('utf-8')
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                token_url,
                headers={
                    'Authorization': f'Basic {auth_header}',
                    'Content-Type': 'application/x-www-form-urlencoded'
                },
                data={
                    'grant_type': 'authorization_code',
                    'code': auth_code,
                    'redirect_uri': self.config['auth']['redirect_uri']
                }
            ) as response:
                if response.status != 200:
                    error = await response.text()
                    raise Exception(f"Failed to get access token: {error}")
                
                self.token_info = await response.json()
                # Calculate expiration time
                self.token_info['expires_at'] = (
                    datetime.now().timestamp() + self.token_info['expires_in']
                )
                
                # Save token info for future use
                with open('.asana_token.json', 'w') as f:
                    json.dump(self.token_info, f)
                
                return self.token_info['access_token']

    async def refresh_token(self):
        if not self.token_info.get('refresh_token'):
            raise Exception("No refresh token available")
            
        token_url = 'https://app.asana.com/-/oauth_token'
        auth_header = base64.b64encode(
            f"{self.config['auth']['client_id']}:{self.config['auth']['client_secret']}"
            .encode('utf-8')
        ).decode('utf-8')
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                token_url,
                headers={
                    'Authorization': f'Basic {auth_header}',
                    'Content-Type': 'application/x-www-form-urlencoded'
                },
                data={
                    'grant_type': 'refresh_token',
                    'refresh_token': self.token_info['refresh_token']
                }
            ) as response:
                if response.status != 200:
                    error = await response.text()
                    raise Exception(f"Failed to refresh token: {error}")
                
                self.token_info = await response.json()
                self.token_info['expires_at'] = (
                    datetime.now().timestamp() + self.token_info['expires_in']
                )
                
                # Save updated token info
                with open('.asana_token.json', 'w') as f:
                    json.dump(self.token_info, f)

    async def connect_to_mcp(self):
        if self.config['auth']['type'] == 'pat':
            # Use Personal Access Token
            auth_header = f"Bearer {self.config['auth']['pat_token']}"
        else:
            # Fall back to OAuth flow if needed
            auth_header = f"Bearer {await self.get_access_token()}"
        
        headers = {
            'Authorization': auth_header,
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
                        print(f"Failed to connect to MCP server: {response.status} - {error}")
                        return
                    
                    print("Successfully connected to Asana MCP server. Waiting for events...")
                    async for line in response.content:
                        if line:
                            print(f"Received: {line.decode().strip()}")
                            
        except Exception as e:
            print(f"Error connecting to MCP server: {str(e)}")

    async def close(self):
        if self.session:
            await self.session.close()

async def main():
    client = AsanaMCPClient()
    try:
        await client.connect_to_mcp()
    except KeyboardInterrupt:
        print("\nDisconnecting from MCP server...")
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(main())
