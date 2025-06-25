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


class ThreadAnalytics:
    """
    Refactored ThreadAnalytics class - Simplified and optimized
    """
    
    def __init__(self, base_url: str = None, output_base_dir: str = "reports"):
        try:
            import streamlit as st
            secrets_url = getattr(st.secrets, "THREAD_API_URL", None)
        except Exception:
            secrets_url = None
            raise Exception("Không tìm thấy URL API trong biến môi trường hoặc streamlit secrets")
        self.base_url = secrets_url
        self.output_base_dir = output_base_dir
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
    
    def fetch_all_threads(self, max_threads: Optional[int] = None, date_from: str = None, date_to: str = None) -> List[Dict[str, Any]]:
        """Lấy tất cả threads với phân trang và filter ngày"""
        all_threads = []
        offset = 0
        limit = 100
        
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
            
            if max_threads and len(all_threads) >= max_threads:
                all_threads = all_threads[:max_threads]
                break
                
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
            if (i + 1) % 10 == 0:
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
    def generate_report(self, threads: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Tạo báo cáo tổng hợp - Optimized"""
        print("\nĐang phân tích dữ liệu...")
        
        total_threads = len(threads)
        threads_by_date = self.analyze_threads_by_date(threads)
        user_stats = self.analyze_users_comprehensive(threads)
        
        avg_threads_per_user = total_threads / user_stats['total_users'] if user_stats['total_users'] > 0 else 0
        
        report = {
            'summary': {
                'total_threads': total_threads,
                'total_users': user_stats['total_users'],
                'avg_threads_per_user': round(avg_threads_per_user, 2),
                'analysis_date': datetime.now().isoformat()
            },
            'threads_by_date': threads_by_date,
            'user_stats': user_stats,
            'threads_per_user': user_stats['threads_per_user'],  # For backward compatibility
            'top_users': self.get_top_users(user_stats['threads_per_user'])
        }
        
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
                'thread_ids': data['thread_ids'][:5],  # Only show first 5 threads
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
    
    def export_conversations_by_user_thread(self, threads: List[Dict[str, Any]], max_conversations: int = 10):
        """Export conversations theo cấu trúc user/thread - Simplified"""
        paths = self._get_output_paths()
        base_conv_dir = paths['conversations_dir']
        
        print(f"\n📤 Xuất {max_conversations} conversations theo user/thread...")
        
        exported_count = 0
        user_summary = {}
        
        for i, thread in enumerate(threads[:max_conversations]):
            thread_id = thread['thread_id']
            metadata = thread.get('metadata', {})
            user_id = metadata.get('user_id', 'unknown_user')
            
            print(f"  {i+1}/{max_conversations}: {thread_id}")
            
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