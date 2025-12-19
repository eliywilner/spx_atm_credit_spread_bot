"""Schwab API client for making authenticated requests."""
import logging
import requests
from typing import Dict, Optional
from src.auth.schwab_auth import SchwabAuth
from src.config import Config
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class SchwabClient:
    """Client for interacting with Schwab API."""
    
    def __init__(self):
        """Initialize the Schwab API client."""
        self.auth = SchwabAuth()
        self.base_url = Config.API_BASE_URL
    
    def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        data: Optional[Dict] = None,
        json_data: Optional[Dict] = None
    ) -> Dict:
        """
        Make an authenticated request to the Schwab API.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (e.g., '/v1/accounts')
            params: URL parameters
            data: Form data
            json_data: JSON body data
            
        Returns:
            dict: Response JSON data
        """
        url = f"{self.base_url}{endpoint}"
        headers = self.auth.get_headers()
        
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                data=data,
                json=json_data
            )
            
            # If token expired, try refreshing
            if response.status_code == 401:
                logger.warning("Token expired, refreshing...")
                self.auth.refresh_access_token()
                headers = self.auth.get_headers()
                response = requests.request(
                    method=method,
                    url=url,
                    headers=headers,
                    params=params,
                    data=data,
                    json=json_data
                )
            
            response.raise_for_status()
            
            # Some endpoints return empty responses (204 No Content) for successful operations
            if response.status_code == 204 or not response.text:
                logger.info("Request successful (empty response)")
                return {}
            
            try:
                return response.json()
            except ValueError:
                # If response is not JSON, return the text
                logger.warning(f"Response is not JSON, returning text")
                return {"response_text": response.text, "status_code": response.status_code}
            
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP Error: {e}")
            if response.text:
                logger.error(f"Response: {response.text}")
            raise
    
    def get_accounts(self) -> Dict:
        """
        Get list of account numbers and their encrypted values.
        
        Returns:
            dict: Account information with account numbers and encrypted values
        """
        return self._make_request('GET', '/accounts/accountNumbers')
    
    def get_account(self, account_id: str) -> Dict:
        """
        Get details for a specific account.
        
        Args:
            account_id: The account ID
            
        Returns:
            dict: Account details
        """
        return self._make_request('GET', f'/v1/accounts/{account_id}')
    
    def get_positions(self, account_id: str) -> Dict:
        """
        Get positions for a specific account.
        
        Args:
            account_id: The account ID
            
        Returns:
            dict: Position information
        """
        return self._make_request('GET', f'/v1/accounts/{account_id}/positions')
    
    def get_orders(self, account_id: str, max_results: int = 50) -> Dict:
        """
        Get orders for a specific account.
        
        Args:
            account_id: The account ID
            max_results: Maximum number of results to return
            
        Returns:
            dict: Order information
        """
        params = {'maxResults': max_results}
        return self._make_request('GET', f'/v1/accounts/{account_id}/orders', params=params)

