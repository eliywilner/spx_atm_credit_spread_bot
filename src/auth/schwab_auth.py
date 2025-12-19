"""Schwab API authentication module."""
import json
import logging
import ssl
import webbrowser
import http.server
import urllib.parse
import os
from typing import Optional, Dict
import requests
from src.config import Config
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class SchwabAuth:
    """Handles authentication with Schwab API using OAuth 2.0."""
    
    def __init__(self):
        """Initialize the authentication handler."""
        Config.validate()
        self.client_id = Config.CLIENT_ID
        self.client_secret = Config.CLIENT_SECRET
        self.redirect_uri = Config.REDIRECT_URI
        self.token_file = Config.TOKEN_FILE
        self.access_token: Optional[str] = None
        self.refresh_token: Optional[str] = None
        
    def get_authorization_url(self) -> str:
        """
        Generate the authorization URL for OAuth flow.
        
        Returns:
            str: The authorization URL to visit in a browser
        """
        params = {
            'client_id': self.client_id,
            'redirect_uri': self.redirect_uri,
            'response_type': 'code',
            'scope': 'api'
        }
        
        auth_url = f"{Config.AUTH_BASE_URL}/v1/oauth/authorize"
        query_string = urllib.parse.urlencode(params)
        return f"{auth_url}?{query_string}"
    
    def _get_or_create_certificate(self):
        """
        Get or create self-signed certificate for localhost HTTPS.
        
        Returns:
            tuple: (cert_file, key_file) paths
        """
        cert_dir = os.path.join(os.path.dirname(__file__), '..', '..')
        cert_file = os.path.join(cert_dir, 'localhost.pem')
        key_file = os.path.join(cert_dir, 'localhost.key')
        
        # Check if certificate already exists
        if os.path.exists(cert_file) and os.path.exists(key_file):
            return cert_file, key_file
        
        # Generate self-signed certificate using openssl
        logger.info("Generating self-signed certificate for localhost...")
        import subprocess
        
        try:
            # Generate self-signed certificate and key
            # Using a combined approach that works on most systems
            # Generate certificate with both localhost and 127.0.0.1 in Subject Alternative Name
            # This helps browsers accept the certificate
            subprocess.run([
                'openssl', 'req', '-x509', '-newkey', 'rsa:2048',
                '-keyout', key_file,
                '-out', cert_file,
                '-days', '365',
                '-nodes',
                '-subj', '/CN=localhost',
                '-addext', 'subjectAltName=DNS:localhost,IP:127.0.0.1'
            ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            logger.info(f"Certificate created: {cert_file}")
            return cert_file, key_file
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            logger.error(f"Failed to generate certificate: {e}")
            logger.error("OpenSSL is required for localhost HTTPS")
            raise Exception(
                "Could not create SSL certificate. Please install OpenSSL:\n"
                "  macOS: OpenSSL should already be installed\n"
                "  If not: brew install openssl\n"
                "  Or use ngrok as an alternative: https://ngrok.com/download"
            )
    
    def _start_callback_server(self) -> str:
        """
        Start a local HTTPS server to receive the OAuth callback.
        
        Returns:
            str: The authorization code from the callback
        """
        code = None
        
        class CallbackHandler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                nonlocal code
                # Parse the callback URL
                parsed_path = urllib.parse.urlparse(self.path)
                query_params = urllib.parse.parse_qs(parsed_path.query)
                
                if 'code' in query_params:
                    code = query_params['code'][0]
                    self.send_response(200)
                    self.send_header('Content-type', 'text/html')
                    self.end_headers()
                    self.wfile.write(
                        b'<html><body><h1>Authentication successful!</h1>'
                        b'<p>You can close this window and return to the application.</p></body></html>'
                    )
                elif 'error' in query_params:
                    error = query_params['error'][0]
                    self.send_response(400)
                    self.send_header('Content-type', 'text/html')
                    self.end_headers()
                    self.wfile.write(
                        f'<html><body><h1>Authentication failed</h1>'
                        f'<p>Error: {error}</p></body></html>'.encode()
                    )
                else:
                    self.send_response(400)
                    self.send_header('Content-type', 'text/html')
                    self.end_headers()
                    self.wfile.write(
                        b'<html><body><h1>No authorization code received</h1></body></html>'
                    )
            
            def log_message(self, format, *args):
                # Suppress server logs
                pass
        
        # Extract port from redirect URI
        parsed_redirect = urllib.parse.urlparse(self.redirect_uri)
        port = parsed_redirect.port or 8080
        use_https = parsed_redirect.scheme == 'https'
        
        server = http.server.HTTPServer(('localhost', port), CallbackHandler)
        
        # Wrap with SSL if using HTTPS
        if use_https:
            try:
                cert_file, key_file = self._get_or_create_certificate()
                context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
                context.load_cert_chain(cert_file, key_file)
                server.socket = context.wrap_socket(server.socket, server_side=True)
                logger.info("HTTPS server started with self-signed certificate")
                logger.warning(
                    "Your browser may show a security warning for the self-signed certificate. "
                    "This is normal for localhost - click 'Advanced' and 'Proceed to localhost' to continue."
                )
            except Exception as e:
                logger.error(f"Failed to set up HTTPS: {e}")
                raise
        
        # Wait for the callback (with timeout)
        logger.info(f"Waiting for callback on {self.redirect_uri}...")
        server.timeout = 300  # 5 minute timeout
        server.handle_request()
        server.server_close()
        
        if not code:
            raise Exception("No authorization code received from callback")
        
        return code
    
    def exchange_code_for_tokens(self, authorization_code: str) -> Dict:
        """
        Exchange authorization code for access and refresh tokens.
        
        Args:
            authorization_code: The authorization code from the OAuth callback
            
        Returns:
            dict: Token response containing access_token and refresh_token
        """
        url = f"{Config.AUTH_BASE_URL}/v1/oauth/token"
        
        # Schwab API requires Basic Auth with client_id:client_secret
        import base64
        credentials = f"{self.client_id}:{self.client_secret}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()
        
        headers = {
            'Authorization': f'Basic {encoded_credentials}',
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        data = {
            'grant_type': 'authorization_code',
            'code': authorization_code,
            'redirect_uri': self.redirect_uri
        }
        
        response = requests.post(url, headers=headers, data=data)
        
        if not response.ok:
            error_msg = f"Token exchange failed: {response.status_code}"
            try:
                error_data = response.json()
                error_msg += f" - {error_data}"
            except:
                error_msg += f" - {response.text}"
            logger.error(error_msg)
            response.raise_for_status()
        
        token_data = response.json()
        self.access_token = token_data.get('access_token')
        self.refresh_token = token_data.get('refresh_token')
        
        # Save tokens to file
        self._save_tokens(token_data)
        
        return token_data
    
    def refresh_access_token(self) -> Dict:
        """
        Refresh the access token using the refresh token.
        
        Returns:
            dict: New token response
            
        Raises:
            Exception: If refresh token is invalid/expired and re-authentication is needed
        """
        if not self.refresh_token:
            self._load_tokens()
        
        if not self.refresh_token:
            raise Exception("No refresh token available. Please re-authenticate.")
        
        url = f"{Config.AUTH_BASE_URL}/v1/oauth/token"
        
        # Schwab API requires Basic Auth with client_id:client_secret
        import base64
        credentials = f"{self.client_id}:{self.client_secret}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()
        
        headers = {
            'Authorization': f'Basic {encoded_credentials}',
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        data = {
            'grant_type': 'refresh_token',
            'refresh_token': self.refresh_token
        }
        
        response = requests.post(url, headers=headers, data=data)
        
        if not response.ok:
            error_msg = f"Token refresh failed: {response.status_code}"
            error_data = None
            error_text = None
            
            try:
                error_data = response.json()
                error_msg += f" - {error_data}"
                error_text = str(error_data)
            except:
                error_text = response.text
                error_msg += f" - {error_text}"
            
            # Check if refresh token itself is expired/invalid
            # 400 Bad Request often means invalid/expired refresh token
            is_token_error = False
            if error_text:
                error_str = error_text.lower()
                is_token_error = any(keyword in error_str for keyword in [
                    'refresh_token_authentication_error',
                    'unsupported_token_type',
                    'invalid_grant',
                    'invalid_token',
                    'bad request'
                ]) or response.status_code == 400
            
            if is_token_error:
                logger.error("="*70)
                logger.error("REFRESH TOKEN EXPIRED OR INVALID - RE-AUTHENTICATION REQUIRED")
                logger.error("="*70)
                logger.error(f"Status Code: {response.status_code}")
                if error_data:
                    logger.error(f"Error Details: {error_data}")
                elif error_text:
                    logger.error(f"Error Response: {error_text}")
                logger.error("")
                logger.error("POSSIBLE CAUSES:")
                logger.error("  1. Refresh token expired (bot offline for >7 days)")
                logger.error("  2. Refresh token is invalid or corrupted")
                logger.error("  3. Client credentials (CLIENT_ID/CLIENT_SECRET) are incorrect")
                logger.error("  4. Token file was manually edited or corrupted")
                logger.error("")
                logger.error("HOW TOKEN REFRESH WORKS:")
                logger.error("  ✓ Access tokens (30 min) → Auto-refresh on every API call")
                logger.error("  ✓ Refresh tokens (7 days) → Auto-extend if bot runs weekly")
                logger.error("")
                logger.error("ACTION REQUIRED: Re-authenticate")
                logger.error("  1. SSH into EC2: ssh ubuntu@<your-ec2-ip>")
                logger.error("  2. Navigate to bot: cd ~/trading_bot")
                logger.error("  3. Delete tokens.json: rm tokens.json")
                logger.error("  4. Re-authenticate: python3 manual_auth.py")
                logger.error("  5. After this, automatic refresh will work again!")
                logger.error("")
                logger.error("NOTE: You do NOT need to re-authenticate every 7 days.")
                logger.error("      Only if the bot is offline for >7 consecutive days.")
                logger.error("="*70)
                
                # Clear invalid tokens to prevent retry loops
                self.access_token = None
                self.refresh_token = None
                # Don't delete the file - let user do it manually after backup if needed
                
            logger.error(error_msg)
            
            # Raise a more informative exception
            if is_token_error:
                raise Exception(
                    "Refresh token expired or invalid. Please re-authenticate. "
                    "See error logs above for detailed instructions."
                )
            else:
                response.raise_for_status()
        
        token_data = response.json()
        self.access_token = token_data.get('access_token')
        
        # Update refresh token if provided in response
        if 'refresh_token' in token_data:
            self.refresh_token = token_data.get('refresh_token')
            logger.debug("New refresh token received from API")
        else:
            # Schwab doesn't always return a new refresh token
            # Preserve the existing one to maintain the 7-day rolling window
            if self.refresh_token:
                token_data['refresh_token'] = self.refresh_token
                logger.debug("Preserving existing refresh token (not provided in response)")
            else:
                logger.warning("No refresh token in response and none in memory - may need re-authentication")
        
        # Save updated tokens (now includes refresh_token)
        self._save_tokens(token_data)
        logger.info("Access token refreshed successfully")
        
        return token_data
    
    def authenticate(self, manual_code: Optional[str] = None) -> str:
        """
        Complete OAuth authentication flow.
        
        Args:
            manual_code: Optional authorization code if callback server fails.
                        You can extract this from the callback URL after authentication.
                        If provided, will always authenticate (ignores existing tokens).
        
        Returns:
            str: Access token
        """
        # If manual code provided, always authenticate (don't check existing tokens)
        # This allows re-authentication even when tokens exist - creates NEW tokens every time
        if manual_code:
            logger.info("Manual authorization code provided - creating new tokens (ignoring existing tokens)")
            code = manual_code
        else:
            # Only check for existing tokens if no manual code provided
            if self._load_tokens():
                logger.info("Loaded existing tokens from file.")
                # Optionally verify token is still valid by making a test request
                # For now, we'll just return it
                return self.access_token
            
            # Start the OAuth flow (no manual code, no existing tokens)
            auth_url = self.get_authorization_url()
            logger.info("Please visit this URL to authorize the application:")
            logger.info(f"{auth_url}")
            
            # Try to open browser automatically
            try:
                webbrowser.open(auth_url)
                logger.info("Opened authorization URL in your default browser.")
            except Exception:
                logger.warning("Could not open browser automatically. Please copy the URL above.")
            
            logger.info("\n" + "="*60)
            logger.info("IMPORTANT: If browser shows 'site can't be reached':")
            logger.info("1. Accept the security warning (Advanced → Proceed)")
            logger.info("2. OR copy the full callback URL and run:")
            logger.info("   python -c \"from src.auth.schwab_auth import SchwabAuth; auth = SchwabAuth(); auth.authenticate(manual_code='CODE_FROM_URL')\"")
            logger.info("="*60 + "\n")
            
            # Wait for callback
            code = self._start_callback_server()
        
        # Exchange code for tokens
        logger.info("Exchanging authorization code for tokens...")
        self.exchange_code_for_tokens(code)
        
        logger.info("Authentication successful!")
        return self.access_token
    
    def get_access_token(self) -> str:
        """
        Get a valid access token, refreshing if necessary.
        
        Returns:
            str: Valid access token
        """
        if not self.access_token:
            self._load_tokens()
        
        if not self.access_token:
            # Need to authenticate
            return self.authenticate()
        
        # Token might be expired, but we'll handle that in API calls
        # For now, return the token we have
        return self.access_token
    
    def _save_tokens(self, token_data: Dict):
        """Save tokens to file."""
        with open(self.token_file, 'w') as f:
            json.dump(token_data, f, indent=2)
        logger.debug(f"Tokens saved to {self.token_file}")
    
    def _load_tokens(self) -> bool:
        """
        Load tokens from file.
        
        Returns:
            bool: True if tokens were loaded successfully
        """
        try:
            with open(self.token_file, 'r') as f:
                token_data = json.load(f)
                self.access_token = token_data.get('access_token')
                self.refresh_token = token_data.get('refresh_token')
                return True
        except FileNotFoundError:
            logger.debug("No existing token file found")
            return False
        except json.JSONDecodeError:
            logger.warning("Token file exists but is invalid")
            return False
    
    def get_headers(self) -> Dict[str, str]:
        """
        Get HTTP headers with authorization token.
        
        Returns:
            dict: Headers dictionary with Authorization header
        """
        token = self.get_access_token()
        return {
            'Authorization': f'Bearer {token}',
            'Accept': 'application/json'
        }

