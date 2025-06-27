#!/usr/bin/env python3
"""
Thread Analytics Script - Refactored Version
Tự động lấy và phân tích dữ liệu threads từ API
"""

import requests
import json
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import pandas as pd
from typing import Dict, List, Any, Optional
import argparse
import os
import time
import shutil
from concurrent.futures import ThreadPoolExecutor, as_completed
import streamlit as st


class ThreadAnalytics:
    """
    Refactored ThreadAnalytics class - Simplified and optimized
    """
    
    def __init__(self, base_url: str = None, output_base_dir: str = "reports", max_workers: int = 4):
        try:
            secrets_url = getattr(st.secrets, "THREAD_API_URL", None)
        except Exception:
            secrets_url = None
            raise Exception("Không tìm thấy URL API trong biến môi trường hoặc streamlit secrets")
        self.base_url = secrets_url
        self.output_base_dir = output_base_dir
        self.max_workers = max_workers
        self.session = requests.Session()
        self.session.headers.update({'Content-Type': 'application/json'})
        self._ensure_directory_structure()
    
    def _ensure_directory_structure(self):
        """Tạo cấu trúc thư mục báo cáo"""
        if not os.path.exists(self.output_base_dir):
            os.makedirs(self.output_base_dir)
    
    def _get_output_paths(self, timestamp: str = None):
        """Lấy đường dẫn output theo cấu trúc ngày"""
        if timestamp is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        date_str = timestamp.split('_')[0]
        formatted_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
        
        date_dir = os.path.join(self.output_base_dir, formatted_date)
        reports_dir = os.path.join(date_dir, "reports")
        conversations_dir = os.path.join(date_dir, "conversations")
        
        for dir_path in [date_dir, reports_dir, conversations_dir]:
            if not os.path.exists(dir_path):
                os.makedirs(dir_path)
        
        return {
            'date_dir': date_dir,
            'reports_dir': reports_dir, 
            'conversations_dir': conversations_dir,
            'timestamp': timestamp
        }
    
    # Core API Methods
    def fetch_threads(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """Lấy danh sách threads từ API"""
        url = f"{self.base_url}/threads/search"
        payload = {
            "metadata": {},
            "values": {},
            "status": "idle",
            "limit": limit,
            "offset": offset,
            "sort_by": "updated_at",
            "sort_order": "desc"
        }
        
        try:
            response = self.session.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            return data if isinstance(data, list) else []
        except requests.exceptions.RequestException as e:
            print(f"Lỗi khi gọi API: {e}")
            return []
    
    def fetch_all_threads(self, date_from: str = None, date_to: str = None) -> List[Dict[str, Any]]:
        """Lấy tất cả threads với phân trang và filter ngày"""
        all_threads = []
        offset = 0
        limit = 1000
        
        print("Đang lấy dữ liệu threads...")
        
        while True:
            print(f"  Lấy từ {offset} đến {offset + limit}")
            threads = self.fetch_threads(limit=limit, offset=offset)
            
            if not threads:
                break
            
            # Filter by date if specified
            if date_from or date_to:
                threads = self._filter_threads_by_date(threads, date_from, date_to)
                
            all_threads.extend(threads)
            
            offset += limit
            time.sleep(0.1)  # Avoid server overload
        
        print(f"Đã lấy được {len(all_threads)} threads")
        return all_threads
    
    def _filter_threads_by_date(self, threads: List[Dict[str, Any]], date_from: str = None, date_to: str = None) -> List[Dict[str, Any]]:
        """Filter threads theo khoảng thời gian"""
        if not date_from and not date_to:
            return threads
        
        filtered_threads = []
        for thread in threads:
            updated_at = thread.get('updated_at', '')
            if not updated_at:
                continue
                
            try:
                thread_date = datetime.fromisoformat(updated_at.replace('Z', '+00:00')).date()
                
                if date_from:
                    from_date = datetime.strptime(date_from, '%Y-%m-%d').date()
                    if thread_date < from_date:
                        continue
                
                if date_to:
                    to_date = datetime.strptime(date_to, '%Y-%m-%d').date()
                    if thread_date > to_date:
                        continue
                
                filtered_threads.append(thread)
            except (ValueError, AttributeError):
                continue
        
        return filtered_threads
    
    def get_thread_history(self, thread_id: str) -> List[Dict[str, Any]]:
        """Lấy lịch sử thực thi của một thread"""
        url = f"{self.base_url}/threads/{thread_id}/history"
        
        try:
            response = self.session.get(url)
            response.raise_for_status()
            data = response.json()
            return data if isinstance(data, list) else []
        except requests.exceptions.RequestException as e:
            print(f"Lỗi khi lấy history cho thread {thread_id}: {e}")
            return []
    
    # Analysis Methods
    def analyze_threads_by_date(self, threads: List[Dict[str, Any]]) -> Dict[str, int]:
        """Phân tích số lượng threads theo ngày"""
        threads_by_date = defaultdict(int)
        
        for thread in threads:
            updated_at = thread.get('updated_at')
            if updated_at:
                try:
                    dt = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
                    date_str = dt.strftime('%Y-%m-%d')
                    threads_by_date[date_str] += 1
                except (ValueError, AttributeError):
                    continue
        
        return dict(sorted(threads_by_date.items()))
    
    def get_user_metadata(self, thread_id: str) -> Dict[str, Any]:
        """Lấy thông tin user metadata từ history của thread"""
        history_data = self.get_thread_history(thread_id)
        
        if not history_data:
            return {}
        
        for item in history_data:
            metadata = item.get('metadata', {})
            if metadata.get('username') or metadata.get('email'):
                return {
                    'username': metadata.get('username', ''),
                    'email': metadata.get('email', ''),
                    'name': metadata.get('name', ''),
                    'phoneNumber': metadata.get('phoneNumber', ''),
                    'user_id': metadata.get('user_id', ''),
                }
        
        return {}
    
    def extract_conversation_from_history(self, history_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract cuộc hội thoại từ history data - Optimized with deduplication"""
        if not history_data or not isinstance(history_data, list):
            return []
        
        conversation = []

        for item in history_data:
            if not isinstance(item, dict):
                return []
            
            values = item.get('values', {})
            created_at = item.get('created_at', '')
            
            # Normalize values to list for processing
            values_list = [values] if isinstance(values, dict) else (values if isinstance(values, list) else [])
            
            for value in values_list:
                if not isinstance(value, dict):
                    continue
                
                # Extract messages from various possible locations
                messages = self._extract_messages_from_value(value)
                
                # Process each message
                for msg in messages:
                    processed_msg = self._process_message(msg, created_at)
                    if processed_msg:
                        conversation.append(processed_msg)
            
            break
        
        # Sort by timestamp to maintain chronological order
        conversation.sort(key=lambda x: x.get('timestamp', ''))
        return conversation
    
    def _extract_messages_from_value(self, value: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract messages from a value object"""
        messages = []
        
        # Direct messages
        direct_messages = value.get('messages', [])
        if isinstance(direct_messages, list):
            messages.extend(direct_messages)
        elif direct_messages:
            messages.append(direct_messages)
        
        # Search in other potential message keys
        if not messages:
            for key, val in value.items():
                if any(keyword in key.lower() for keyword in ['message', 'chat', 'conversation', 'dialog']):
                    if isinstance(val, list):
                        messages.extend(val)
                    elif isinstance(val, dict):
                        messages.append(val)
        
        return messages
    
    def _process_message(self, msg: Dict[str, Any], timestamp: str) -> Optional[Dict[str, Any]]:
        """Process a single message and return standardized format"""
        if not isinstance(msg, dict):
            return None
        
        msg_type = msg.get('type', msg.get('role', 'unknown'))
        content = msg.get('content', msg.get('text', msg.get('message', '')))
        
        # Handle various content formats
        if isinstance(content, list):
            content = ' '.join(str(item) for item in content if item)
        elif isinstance(content, dict):
            content = str(content)
        
        # Validate message
        if not content or not str(content).strip() or msg_type not in ['human', 'ai', 'user', 'assistant']:
            return None
        
        role = 'User' if msg_type in ['human', 'user'] else 'AI'
        
        return {
            'timestamp': timestamp,
            'role': role,
            'content': str(content).strip()
        }
    
    def analyze_users_comprehensive(self, threads: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Phân tích comprehensive users với conversation data - Optimized"""
        user_threads = defaultdict(list)
        user_details = {}
        thread_conversations = {}
        total_users = set()
        
        print("\n👥 Đang thu thập thông tin user metadata và conversations...")
        
        for i, thread in enumerate(threads):
            if (i + 1) % 50 == 0:
                print(f"  Đã xử lý {i + 1}/{len(threads)} threads...")
            
            metadata = thread.get('metadata', {})
            user_id = metadata.get('user_id')
            thread_id = thread.get('thread_id')
            
            if not user_id or not thread_id:
                continue
            
            user_threads[user_id].append(thread_id)
            total_users.add(user_id)
            
            # Get user metadata if not exists
            if user_id not in user_details:
                user_metadata = self.get_user_metadata(thread_id)
                user_details[user_id] = user_metadata if user_metadata else {
                    'username': '', 'email': '', 'name': '', 'phoneNumber': '', 'userId': user_id
                }
            
            # Get conversation content
            conversation_data = self._get_thread_conversation_data(thread, thread_id)
            thread_conversations[thread_id] = conversation_data
        
        # Build user statistics
        user_stats = self._build_user_statistics(user_threads, user_details, thread_conversations, total_users)
        
        print(f"✅ Thu thập xong metadata cho {len(user_details)} users và {len(thread_conversations)} conversations")
        return user_stats
    
    def _get_thread_conversation_data(self, thread: Dict[str, Any], thread_id: str) -> Dict[str, Any]:
        """Get conversation data for a single thread"""
        history_data = self.get_thread_history(thread_id)
        conversation = self.extract_conversation_from_history(history_data)
        
        if conversation:
            user_messages = [msg for msg in conversation if msg.get('role') == 'User']
            ai_messages = [msg for msg in conversation if msg.get('role') == 'AI']
            
            return {
                'total_messages': len(conversation),
                'user_messages': len(user_messages),
                'ai_messages': len(ai_messages),
                'first_message': conversation[0].get('content', '')[:100] + '...' if conversation else '',
                'last_message': conversation[-1].get('content', '')[:100] + '...' if conversation else '',
                'created_at': thread.get('created_at', ''),
                'updated_at': thread.get('updated_at', ''),
                'user_id': thread.get('metadata', {}).get('user_id', ''),
                'conversation': conversation
            }
        else:
            return {
                'total_messages': 0, 'user_messages': 0, 'ai_messages': 0,
                'first_message': 'No conversation found', 'last_message': 'No conversation found',
                'created_at': thread.get('created_at', ''), 'updated_at': thread.get('updated_at', ''),
                'user_id': thread.get('metadata', {}).get('user_id', ''), 'conversation': []
            }
    
    def _build_user_statistics(self, user_threads: Dict, user_details: Dict, thread_conversations: Dict, total_users: set) -> Dict[str, Any]:
        """Build comprehensive user statistics"""
        user_stats = {
            'total_users': len(total_users),
            'threads_per_user': {},
            'user_thread_count': Counter(),
            'user_details': user_details,
            'thread_conversations': thread_conversations
        }
        
        for user_id, thread_ids in user_threads.items():
            thread_count = len(thread_ids)
            # Calculate total messages for this user
            total_messages = sum(thread_conversations.get(tid, {}).get('total_messages', 0) for tid in thread_ids)
            total_user_messages = sum(thread_conversations.get(tid, {}).get('user_messages', 0) for tid in thread_ids)

            user_stats['threads_per_user'][user_id] = {
                'thread_count': thread_count,
                'thread_ids': thread_ids,
                'user_info': user_details.get(user_id, {}),
                'total_messages': total_messages,
                'total_user_messages': total_user_messages,
                'avg_messages_per_thread': round(total_messages / thread_count, 2) if thread_count > 0 else 0
            }
            user_stats['user_thread_count'][thread_count] += 1
        
        return user_stats
    
    # Report Generation Methods
    def generate_report(self, threads: List[Dict[str, Any]], include_tool_analysis: bool = True) -> Dict[str, Any]:
        """Tạo báo cáo tổng hợp - Optimized"""
        print("\nĐang phân tích dữ liệu...")
        
        total_threads = len(threads)
        threads_by_date = self.analyze_threads_by_date(threads)
        user_stats = self.analyze_users_comprehensive(threads)
        
        avg_threads_per_user = total_threads / user_stats['total_users'] if user_stats['total_users'] > 0 else 0
        
        # Calculate message statistics from user_stats
        total_messages = 0
        total_user_messages = 0
        total_ai_messages = 0
        
        for user_data in user_stats['threads_per_user'].values():
            total_messages += user_data.get('total_messages', 0)
            total_user_messages += user_data.get('total_user_messages', 0)
        
        total_ai_messages = total_messages - total_user_messages
        avg_messages_per_user = total_messages / user_stats['total_users'] if user_stats['total_users'] > 0 else 0
        avg_messages_per_thread = total_messages / total_threads if total_threads > 0 else 0
        
        # Calculate peak day statistics
        peak_day = ''
        peak_threads = 0
        if threads_by_date:
            peak_day = max(threads_by_date.items(), key=lambda x: x[1])
            peak_threads = peak_day[1]
            peak_day = peak_day[0]
        
        report = {
            'summary': {
                'total_threads': total_threads,
                'total_users': user_stats['total_users'],
                'avg_threads_per_user': round(avg_threads_per_user, 2),
                'total_messages': total_messages,
                'user_messages': total_user_messages,
                'ai_messages': total_ai_messages,
                'avg_messages_per_user': round(avg_messages_per_user, 2),
                'avg_messages_per_thread': round(avg_messages_per_thread, 2),
                'peak_day': peak_day,
                'peak_threads': peak_threads,
                'analysis_date': datetime.now().isoformat()
            },
            'threads_by_date': threads_by_date,
            'user_stats': user_stats,
            'threads_per_user': user_stats['threads_per_user'],  # For backward compatibility
            'top_users': self.get_top_users(user_stats['threads_per_user'])
        }
        
        # Thêm phân tích tool calling nếu được yêu cầu
        if include_tool_analysis:
            tool_calling_stats = self.analyze_tool_calling_for_all_threads(threads)
            report['tool_calling_stats'] = tool_calling_stats
            
            # Cập nhật summary với tool calling info
            report['summary'].update({
                'total_tool_calls': tool_calling_stats['total_tool_calls'],
                'create_lead_calls': tool_calling_stats['create_lead'],
                'send_html_email_calls': tool_calling_stats['send_html_email'],
                'threads_with_create_lead': tool_calling_stats['threads_with_create_lead'],
                'threads_with_send_html_email': tool_calling_stats['threads_with_send_html_email']
            })
        
        return report
    
    def get_top_users(self, threads_per_user: Dict[str, Dict], top_n: int = 10) -> List[Dict[str, Any]]:
        """Lấy top users có nhiều threads nhất với metadata"""
        sorted_users = sorted(
            threads_per_user.items(),
            key=lambda x: x[1]['thread_count'],
            reverse=True
        )
        
        return [
            {
                'user_id': user_id,
                'thread_count': data['thread_count'],
                'thread_ids': data['thread_ids'],
                'user_info': data.get('user_info', {})
            }
            for user_id, data in sorted_users[:top_n]
        ]
    
    # File Export Methods
    def save_report(self, report: Dict[str, Any], filename: str = None):
        """Lưu báo cáo JSON vào file"""
        paths = self._get_output_paths()
        
        if filename is None:
            filename = f"thread_analytics_report_{paths['timestamp']}.json"
        elif not filename.endswith('.json'):
            filename = f"{filename}_{paths['timestamp']}.json"
        
        filepath = os.path.join(paths['reports_dir'], filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        print(f"\n📄 Đã lưu báo cáo JSON vào: {filepath}")
        return filepath
    
    def save_report_as_text(self, report: Dict[str, Any], filename: str = None):
        """Lưu báo cáo dạng text với cấu trúc thư mục theo ngày"""
        paths = self._get_output_paths()
        
        if filename is None:
            filename = f"thread_analytics_report_{paths['timestamp']}.txt"
        elif not filename.endswith('.txt'):
            filename = f"{filename}_{paths['timestamp']}.txt"
        
        filepath = os.path.join(paths['reports_dir'], filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            summary = report['summary']
        
            f.write("="*60 + "\n")
            f.write("📊 BÁO CÁO PHÂN TÍCH THREADS\n")
            f.write("="*60 + "\n")
            f.write(f"📅 Thời gian phân tích: {summary['analysis_date']}\n")
            f.write(f"💬 Tổng số threads: {summary['total_threads']:,}\n")
            f.write(f"👥 Tổng số users: {summary['total_users']:,}\n")
            f.write(f"📈 Trung bình threads/user: {summary['avg_threads_per_user']}\n\n")
        
            # Threads theo ngày
            f.write("📅 THREADS THEO NGÀY (10 ngày gần nhất):\n")
            f.write("-" * 40 + "\n")
            threads_by_date = report['threads_by_date']
            recent_dates = list(threads_by_date.items())[-10:]
            for date, count in recent_dates:
                f.write(f"{date}: {count:,} threads\n")
        
            # Top users
            f.write("\n🏆 TOP 10 USERS CÓ NHIỀU THREADS NHẤT:\n")
            f.write("-" * 80 + "\n")
            for i, user in enumerate(report['top_users'], 1):
                user_info = user.get('user_info', {})
                username = user_info.get('username', 'N/A')
                email = user_info.get('email', 'N/A')
                name = user_info.get('name', 'N/A')
                phone = user_info.get('phoneNumber', 'N/A')
                
                # Lấy conversation stats từ user_stats
                user_id = user['user_id']
                user_stats = report['user_stats']['threads_per_user'].get(user_id, {})
                total_messages = user_stats.get('total_messages', 0)
                total_user_messages = user_stats.get('total_user_messages', 0)
                avg_messages = user_stats.get('avg_messages_per_thread', 0)
                
                f.write(f"{i:2d}. [{user['thread_count']} threads, {total_messages} messages] {username}\n")
                f.write(f"    📧 Email: {email}\n")
                f.write(f"    👤 Name: {name}\n")
                f.write(f"    📱 Phone: {phone if phone else 'N/A'}\n")
                f.write(f"    💬 Messages: {total_user_messages} user, {total_messages-total_user_messages} AI (avg: {avg_messages}/thread)\n")
                f.write(f"    🆔 User ID: {user['user_id'][:8]}...{user['user_id'][-8:]}\n\n")
        
        print(f"\n📄 Đã lưu báo cáo dạng text vào: {filepath}")
        return filepath
    
    def export_to_csv(self, report: Dict[str, Any]):
        """Xuất dữ liệu ra CSV"""
        paths = self._get_output_paths()
        timestamp = paths['timestamp']
        
        # Export threads by date
        df_dates = pd.DataFrame(list(report['threads_by_date'].items()), 
                               columns=['date', 'thread_count'])
        date_file = os.path.join(paths['reports_dir'], f"threads_by_date_{timestamp}.csv")
        df_dates.to_csv(date_file, index=False)
        print(f"📅 Đã xuất dữ liệu theo ngày: {date_file}")
        
        # Export user stats
        user_data = []
        for user_id, data in report['user_stats']['threads_per_user'].items():
            user_info = data.get('user_info', {})
            user_data.append({
                'user_id': user_id,
                'username': user_info.get('username', ''),
                'email': user_info.get('email', ''),
                'name': user_info.get('name', ''),
                'phoneNumber': user_info.get('phoneNumber', ''),
                'thread_count': data['thread_count'],
                'total_messages': data.get('total_messages', 0),
                'total_user_messages': data.get('total_user_messages', 0),
                'avg_messages_per_thread': data.get('avg_messages_per_thread', 0)
            })
        
        df_users = pd.DataFrame(user_data)
        user_file = os.path.join(paths['reports_dir'], f"user_stats_{timestamp}.csv")
        df_users.to_csv(user_file, index=False)
        print(f"👥 Đã xuất thống kê users: {user_file}")
        
        return {'date_file': date_file, 'user_file': user_file}
    
    def export_conversations_by_user_thread(self, threads: List[Dict[str, Any]]):
        """Export conversations theo cấu trúc user/thread - Simplified"""
        paths = self._get_output_paths()
        base_conv_dir = paths['conversations_dir']
        
        
        exported_count = 0
        user_summary = {}
        
        for i, thread in enumerate(threads):
            thread_id = thread['thread_id']
            metadata = thread.get('metadata', {})
            user_id = metadata.get('user_id', 'unknown_user')
            
            print(f"  {i+1}/{len(threads)}: {thread_id}")
            
            # Create user directory
            user_dir = os.path.join(base_conv_dir, f"user_{user_id}")
            if not os.path.exists(user_dir):
                os.makedirs(user_dir)
            
            # Get user metadata
            user_metadata = self.get_user_metadata(thread_id)
            if user_id not in user_summary:
                user_summary[user_id] = {
                    'threads': [],
                    'total_messages': 0,
                    'user_info': user_metadata
                }
            
            # Get conversation
            history_data = self.get_thread_history(thread_id)
            conversation = self.extract_conversation_from_history(history_data)
            
            if conversation:
                exported_count += 1
                
                # Write thread file
                thread_filename = f"thread_{thread_id}.txt"
                thread_filepath = os.path.join(user_dir, thread_filename)
                
                self._write_thread_conversation_file(thread_filepath, thread, conversation, user_metadata, user_id)
                
                # Update summary
                user_summary[user_id]['threads'].append({
                    'thread_id': thread_id,
                    'message_count': len(conversation),
                    'file_path': thread_filepath,
                    'created_at': thread.get('created_at', ''),
                    'updated_at': thread.get('updated_at', '')
                })
                user_summary[user_id]['total_messages'] += len(conversation)
        
        # Create user summaries
        self._create_user_summaries(user_summary, base_conv_dir)
        
        print(f"✅ Đã xuất {exported_count} conversations cho {len(user_summary)} users")
        return {
            'exported_count': exported_count,
            'users_count': len(user_summary),
            'base_dir': base_conv_dir
        }
    
    def _write_thread_conversation_file(self, filepath: str, thread: Dict, conversation: List, user_metadata: Dict, user_id: str):
        """Write conversation to a thread file"""
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write("="*80 + "\n")
            f.write(f"💬 THREAD CONVERSATION: {thread['thread_id']}\n")
            f.write("="*80 + "\n")
            f.write(f"📅 Created: {thread.get('created_at', 'N/A')}\n")
            f.write(f"🔄 Updated: {thread.get('updated_at', 'N/A')}\n")
            f.write(f"💬 Total messages: {len(conversation)}\n")
            f.write(f"👤 User ID: {user_id}\n")
            
            # User metadata
            if user_metadata:
                f.write(f"\n👤 User Information:\n")
                f.write(f"   - Username: {user_metadata.get('username', 'N/A')}\n")
                f.write(f"   - Email: {user_metadata.get('email', 'N/A')}\n")
                f.write(f"   - Name: {user_metadata.get('name', 'N/A')}\n")
                f.write(f"   - Phone: {user_metadata.get('phoneNumber', 'N/A')}\n")
            
            f.write("\n" + "="*80 + "\n")
            f.write("CONVERSATION HISTORY:\n")
            f.write("="*80 + "\n")
            
            # Write messages
            for j, msg in enumerate(conversation, 1):
                role = msg['role']
                content = str(msg['content'])
                timestamp = msg.get('timestamp', '')
                
                # Format role display
                if role == "User":
                    display_name = (user_metadata.get('name', '') or 
                                  user_metadata.get('username', '') or 
                                  user_metadata.get('email', '').split('@')[0] if user_metadata.get('email') else 'USER')
                    icon = f"👤 {display_name.upper()}"
                else:
                    icon = "🤖 AI"
                
                f.write(f"\n[{j:03d}] {icon}")
                if timestamp:
                    try:
                        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                        formatted_time = dt.strftime('%Y-%m-%d %H:%M:%S')
                        f.write(f" - {formatted_time}")
                    except:
                        f.write(f" - {timestamp}")
                f.write("\n")
                
                # Write content with line wrapping
                self._write_wrapped_content(f, content)
                
                if j < len(conversation):
                    f.write("    " + "·"*50 + "\n")
    
    def _write_wrapped_content(self, f, content: str):
        """Write content with proper line wrapping"""
        lines = content.split('\n')
        for line in lines:
            if len(line) <= 70:
                f.write(f"    {line}\n")
            else:
                words = line.split(' ')
                current_line = "    "
                for word in words:
                    if len(current_line + word) <= 70:
                        current_line += word + " "
                    else:
                        f.write(current_line.rstrip() + "\n")
                        current_line = "    " + word + " "
                if current_line.strip():
                    f.write(current_line.rstrip() + "\n")
    
    def _create_user_summaries(self, user_summary: Dict, base_conv_dir: str):
        """Create summary files for each user"""
        print(f"📊 Tạo user summaries...")
        for user_id, summary in user_summary.items():
            user_dir = os.path.join(base_conv_dir, f"user_{user_id}")
            summary_file = os.path.join(user_dir, "user_summary.txt")

            # Lấy thống kê thời gian nếu có
            threads_per_user = getattr(self, 'user_stats', {}).get('threads_per_user', {})
            user_stats = threads_per_user.get(user_id, {}) if threads_per_user else {}

            with open(summary_file, 'w', encoding='utf-8') as f:
                user_info = summary['user_info']
                f.write("="*60 + "\n")
                f.write(f"👤 USER SUMMARY: {user_id}\n")
                f.write("="*60 + "\n")
                f.write(f"📅 Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"🧵 Total threads: {len(summary['threads'])}\n")
                f.write(f"💬 Total messages: {summary['total_messages']}\n")
                if user_stats:
                    f.write(f"⏳ User lifetime: {user_stats.get('user_lifetime_human', 'N/A')}\n")
                    f.write(f"🕒 Tổng thời gian các threads: {user_stats.get('total_thread_duration_human', 'N/A')}\n")
                    f.write(f"📅 Thread đầu tiên: {user_stats.get('first_thread_time', 'N/A')}\n")
                    f.write(f"📅 Thread cuối cùng: {user_stats.get('last_thread_time', 'N/A')}\n")
                    f.write(f"📈 Avg messages/thread: {user_stats.get('avg_messages_per_thread', 0):.1f}\n")
                f.write(f"\n👤 User Information:\n")
                f.write(f"   - Username: {user_info.get('username', 'N/A')}\n")
                f.write(f"   - Email: {user_info.get('email', 'N/A')}\n")
                f.write(f"   - Name: {user_info.get('name', 'N/A')}\n")
                f.write(f"   - Phone: {user_info.get('phoneNumber', 'N/A')}\n")
                f.write(f"\n🧵 THREAD LIST:\n")
                f.write("-" * 40 + "\n")
                for i, thread_info in enumerate(summary['threads'], 1):
                    f.write(f"{i:2d}. {thread_info['thread_id']}\n")
                    f.write(f"    💬 Messages: {thread_info['message_count']}\n")
                    f.write(f"    📅 Created: {thread_info['created_at']}\n")
                    f.write(f"    📄 File: {os.path.basename(thread_info['file_path'])}\n\n")
    
    def print_summary(self, report: Dict[str, Any]):
        """In tóm tắt báo cáo"""
        summary = report['summary']
        
        print("\n" + "="*60)
        print("📊 BÁO CÁO PHÂN TÍCH THREADS")
        print("="*60)
        print(f"📅 Thời gian phân tích: {summary['analysis_date']}")
        print(f"💬 Tổng số threads: {summary['total_threads']:,}")
        print(f"👥 Tổng số users: {summary['total_users']:,}")
        print(f"📈 Trung bình threads/user: {summary['avg_threads_per_user']}")
        
        print("\n📅 THREADS THEO NGÀY (10 ngày gần nhất):")
        print("-" * 40)
        threads_by_date = report['threads_by_date']
        recent_dates = list(threads_by_date.items())[-10:]
        for date, count in recent_dates:
            print(f"{date}: {count:,} threads")
        
        print("\n🏆 TOP 10 USERS CÓ NHIỀU THREADS NHẤT:")
        print("-" * 80)
        for i, user in enumerate(report['top_users'], 1):
            user_info = user.get('user_info', {})
            username = user_info.get('username', 'N/A')
            email = user_info.get('email', 'N/A')
            name = user_info.get('name', 'N/A')
            
            print(f"{i:2d}. [{user['thread_count']} threads] {username}")
            print(f"    📧 Email: {email}")
            print(f"    👤 Name: {name}")
            print(f"    🆔 User ID: {user['user_id'][:8]}...{user['user_id'][-8:]}")
            print()

    def _process_single_thread(self, thread: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Xử lý một thread đơn lẻ"""
        thread_id = thread.get('thread_id')
        if not thread_id:
            return None
            
        history_data = self.get_thread_history(thread_id)
        if not history_data:
            return None
            
        conversation = self.extract_conversation_from_history(history_data)
        if not conversation:
            return None
            
        return {
            'thread_id': thread_id,
            'created_at': thread.get('created_at', ''),
            'updated_at': thread.get('updated_at', ''),
            'message_count': len(conversation),
            'conversation': conversation,
            'metadata': thread.get('metadata', {})
        }

    def process_threads_parallel(self, threads: List[Dict[str, Any]], progress_bar=None, status_text=None) -> List[Dict[str, Any]]:
        """Xử lý nhiều threads song song"""
        results = []
        total = len(threads)
        processed = 0

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_thread = {executor.submit(self._process_single_thread, thread): thread for thread in threads}
            
            for future in as_completed(future_to_thread):
                processed += 1
                if progress_bar is not None:
                    progress_bar.progress(processed / total)
                if status_text is not None:
                    status_text.text(f"Đang xử lý: {processed}/{total} threads...")
                
                try:
                    result = future.result()
                    if result:
                        results.append(result)
                except Exception as e:
                    print(f"Thread xử lý gặp lỗi: {str(e)}")
                    continue

        return results

    def get_conversations_for_threads(self, threads: List[dict], progress_container=None) -> List[dict]:
        """Lấy conversations cho các threads với xử lý song song"""
        if progress_container:
            with progress_container:
                st.info(f"💬 Đang lấy conversations cho {len(threads)} threads...")
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                conversations = self.process_threads_parallel(threads, progress_bar, status_text)
                
                if conversations:
                    st.success(f"✅ Đã tải {len(conversations)} conversations")
                else:
                    st.warning("⚠️ Không tìm thấy conversations")
                
                return conversations
        else:
            return self.process_threads_parallel(threads)

    def analyze_tool_calling_stats(self, history_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Phân tích thống kê tool calling của create_lead và send_email từ thread history
        
        Args:
            history_data: Danh sách history data từ thread
            
        Returns:
            Dict với thống kê tool calling
        """
        tool_stats = {
            'create_lead': 0,
            'send_html_email': 0,
            'total_tool_calls': 0,
            'tool_calls_detail': []
        }
        
        if not history_data or not isinstance(history_data, list):
            return tool_stats
        
        processed_call_ids = set()  # Tránh duplicate
        
        for item in history_data:
            # Lấy messages từ values
            values = item.get('values', {})
            messages = values.get('messages', [])
            
            if not isinstance(messages, list):
                continue
                
            for message in messages:
                if not isinstance(message, dict):
                    continue
                    
                # Ưu tiên kiểm tra tool_calls trong additional_kwargs trước
                additional_kwargs = message.get('additional_kwargs', {})
                tool_calls = additional_kwargs.get('tool_calls', [])
                
                if tool_calls and isinstance(tool_calls, list):
                    # Xử lý tool_calls từ additional_kwargs
                    for tool_call in tool_calls:
                        if not isinstance(tool_call, dict):
                            continue
                            
                        function_info = tool_call.get('function', {})
                        function_name = function_info.get('name', '')
                        call_id = tool_call.get('id', '')
                        
                        # Tránh duplicate bằng call_id
                        if function_name and call_id and call_id not in processed_call_ids:
                            processed_call_ids.add(call_id)
                            tool_stats['total_tool_calls'] += 1
                            
                            # Đếm specific tools
                            if function_name == 'create_lead':
                                tool_stats['create_lead'] += 1
                            elif function_name == 'send_html_email':
                                tool_stats['send_html_email'] += 1
                            
                            # Lưu detail
                            tool_detail = {
                                'function_name': function_name,
                                'call_id': call_id,
                                'arguments': function_info.get('arguments', ''),
                                'timestamp': item.get('created_at', ''),
                                'message_type': message.get('type', ''),
                                'message_id': message.get('id', '')
                            }
                            tool_stats['tool_calls_detail'].append(tool_detail)
                else:
                    # Fallback: Kiểm tra tool_calls trực tiếp trong message nếu không có trong additional_kwargs
                    direct_tool_calls = message.get('tool_calls', [])
                    if isinstance(direct_tool_calls, list):
                        for tool_call in direct_tool_calls:
                            if not isinstance(tool_call, dict):
                                continue
                                
                            function_name = tool_call.get('name', '')
                            call_id = tool_call.get('id', '')
                            
                            # Tránh duplicate bằng call_id
                            if function_name and call_id and call_id not in processed_call_ids:
                                processed_call_ids.add(call_id)
                                tool_stats['total_tool_calls'] += 1
                                
                                # Đếm specific tools
                                if function_name == 'create_lead':
                                    tool_stats['create_lead'] += 1
                                elif function_name == 'send_html_email':
                                    tool_stats['send_html_email'] += 1
                                
                                # Lưu detail
                                tool_detail = {
                                    'function_name': function_name,
                                    'call_id': call_id,
                                    'arguments': str(tool_call.get('args', {})),
                                    'timestamp': item.get('created_at', ''),
                                    'message_type': message.get('type', ''),
                                    'message_id': message.get('id', '')
                                }
                                tool_stats['tool_calls_detail'].append(tool_detail)
        
        return tool_stats
    
    def analyze_tool_calling_for_all_threads(self, threads: List[Dict[str, Any]], progress_container=None) -> Dict[str, Any]:
        """
        Phân tích tool calling cho tất cả threads
        
        Args:
            threads: Danh sách threads
            progress_container: Container để hiển thị progress (optional)
            
        Returns:
            Dict với thống kê tổng hợp tool calling
        """
        print("\n🔧 Đang phân tích tool calling statistics...")
        
        total_stats = {
            'create_lead': 0,
            'send_html_email': 0,
            'total_tool_calls': 0,
            'threads_with_create_lead': 0,
            'threads_with_send_html_email': 0,
            'threads_with_any_tool': 0,
            'tool_calls_by_thread': {},
            'tool_calls_by_date': defaultdict(lambda: {
                'create_lead': 0, 'send_html_email': 0, 'total': 0
            }),
            'detailed_calls': []
        }
        
        if progress_container:
            progress_bar = progress_container.progress(0)
            status_text = progress_container.empty()
        
        for i, thread in enumerate(threads):
            thread_id = thread.get('thread_id', '')
            
            if progress_container:
                progress = (i + 1) / len(threads)
                progress_bar.progress(progress)
                status_text.text(f"Đang phân tích thread {i + 1}/{len(threads)}: {thread_id}")
            
            if (i + 1) % 50 == 0:
                print(f"  Đã xử lý {i + 1}/{len(threads)} threads...")
            
            if not thread_id:
                continue
                
            # Lấy history data
            history_data = self.get_thread_history(thread_id)
            
            # Phân tích tool calling cho thread này
            thread_tool_stats = self.analyze_tool_calling_stats(history_data)
            
            # Cập nhật total stats với safe access
            total_stats['create_lead'] += thread_tool_stats.get('create_lead', 0)
            total_stats['send_html_email'] += thread_tool_stats.get('send_html_email', 0)
            total_stats['total_tool_calls'] += thread_tool_stats.get('total_tool_calls', 0)
            
            # Đếm threads có tool calls với safe access
            if thread_tool_stats.get('create_lead', 0) > 0:
                total_stats['threads_with_create_lead'] += 1
            if thread_tool_stats.get('send_html_email', 0) > 0:
                total_stats['threads_with_send_html_email'] += 1
            if thread_tool_stats.get('total_tool_calls', 0) > 0:
                total_stats['threads_with_any_tool'] += 1
            
            # Lưu stats cho từng thread
            total_stats['tool_calls_by_thread'][thread_id] = {
                'thread_metadata': thread.get('metadata', {}),
                'created_at': thread.get('created_at', ''),
                'updated_at': thread.get('updated_at', ''),
                'tool_stats': thread_tool_stats
            }
            
            # Thống kê theo ngày
            created_at = thread.get('created_at', '')
            if created_at:
                try:
                    dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    date_str = dt.strftime('%Y-%m-%d')
                    
                    total_stats['tool_calls_by_date'][date_str]['create_lead'] += thread_tool_stats.get('create_lead', 0)
                    total_stats['tool_calls_by_date'][date_str]['send_html_email'] += thread_tool_stats.get('send_html_email', 0)
                    total_stats['tool_calls_by_date'][date_str]['total'] += thread_tool_stats.get('total_tool_calls', 0)
                except (ValueError, AttributeError):
                    pass
            
            # Thêm detailed calls với safe access
            for detail in thread_tool_stats.get('tool_calls_detail', []):
                detail['thread_id'] = thread_id
                total_stats['detailed_calls'].append(detail)
        
        # Convert defaultdict to regular dict
        total_stats['tool_calls_by_date'] = dict(total_stats['tool_calls_by_date'])
        
        if progress_container:
            progress_bar.progress(1.0)
            status_text.text("✅ Hoàn thành phân tích tool calling!")
        
        print(f"✅ Phân tích tool calling hoàn thành!")
        print(f"   📊 Tổng số tool calls: {total_stats['total_tool_calls']}")
        print(f"   🎯 create_lead: {total_stats['create_lead']}")
        print(f"   📧 send_html_email: {total_stats['send_html_email']}")
        print(f"   📈 Threads có create_lead: {total_stats['threads_with_create_lead']}")
        print(f"   📧 Threads có send_html_email: {total_stats['threads_with_send_html_email']}")
        
        return total_stats

    def export_tool_calling_to_csv(self, tool_calling_stats: Dict[str, Any]):
        """Xuất thống kê tool calling ra file CSV"""
        paths = self._get_output_paths()
        
        # 1. Xuất summary stats
        summary_data = {
            'Metric': [
                'Total Tool Calls',
                'Create Lead Calls', 
                'Send HTML Email Calls',
                'Threads with Create Lead',
                'Threads with Send HTML Email',
                'Threads with Any Tool'
            ],
            'Count': [
                tool_calling_stats['total_tool_calls'],
                tool_calling_stats['create_lead'],
                tool_calling_stats['send_html_email'],
                tool_calling_stats['threads_with_create_lead'],
                tool_calling_stats['threads_with_send_html_email'],
                tool_calling_stats['threads_with_any_tool']
            ]
        }
        
        summary_df = pd.DataFrame(summary_data)
        summary_filename = os.path.join(paths['reports_dir'], f"tool_calling_summary_{paths['timestamp']}.csv")
        summary_df.to_csv(summary_filename, index=False, encoding='utf-8-sig')
        print(f"📄 Xuất summary tool calling: {summary_filename}")
        
        # 2. Xuất detailed calls
        if tool_calling_stats['detailed_calls']:
            detailed_df = pd.DataFrame(tool_calling_stats['detailed_calls'])
            detailed_filename = os.path.join(paths['reports_dir'], f"tool_calling_detailed_{paths['timestamp']}.csv")
            detailed_df.to_csv(detailed_filename, index=False, encoding='utf-8-sig')
            print(f"📄 Xuất detailed tool calls: {detailed_filename}")
        
        # 3. Xuất stats by date
        if tool_calling_stats['tool_calls_by_date']:
            date_data = []
            for date, stats in tool_calling_stats['tool_calls_by_date'].items():
                date_data.append({
                    'Date': date,
                    'Create Lead': stats['create_lead'],
                    'Send HTML Email': stats['send_html_email'],
                    'Total': stats['total']
                })
            
            date_df = pd.DataFrame(date_data)
            date_df = date_df.sort_values('Date')
            date_filename = os.path.join(paths['reports_dir'], f"tool_calling_by_date_{paths['timestamp']}.csv")
            date_df.to_csv(date_filename, index=False, encoding='utf-8-sig')
            print(f"📄 Xuất tool calling by date: {date_filename}")
        
        # 4. Xuất stats by thread
        if tool_calling_stats['tool_calls_by_thread']:
            thread_data = []
            for thread_id, thread_info in tool_calling_stats['tool_calls_by_thread'].items():
                thread_stats = thread_info['tool_stats']
                metadata = thread_info['thread_metadata']
                
                thread_data.append({
                    'Thread ID': thread_id,
                    'User ID': metadata.get('user_id', ''),
                    'Username': metadata.get('username', ''),
                    'Email': metadata.get('email', ''),
                    'Created At': thread_info.get('created_at', ''),
                    'Updated At': thread_info.get('updated_at', ''),
                    'Create Lead Calls': thread_stats['create_lead'],
                    'Send HTML Email Calls': thread_stats['send_html_email'],
                    'Total Tool Calls': thread_stats['total_tool_calls']
                })
            
            thread_df = pd.DataFrame(thread_data)
            thread_df = thread_df.sort_values('Total Tool Calls', ascending=False)
            thread_filename = os.path.join(paths['reports_dir'], f"tool_calling_by_thread_{paths['timestamp']}.csv")
            thread_df.to_csv(thread_filename, index=False, encoding='utf-8-sig')
            print(f"📄 Xuất tool calling by thread: {thread_filename}")
        
        return {
            'summary_file': summary_filename,
            'detailed_file': detailed_filename if tool_calling_stats['detailed_calls'] else None,
            'date_file': date_filename if tool_calling_stats['tool_calls_by_date'] else None,
            'thread_file': thread_filename if tool_calling_stats['tool_calls_by_thread'] else None
        }


def cleanup_output_files(keep_latest: int = 3, base_dir: str = "reports"):
    """Dọn dẹp các files output cũ theo cấu trúc thư mục mới"""
    print(f"\n🧹 Dọn dẹp thư mục {base_dir}, giữ lại {keep_latest} ngày gần nhất...")
    
    if not os.path.exists(base_dir):
        print(f"⚠️ Thư mục {base_dir} không tồn tại")
        return
    
    # Get list of date directories
    date_dirs = []
    for item in os.listdir(base_dir):
        item_path = os.path.join(base_dir, item)
        if os.path.isdir(item_path) and len(item) == 10 and item.count('-') == 2:  # YYYY-MM-DD format
            try:
                date_obj = datetime.strptime(item, '%Y-%m-%d')
                date_dirs.append((date_obj, item_path))
            except ValueError:
                continue
    
    # Sort by date (newest first)
    date_dirs.sort(key=lambda x: x[0], reverse=True)
    
    cleaned_count = 0
    if len(date_dirs) > keep_latest:
        dirs_to_remove = date_dirs[keep_latest:]
        
        for date_obj, dir_path in dirs_to_remove:
            try:
                shutil.rmtree(dir_path)
                print(f"  ❌ Đã xóa thư mục: {os.path.basename(dir_path)}")
                cleaned_count += 1
            except Exception as e:
                print(f"  ⚠️ Không thể xóa {dir_path}: {e}")
    
    print(f"✅ Đã dọn dẹp {cleaned_count} thư mục ngày")
    
    # Show remaining directories
    remaining_dirs = [os.path.basename(d[1]) for d in date_dirs[:keep_latest]]
    if remaining_dirs:
        print(f"📁 Còn lại {len(remaining_dirs)} thư mục: {', '.join(remaining_dirs)}")


def main():
    parser = argparse.ArgumentParser(description='Thread Analytics Tool - Refactored')
    parser.add_argument('--max-threads', type=int, help='Số lượng threads tối đa để phân tích')
    parser.add_argument('--date-from', help='Ngày bắt đầu (YYYY-MM-DD)')
    parser.add_argument('--date-to', help='Ngày kết thúc (YYYY-MM-DD)')
    parser.add_argument('--export-csv', action='store_true', help='Xuất dữ liệu ra CSV')
    parser.add_argument('--export-conversations', type=int, default=0, help='Xuất N cuộc hội thoại ra file TXT')
    parser.add_argument('--output', help='Tên file để lưu báo cáo (không cần extension)')
    parser.add_argument('--json-report', action='store_true', help='Lưu báo cáo dạng JSON thay vì text')
    
    args = parser.parse_args()
    
    # Initialize analytics
    analytics = ThreadAnalytics()
    
    # Fetch threads
    threads = analytics.fetch_all_threads(
        max_threads=args.max_threads,
        date_from=args.date_from,
        date_to=args.date_to
    )
    
    if not threads:
        print("Không có dữ liệu threads để phân tích!")
        return
    
    # Generate report
    report = analytics.generate_report(threads)
    
    # Print summary
    analytics.print_summary(report)
    
    # Save report
    if args.json_report:
        output_file = args.output + '.json' if args.output else None
        report_file = analytics.save_report(report, output_file)
    else:
        output_file = args.output + '.txt' if args.output else None
        report_file = analytics.save_report_as_text(report, output_file)
    
    # Export CSV if requested
    if args.export_csv:
        analytics.export_to_csv(report)
    
    # Export conversations if requested
    if args.export_conversations > 0:
        print(f"\n📥 Xuất conversations cho {args.export_conversations} threads đầu tiên...")
        result = analytics.export_conversations_by_user_thread(threads, args.export_conversations)
        print(f"✅ Đã xuất {result['exported_count']} conversations cho {result['users_count']} users")
    
    # Cleanup old files
    cleanup_output_files(keep_latest=3, base_dir=analytics.output_base_dir)
    
    print(f"\n✅ Hoàn thành! Báo cáo đã được lưu tại: {report_file}")


if __name__ == "__main__":
    main() 