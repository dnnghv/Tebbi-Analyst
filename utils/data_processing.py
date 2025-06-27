"""
Data processing utilities for Tebbi Analytics Dashboard
"""

import pandas as pd
from datetime import datetime
from collections import Counter, defaultdict
from typing import Dict, List, Any, Optional
import numpy as np

def get_user_display_name(user_info: dict, user_id: str = None) -> str:
    """Lấy tên hiển thị cho user từ metadata"""
    name = user_info.get('name', '').strip()
    username = user_info.get('username', '').strip()
    email = user_info.get('email', '').strip()
    
    if name:
        return name.upper()
    elif username:
        return username.upper()
    elif email:
        return email.split('@')[0].upper()
    elif user_id:
        return user_id
    else:
        return "UNKNOWN_USER"

def process_threads_data(threads_per_user: dict) -> List[dict]:
    """Process threads data for visualization"""
    data = []
    for user_id, info in threads_per_user.items():
        username = info.get('user_info', {}).get('username', '') or info.get('username', '')
        data.append({
            'User ID': user_id,
            'Username': username,
            'Email': info.get('email', ''),
            'Thread Count': info.get('thread_count', 0),
            'Total Messages': info.get('total_messages', 0),
            'User Messages': info.get('total_user_messages', 0)
        })
    return data

def process_messages_by_date(report_data: dict) -> dict:
    """Process messages data by date"""
    messages_by_date = {}
    if 'user_stats' in report_data and 'thread_conversations' in report_data['user_stats']:
        for conv in report_data['user_stats']['thread_conversations'].values():
            date = conv.get('created_at', '')[:10]
            msg_count = conv.get('total_messages', 0)
            if date:
                messages_by_date[date] = messages_by_date.get(date, 0) + msg_count
    return messages_by_date

def process_user_message_distribution(threads_per_user: dict) -> pd.DataFrame:
    """Process user message distribution data"""
    message_counts = [data.get('total_messages', 0) for data in threads_per_user.values()]
    bins = [1, 2, 3, 5, 10, 20, 50, 100, 200, 500, 1000, float('inf')]
    labels = ['1', '2', '3-4', '5-9', '10-19', '20-49', '50-99', '100-199', '200-499', '500-999', '1000+']
    distribution = Counter()
    for count in message_counts:
        for i, bin_max in enumerate(bins):
            if count <= bin_max:
                distribution[labels[i]] += 1
                break
    return pd.DataFrame(list(distribution.items()), columns=['Range', 'Users'])

def organize_conversations_by_user(conversations_data: List[dict]) -> Dict[str, List[dict]]:
    """Organize conversations by user"""
    users_conversations = defaultdict(list)
    for conv in conversations_data:
        metadata = conv.get('metadata', {})
        user_id = metadata.get('user_id', 'Unknown')
        users_conversations[user_id].append(conv)
    return users_conversations

def process_user_options(users_conversations: dict, threads_per_user: dict) -> dict:
    """Process user options for display"""
    user_options = {}
    for user_id, convs in users_conversations.items():
        user_info = {}
        if user_id in threads_per_user:
            user_info = threads_per_user[user_id].get('user_info', {})
        display_name = get_user_display_name(user_info, user_id)
        user_options[f"{display_name}"] = user_id
    return user_options 