"""
Utility functions for working with orders.
"""
from typing import Optional, Dict
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


def get_actual_fill_credit_from_order(order_details: Dict) -> Optional[float]:
    """
    Extract actual fill credit from filled order.
    
    This function extracts the actual net credit received from a filled order
    by examining the execution legs and calculating the difference between
    SELL and BUY leg prices.
    
    Args:
        order_details: Order dictionary from broker API (must have status='FILLED')
    
    Returns:
        Actual net credit received, or None if not available
    
    Example:
        >>> order = {
        ...     'status': 'FILLED',
        ...     'orderLegCollection': [
        ...         {'legId': 1, 'instruction': 'BUY_TO_OPEN'},
        ...         {'legId': 2, 'instruction': 'SELL_TO_OPEN'}
        ...     ],
        ...     'orderActivityCollection': [{
        ...         'executionLegs': [
        ...             {'legId': 2, 'price': 11.06, 'quantity': 1.0},
        ...             {'legId': 1, 'price': 6.36, 'quantity': 1.0}
        ...         ]
        ...     }]
        ... }
        >>> get_actual_fill_credit_from_order(order)
        4.70
    """
    # Check if order is filled
    if order_details.get('status') != 'FILLED':
        logger.debug(f"Order status is not FILLED: {order_details.get('status')}")
        return None
    
    # Get order legs to map legId to instruction (BUY/SELL)
    order_legs = order_details.get('orderLegCollection', [])
    if not order_legs:
        logger.warning("Order has no orderLegCollection")
        return None
    
    leg_map = {}
    for leg in order_legs:
        leg_id = leg.get('legId')
        instruction = leg.get('instruction', '')
        if leg_id is not None:
            leg_map[leg_id] = instruction
    
    if not leg_map:
        logger.warning("Could not build leg map from orderLegCollection")
        return None
    
    # Get execution activities
    activities = order_details.get('orderActivityCollection', [])
    if not activities:
        logger.warning("Order has no orderActivityCollection")
        return None
    
    # Get first activity (the fill)
    activity = activities[0]
    execution_legs = activity.get('executionLegs', [])
    if not execution_legs:
        logger.warning("Order activity has no executionLegs")
        return None
    
    # Calculate net credit
    total_credit = 0.0
    total_debit = 0.0
    
    for exec_leg in execution_legs:
        leg_id = exec_leg.get('legId')
        price = exec_leg.get('price', 0)
        quantity = exec_leg.get('quantity', 0)
        
        if leg_id is None or price == 0 or quantity == 0:
            logger.warning(f"Skipping invalid execution leg: legId={leg_id}, price={price}, quantity={quantity}")
            continue
        
        instruction = leg_map.get(leg_id, '')
        
        if 'SELL' in instruction or 'SELL_TO_OPEN' in instruction:
            credit = price * quantity
            total_credit += credit
            logger.debug(f"Leg {leg_id} ({instruction}): ${price:.2f} × {quantity} = ${credit:.2f} (credit)")
        elif 'BUY' in instruction or 'BUY_TO_OPEN' in instruction:
            debit = price * quantity
            total_debit += debit
            logger.debug(f"Leg {leg_id} ({instruction}): ${price:.2f} × {quantity} = ${debit:.2f} (debit)")
        else:
            logger.warning(f"Unknown instruction for leg {leg_id}: {instruction}")
    
    if total_credit == 0 and total_debit == 0:
        logger.warning("Could not calculate fill credit: no valid execution legs")
        return None
    
    net_credit = total_credit - total_debit
    
    logger.info(f"Calculated actual fill credit: ${total_credit:.2f} - ${total_debit:.2f} = ${net_credit:.2f}")
    
    return net_credit

