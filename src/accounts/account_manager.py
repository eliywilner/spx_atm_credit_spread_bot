"""Account management for Schwab API."""
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional
from src.client.schwab_client import SchwabClient
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class AccountManager:
    """Manages account operations and order retrieval."""
    
    def __init__(self):
        """Initialize the account manager."""
        self.client = SchwabClient()
        self._account_cache: Optional[List[Dict]] = None
    
    def get_account_numbers(self) -> List[Dict]:
        """
        Get list of account numbers and their corresponding encrypted hash values.
        
        Returns:
            list: List of dictionaries with 'accountNumber' and 'hashValue' keys
                  Example: [{'accountNumber': '12345678', 'hashValue': 'ABC123...'}]
        """
        logger.info("Fetching account numbers and hash values...")
        accounts = self.client.get_accounts()
        self._account_cache = accounts
        
        logger.info(f"Found {len(accounts)} account(s)")
        for account in accounts:
            account_num = account.get('accountNumber', 'N/A')
            hash_val = account.get('hashValue', 'N/A')
            logger.debug(f"  Account: {account_num}, Hash: {hash_val[:20]}...")
        
        return accounts
    
    def get_account_hash(self, account_number: Optional[str] = None) -> str:
        """
        Get the encrypted hash value for a specific account number.
        
        Args:
            account_number: The plain text account number. If None, returns hash for first account.
        
        Returns:
            str: The encrypted hash value to use in API calls
        
        Raises:
            ValueError: If account number not found
        """
        accounts = self.get_account_numbers()
        
        if account_number is None:
            # Return hash for first account if no account number specified
            if accounts:
                return accounts[0].get('hashValue')
            else:
                raise ValueError("No accounts found")
        
        # Find the account by account number
        for account in accounts:
            if account.get('accountNumber') == account_number:
                return account.get('hashValue')
        
        raise ValueError(f"Account number {account_number} not found")
    
    def get_orders_executed_today(
        self,
        account_number: Optional[str] = None,
        max_results: int = 3000,
        status: Optional[str] = None
    ) -> List[Dict]:
        """
        Get all orders executed today for a specific account.
        
        Args:
            account_number: The plain text account number. If None, uses first account.
            max_results: Maximum number of orders to retrieve (default: 3000)
            status: Optional order status filter (e.g., 'FILLED', 'EXECUTED')
        
        Returns:
            list: List of order dictionaries
        
        Raises:
            ValueError: If account number not found
        """
        # Get the encrypted account hash
        account_hash = self.get_account_hash(account_number)
        
        # Get today's date range in ISO-8601 format
        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = datetime.now(timezone.utc).replace(hour=23, minute=59, second=59, microsecond=999000)
        
        from_entered_time = today_start.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
        to_entered_time = today_end.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
        
        logger.info(f"Fetching orders executed today (from {from_entered_time} to {to_entered_time})...")
        
        # Build query parameters
        params = {
            'maxResults': max_results,
            'fromEnteredTime': from_entered_time,
            'toEnteredTime': to_entered_time
        }
        
        if status:
            params['status'] = status
        
        # Make the API call
        endpoint = f'/accounts/{account_hash}/orders'
        orders = self.client._make_request('GET', endpoint, params=params)
        
        logger.info(f"Found {len(orders)} order(s) executed today")
        
        return orders
    
    def get_orders(
        self,
        account_number: Optional[str] = None,
        from_entered_time: Optional[str] = None,
        to_entered_time: Optional[str] = None,
        max_results: int = 3000,
        status: Optional[str] = None
    ) -> List[Dict]:
        """
        Get orders for a specific account with custom date range.
        
        Args:
            account_number: The plain text account number. If None, uses first account.
            from_entered_time: Start time in ISO-8601 format (e.g., '2024-03-29T00:00:00.000Z')
            to_entered_time: End time in ISO-8601 format (e.g., '2024-04-28T23:59:59.000Z')
            max_results: Maximum number of orders to retrieve (default: 3000)
            status: Optional order status filter
        
        Returns:
            list: List of order dictionaries
        
        Raises:
            ValueError: If account number not found or date parameters are invalid
        """
        # Get the encrypted account hash
        account_hash = self.get_account_hash(account_number)
        
        # Build query parameters
        params = {
            'maxResults': max_results
        }
        
        # Add date range if provided
        if from_entered_time and to_entered_time:
            params['fromEnteredTime'] = from_entered_time
            params['toEnteredTime'] = to_entered_time
        elif from_entered_time or to_entered_time:
            raise ValueError("Both 'fromEnteredTime' and 'toEnteredTime' must be provided together")
        
        if status:
            params['status'] = status
        
        logger.info(f"Fetching orders for account {account_number or 'default'}...")
        
        # Make the API call
        endpoint = f'/accounts/{account_hash}/orders'
        orders = self.client._make_request('GET', endpoint, params=params)
        
        logger.info(f"Found {len(orders)} order(s)")
        
        return orders
    
    def get_account_balances(self, account_number: Optional[str] = None) -> Dict:
        """
        Get account balances and details for a specific account.
        
        Args:
            account_number: The plain text account number. If None, uses first account.
        
        Returns:
            dict: Account details including balances, positions, and account information
                  Contains fields like:
                  - currentBalances: Cash balances, buying power, etc.
                  - initialBalances: Initial account balances
                  - projectedBalances: Projected balances
                  - accountId: Account identifier
                  - accountType: Type of account
        
        Raises:
            ValueError: If account number not found
        """
        # Get the encrypted account hash
        account_hash = self.get_account_hash(account_number)
        
        logger.info(f"Fetching account balances for account {account_number or 'default'}...")
        
        # Make the API call
        endpoint = f'/accounts/{account_hash}'
        account_details = self.client._make_request('GET', endpoint)
        
        logger.info("Account balances retrieved successfully")
        
        return account_details
    
    def get_net_liquidity(self, account_number: Optional[str] = None) -> float:
        """
        Get net liquidity (liquidation value) for a specific account.
        
        Net liquidity represents the total value of the account if all positions
        were liquidated at current market prices.
        
        Args:
            account_number: The plain text account number. If None, uses first account.
        
        Returns:
            float: Net liquidity value (liquidation value)
        
        Raises:
            ValueError: If account number not found
        """
        # Get account balances
        balances = self.get_account_balances(account_number)
        
        # Extract net liquidity from currentBalances (liquidationValue)
        securities_account = balances.get('securitiesAccount', {})
        current_balances = securities_account.get('currentBalances', {})
        net_liquidity = current_balances.get('liquidationValue', 0.0)
        
        logger.info(f"Net liquidity for account {account_number or 'default'}: ${net_liquidity:,.2f}")
        
        return net_liquidity

    def get_option_buying_power(self, account_number: Optional[str] = None) -> float:
        """
        Get option buying power for a specific account.
        
        Option buying power represents the amount available for options trading,
        which is typically different from general buying power due to margin requirements.
        
        Args:
            account_number: The plain text account number. If None, uses first account.
        
        Returns:
            float: Option buying power value
        
        Raises:
            ValueError: If account number not found
        """
        # Get account balances
        balances = self.get_account_balances(account_number)
        
        # Extract option buying power from currentBalances
        securities_account = balances.get('securitiesAccount', {})
        current_balances = securities_account.get('currentBalances', {})
        
        # Try different possible field names for option buying power
        option_buying_power = None
        
        # Check for optionBuyingPower (camelCase) - specific option buying power field
        if 'optionBuyingPower' in current_balances:
            option_buying_power = current_balances.get('optionBuyingPower')
            logger.info("Found optionBuyingPower field in account balances")
        # Check for option_buying_power (snake_case)
        elif 'option_buying_power' in current_balances:
            option_buying_power = current_balances.get('option_buying_power')
            logger.info("Found option_buying_power field in account balances")
        # Check for optionBuyingPowerAvailable
        elif 'optionBuyingPowerAvailable' in current_balances:
            option_buying_power = current_balances.get('optionBuyingPowerAvailable')
            logger.info("Found optionBuyingPowerAvailable field in account balances")
        # Use buyingPowerNonMarginableTrade for options (non-marginable trades)
        elif 'buyingPowerNonMarginableTrade' in current_balances:
            option_buying_power = current_balances.get('buyingPowerNonMarginableTrade')
            logger.info("Using buyingPowerNonMarginableTrade for option buying power")
        
        if option_buying_power is None:
            # Fallback to regular buyingPower if option-specific field not available
            option_buying_power = current_balances.get('buyingPower', 0.0)
            logger.warning(f"Option-specific buying power field not found in account balances")
            logger.warning(f"Available balance fields: {list(current_balances.keys())}")
            logger.warning(f"Using regular buyingPower as fallback: ${option_buying_power:,.2f}")
        else:
            logger.info(f"Using option buying power: ${option_buying_power:,.2f}")
        
        logger.info(f"Option buying power for account {account_number or 'default'}: ${option_buying_power:,.2f}")
        
        return float(option_buying_power)

