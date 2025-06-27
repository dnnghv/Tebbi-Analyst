"""
Date utility functions for the Tebbi Analytics application
"""

from datetime import datetime, date
from typing import Optional, Union

def parse_date_range(date_str: str, start_date: Union[date, datetime], end_date: Union[date, datetime]) -> bool:
    """
    Check if a date string falls within a given date range.
    
    Args:
        date_str (str): Date string in ISO format (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)
        start_date (date|datetime): Start date of the range
        end_date (date|datetime): End date of the range
        
    Returns:
        bool: True if date_str falls within the range, False otherwise
    """
    if not date_str:
        return False
        
    try:
        # Convert string to datetime
        if 'T' in date_str:
            # Handle ISO format with time
            parsed_date = datetime.strptime(date_str.split('T')[0], '%Y-%m-%d').date()
        else:
            # Handle date-only format
            parsed_date = datetime.strptime(date_str[:10], '%Y-%m-%d').date()
            
        # Convert start_date and end_date to date if they're datetime
        if isinstance(start_date, datetime):
            start_date = start_date.date()
        if isinstance(end_date, datetime):
            end_date = end_date.date()
            
        # Check if date is within range
        return start_date <= parsed_date <= end_date
        
    except (ValueError, TypeError):
        return False 