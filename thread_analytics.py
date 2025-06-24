#!/usr/bin/env python3
"""
Thread Analytics Script
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


class ThreadAnalytics:
    def __init__(self, base_url: str = "https://agent-prod.rovitravel.com", output_base_dir: str = "reports"):
        self.base_url = base_url
        self.output_base_dir = output_base_dir
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json'
        })
        
        # Create base directory structure
        self._ensure_directory_structure()
    
    def _ensure_directory_structure(self):
        """Tạo cấu trúc thư mục báo cáo"""
        if not os.path.exists(self.output_base_dir):
            os.makedirs(self.output_base_dir)
    
    def _get_output_paths(self, timestamp: str = None):
        """Lấy đường dẫn output theo cấu trúc ngày"""
        if timestamp is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Parse date from timestamp
        date_str = timestamp.split('_')[0]  # Get YYYYMMDD part
        formatted_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"  # YYYY-MM-DD
        
        # Create paths
        date_dir = os.path.join(self.output_base_dir, formatted_date)
        reports_dir = os.path.join(date_dir, "reports")
        conversations_dir = os.path.join(date_dir, "conversations")
        
        # Ensure directories exist
        for dir_path in [date_dir, reports_dir, conversations_dir]:
            if not os.path.exists(dir_path):
                os.makedirs(dir_path)
        
        return {
            'date_dir': date_dir,
            'reports_dir': reports_dir, 
            'conversations_dir': conversations_dir,
            'timestamp': timestamp
        }
    
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
            # API trả về trực tiếp là array threads
            return data if isinstance(data, list) else []
        except requests.exceptions.RequestException as e:
            print(f"Lỗi khi gọi API: {e}")
            return []
    
    def fetch_all_threads(self, max_threads: Optional[int] = None) -> List[Dict[str, Any]]:
        """Lấy tất cả threads với phân trang"""
        all_threads = []
        offset = 0
        limit = 100
        
        print("Đang lấy dữ liệu threads...")
        
        while True:
            print(f"  Lấy từ {offset} đến {offset + limit}")
            threads = self.fetch_threads(limit=limit, offset=offset)
            
            if not threads:
                break
                
            all_threads.extend(threads)
            
            if max_threads and len(all_threads) >= max_threads:
                all_threads = all_threads[:max_threads]
                break
                
            offset += limit
            
            # Tránh quá tải server
            import time
            time.sleep(0.1)
        
        print(f"Đã lấy được {len(all_threads)} threads")
        return all_threads
    
    def get_thread_history(self, thread_id: str) -> List[Dict[str, Any]]:
        """Lấy lịch sử thực thi của một thread"""
        url = f"{self.base_url}/threads/{thread_id}/history"
        
        try:
            response = self.session.get(url)
            response.raise_for_status()
            data = response.json()
            # API trả về trực tiếp là array history items
            return data if isinstance(data, list) else []
        except requests.exceptions.RequestException as e:
            print(f"Lỗi khi lấy history cho thread {thread_id}: {e}")
            return []
    
    def analyze_threads_by_date(self, threads: List[Dict[str, Any]]) -> Dict[str, int]:
        """Phân tích số lượng threads theo ngày"""
        threads_by_date = defaultdict(int)
        
        for thread in threads:
            updated_at = thread.get('updated_at')
            if updated_at:
                # Parse thời gian (giả định format ISO)
                try:
                    dt = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
                    date_str = dt.strftime('%Y-%m-%d')
                    threads_by_date[date_str] += 1
                except (ValueError, AttributeError):
                    print(f"Không thể parse thời gian: {updated_at}")
        
        return dict(sorted(threads_by_date.items()))
    
    def get_user_metadata(self, thread_id: str) -> Dict[str, Any]:
        """Lấy thông tin user metadata từ history của thread"""
        history_data = self.get_thread_history(thread_id)
        
        if not history_data:
            return {}
        
        # Lấy metadata từ history item đầu tiên (thường chứa user info)
        for item in history_data:
            metadata = item.get('metadata', {})
            if metadata.get('username') or metadata.get('email'):
                return {
                    'username': metadata.get('username', ''),
                    'email': metadata.get('email', ''),
                    'name': metadata.get('name', ''),
                    'phoneNumber': metadata.get('phoneNumber', ''),
                    'user_id': metadata.get('user_id', ''),
                    'userId': metadata.get('userId', '')
                }
        
        return {}

    def analyze_users_with_conversations(self, threads: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Phân tích dữ liệu user với metadata và conversation content"""
        user_threads = defaultdict(list)
        user_details = {}
        thread_conversations = {}
        total_users = set()
        
        print("\n👥 Đang thu thập thông tin user metadata và conversations...")
        
        for i, thread in enumerate(threads):
            # Progress indicator
            if (i + 1) % 10 == 0:
                print(f"  Đã xử lý {i + 1}/{len(threads)} threads...")
            
            metadata = thread.get('metadata', {})
            user_id = metadata.get('user_id')
            thread_id = thread.get('thread_id')
            
            if user_id and thread_id:
                user_threads[user_id].append(thread_id)
                total_users.add(user_id)
                
                # Lấy user metadata nếu chưa có (tránh lặp lại)
                if user_id not in user_details:
                    user_metadata = self.get_user_metadata(thread_id)
                    if user_metadata:
                        user_details[user_id] = user_metadata
                    else:
                        # Fallback với thông tin cơ bản
                        user_details[user_id] = {
                            'username': '',
                            'email': '',
                            'name': '',
                            'phoneNumber': '',
                            # 'user_id': user_id,
                            'userId': user_id
                        }
                
                # Lấy conversation content
                history_data = self.get_thread_history(thread_id)
                conversation = self.extract_conversation_from_history(history_data)
                
                # Tóm tắt conversation
                if conversation:
                    messages_count = len(conversation)
                    user_messages = [msg for msg in conversation if msg.get('role') == 'User']
                    ai_messages = [msg for msg in conversation if msg.get('role') == 'AI']
                    
                    # Lấy tin nhắn đầu và cuối
                    first_message = conversation[0].get('content', '') + '...' if conversation else ''
                    last_message = conversation[-1].get('content', '') + '...' if conversation else ''
                    
                    thread_conversations[thread_id] = {
                        'total_messages': messages_count,
                        'user_messages': len(user_messages),
                        'ai_messages': len(ai_messages),
                        'first_message': first_message,
                        'last_message': last_message,
                        'created_at': thread.get('created_at', ''),
                        'updated_at': thread.get('updated_at', ''),
                        'user_id': user_id,
                        'conversation': conversation  # Lưu full conversation để dùng cho web
                    }
                else:
                    thread_conversations[thread_id] = {
                        'total_messages': 0,
                        'user_messages': 0,
                        'ai_messages': 0,
                        'first_message': 'No conversation found',
                        'last_message': 'No conversation found',
                        'created_at': thread.get('created_at', ''),
                        'updated_at': thread.get('updated_at', ''),
                        'user_id': user_id,
                        'conversation': []
                    }
        
        user_stats = {
            'total_users': len(total_users),
            'threads_per_user': {},
            'user_thread_count': Counter(),
            'user_details': user_details,
            'thread_conversations': thread_conversations
        }
        
        for user_id, thread_ids in user_threads.items():
            thread_count = len(thread_ids)
            
            # Tính tổng messages cho user này
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
        
        print(f"✅ Thu thập xong metadata cho {len(user_details)} users và {len(thread_conversations)} conversations")
        
        return user_stats

    def analyze_users(self, threads: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Wrapper để giữ tương thích với code cũ"""
        return self.analyze_users_with_conversations(threads)
    
    def generate_report(self, threads: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Tạo báo cáo tổng hợp"""
        print("\nĐang phân tích dữ liệu...")
        
        # Thống kê tổng quan
        total_threads = len(threads)
        
        # Phân tích theo ngày
        threads_by_date = self.analyze_threads_by_date(threads)
        
        # Phân tích user
        user_stats = self.analyze_users(threads)
        
        # Tính toán thống kê
        if user_stats['total_users'] > 0:
            avg_threads_per_user = total_threads / user_stats['total_users']
        else:
            avg_threads_per_user = 0
        
        report = {
            'summary': {
                'total_threads': total_threads,
                'total_users': user_stats['total_users'],
                'avg_threads_per_user': round(avg_threads_per_user, 2),
                'analysis_date': datetime.now().isoformat()
            },
            'threads_by_date': threads_by_date,
            'user_stats': user_stats,
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
                'thread_ids': data['thread_ids'][:5],  # Chỉ hiển thị 5 thread đầu
                'user_info': data.get('user_info', {})  # Thêm metadata
            }
            for user_id, data in sorted_users[:top_n]
        ]
    
    def save_report(self, report: Dict[str, Any], filename: str = None):
        """Lưu báo cáo ra file trong cấu trúc thư mục"""
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
            f.write("\n🏆 TOP 10 USERS CÓ NHIỀU THREADS NHẤT (KÈM METADATA & CONVERSATIONS):\n")
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
            
            # Phân phối threads/user
            f.write("📊 PHÂN PHỐI SỐ THREADS/USER:\n")
            f.write("-" * 40 + "\n")
            user_thread_count = report['user_stats']['user_thread_count']
            for thread_count, user_count in sorted(user_thread_count.items())[:10]:
                f.write(f"{thread_count} threads: {user_count} users\n")
            
            # Chi tiết conversations nếu có
            thread_conversations = report['user_stats'].get('thread_conversations', {})
            if thread_conversations:
                f.write(f"\n💬 CHI TIẾT {len(thread_conversations)} THREADS VỚI CONVERSATIONS:\n")
                f.write("-" * 60 + "\n")
                
                # Sắp xếp theo số messages giảm dần
                sorted_conversations = sorted(
                    thread_conversations.items(),
                    key=lambda x: x[1].get('total_messages', 0),
                    reverse=True
                )
                
                for i, (thread_id, conv_data) in enumerate(sorted_conversations[:20], 1):  # Top 20
                    f.write(f"{i:2d}. Thread: {thread_id}\n")
                    f.write(f"    💬 Messages: {conv_data.get('total_messages', 0)} total ")
                    f.write(f"({conv_data.get('user_messages', 0)} user, {conv_data.get('ai_messages', 0)} AI)\n")
                    f.write(f"    📅 Created: {conv_data.get('created_at', 'N/A')}\n")
                    f.write(f"    🔄 Updated: {conv_data.get('updated_at', 'N/A')}\n")
                    
                    first_msg = conv_data.get('first_message', '')
                    if first_msg and first_msg != 'No conversation found':
                        first_preview = first_msg[:100] + "..." if len(first_msg) > 100 else first_msg
                        f.write(f"    💭 First: {first_preview}\n")
                    
                    last_msg = conv_data.get('last_message', '')
                    if last_msg and last_msg != 'No conversation found' and last_msg != first_msg:
                        last_preview = last_msg[:100] + "..." if len(last_msg) > 100 else last_msg
                        f.write(f"    💭 Last: {last_preview}\n")
                    f.write("\n")
        
        print(f"\n📄 Đã lưu báo cáo dạng text vào: {filepath}")
        return filepath
    
    def export_to_csv(self, report: Dict[str, Any]):
        """Xuất dữ liệu ra CSV với conversation content trong cấu trúc thư mục"""
        paths = self._get_output_paths()
        timestamp = paths['timestamp']
        
        # Export threads by date
        df_dates = pd.DataFrame(list(report['threads_by_date'].items()), 
                               columns=['date', 'thread_count'])
        date_file = os.path.join(paths['reports_dir'], f"threads_by_date_{timestamp}.csv")
        df_dates.to_csv(date_file, index=False)
        print(f"📅 Đã xuất dữ liệu theo ngày: {date_file}")
        
        # Export user stats với metadata và conversation stats
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
        user_file = os.path.join(paths['reports_dir'], f"user_stats_comprehensive_{timestamp}.csv")
        df_users.to_csv(user_file, index=False)
        print(f"👥 Đã xuất thống kê users tổng hợp: {user_file}")
        
        # Export detailed thread conversations
        thread_conversations = report['user_stats'].get('thread_conversations', {})
        if thread_conversations:
            conversation_data = []
            for thread_id, conv_data in thread_conversations.items():
                conversation_data.append({
                    'thread_id': thread_id,
                    'user_id': conv_data.get('user_id', ''),
                    'total_messages': conv_data.get('total_messages', 0),
                    'user_messages': conv_data.get('user_messages', 0),
                    'ai_messages': conv_data.get('ai_messages', 0),
                    'first_message_preview': conv_data.get('first_message', ''),
                    'last_message_preview': conv_data.get('last_message', ''),
                    'created_at': conv_data.get('created_at', ''),
                    'updated_at': conv_data.get('updated_at', '')
                })
            
            df_conversations = pd.DataFrame(conversation_data)
            conv_file = os.path.join(paths['reports_dir'], f"thread_conversations_{timestamp}.csv")
            df_conversations.to_csv(conv_file, index=False)
            print(f"💬 Đã xuất chi tiết conversations: {conv_file}")
        
        return {
            'date_file': date_file,
            'user_file': user_file,
            'conversation_file': conv_file if thread_conversations else None
        }
    
    def extract_conversation_from_history(self, history_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract cuộc hội thoại từ history data"""
        conversation = []
        
        if not history_data or not isinstance(history_data, list):
            return conversation
        
        for item in history_data:
            if not isinstance(item, dict):
                continue
                
            values = item.get('values', {})
            created_at = item.get('created_at', '')
            
            if not values:
                continue
            
            # values có thể là dict hoặc list
            if isinstance(values, dict):
                values_to_process = [values]
            elif isinstance(values, list):
                values_to_process = values
            else:
                continue
            
            for value in values_to_process:
                if not isinstance(value, dict):
                    continue
                    
                # Tìm messages trong values
                messages = []
                
                # Thử messages trực tiếp
                direct_messages = value.get('messages', [])
                if isinstance(direct_messages, list):
                    messages.extend(direct_messages)
                elif direct_messages:  # Single message
                    messages.append(direct_messages)
                
                # Thử tìm trong các key khác có thể chứa messages
                if not messages:
                    for key, val in value.items():
                        key_lower = key.lower()
                        if any(keyword in key_lower for keyword in ['message', 'chat', 'conversation', 'dialog']):
                            if isinstance(val, list):
                                messages.extend(val)
                            elif isinstance(val, dict):
                                messages.append(val)
                
                # Extract messages
                for msg in messages:
                    if not isinstance(msg, dict):
                        continue
                        
                    msg_type = msg.get('type', msg.get('role', 'unknown'))
                    content = msg.get('content', msg.get('text', msg.get('message', '')))
                    
                    # Handle content nếu là list hoặc dict
                    if isinstance(content, list):
                        content = ' '.join(str(item) for item in content if item)
                    elif isinstance(content, dict):
                        content = str(content)
                    
                    # Chỉ lấy messages có content và role hợp lệ
                    if content and str(content).strip() and msg_type in ['human', 'ai', 'user', 'assistant']:
                        role = 'User' if msg_type in ['human', 'user'] else 'AI'
                        
                        conversation.append({
                            'timestamp': created_at,
                            'role': role,
                            'content': str(content).strip()
                        })
        
        return conversation
    
    def export_conversations_to_file(self, threads: List[Dict[str, Any]], max_conversations: int = 10):
        """Export conversations ra file JSON để review chi tiết"""
        paths = self._get_output_paths()
        filename = f"conversations_{paths['timestamp']}.json"
        filepath = os.path.join(paths['conversations_dir'], filename)
        
        print(f"\n📤 XUẤT HỘI THOẠI RA FILE JSON:")
        print("-" * 40)
        
        all_conversations = []
        
        for i, thread in enumerate(threads[:max_conversations]):
            thread_id = thread['thread_id']
            print(f"  Xử lý thread {i+1}/{min(max_conversations, len(threads))}: {thread_id}")
            
            history_data = self.get_thread_history(thread_id)
            if history_data:
                conversation = self.extract_conversation_from_history(history_data)
                
                if conversation:
                    thread_conversation = {
                        'thread_id': thread_id,
                        'created_at': thread.get('created_at'),
                        'updated_at': thread.get('updated_at'),
                        'metadata': thread.get('metadata', {}),
                        'conversation': conversation,
                        'message_count': len(conversation)
                    }
                    all_conversations.append(thread_conversation)
        
        # Lưu file
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(all_conversations, f, ensure_ascii=False, indent=2)
        
        print(f"\n✅ Đã xuất {len(all_conversations)} cuộc hội thoại vào file: {filepath}")
        return filepath

    def export_conversations_by_user_thread(self, threads: List[Dict[str, Any]], max_conversations: int = 10):
        """Export conversations theo cấu trúc user/thread riêng biệt"""
        paths = self._get_output_paths()
        base_conv_dir = paths['conversations_dir']
        
        print(f"\n📤 XUẤT HỘI THOẠI THEO USER/THREAD:")
        print("-" * 40)
        
        exported_count = 0
        user_summary = {}
        
        for i, thread in enumerate(threads[:max_conversations]):
            thread_id = thread['thread_id']
            metadata = thread.get('metadata', {})
            user_id = metadata.get('user_id', 'unknown_user')
            
            print(f"  Xử lý thread {i+1}/{min(max_conversations, len(threads))}: {thread_id}")
            
            # Tạo thư mục user nếu chưa có
            user_dir = os.path.join(base_conv_dir, f"user_{user_id}")
            if not os.path.exists(user_dir):
                os.makedirs(user_dir)
            
            # Lấy user metadata để tạo file info
            user_metadata = self.get_user_metadata(thread_id)
            if user_id not in user_summary:
                user_summary[user_id] = {
                    'threads': [],
                    'total_messages': 0,
                    'user_info': user_metadata
                }
            
            history_data = self.get_thread_history(thread_id)
            if history_data:
                conversation = self.extract_conversation_from_history(history_data)
                
                if conversation:
                    exported_count += 1
                    
                    # File cho thread này
                    thread_filename = f"thread_{thread_id}.txt"
                    thread_filepath = os.path.join(user_dir, thread_filename)
                    
                    with open(thread_filepath, 'w', encoding='utf-8') as f:
                        f.write("="*80 + "\n")
                        f.write(f"💬 THREAD CONVERSATION: {thread_id}\n")
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
                        
                        # Xuất từng tin nhắn
                        for j, msg in enumerate(conversation, 1):
                            role = msg['role']
                            content = str(msg['content'])
                            timestamp = msg.get('timestamp', '')
                            
                            # Icon và tên cho role
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
                            
                            # Content với line wrapping
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
                            
                            if j < len(conversation):
                                f.write("    " + "·"*50 + "\n")
                    
                    # Cập nhật summary
                    user_summary[user_id]['threads'].append({
                        'thread_id': thread_id,
                        'message_count': len(conversation),
                        'file_path': thread_filepath,
                        'created_at': thread.get('created_at', ''),
                        'updated_at': thread.get('updated_at', '')
                    })
                    user_summary[user_id]['total_messages'] += len(conversation)
                    
                    print(f"    ✅ Saved: {thread_filepath}")
                else:
                    print(f"    ⚠️ Không tìm thấy conversation cho thread {thread_id}")
            else:
                print(f"    ❌ Không thể lấy history cho thread {thread_id}")
        
        # Tạo file summary cho mỗi user
        print(f"\n📊 Tạo user summaries...")
        for user_id, summary in user_summary.items():
            user_dir = os.path.join(base_conv_dir, f"user_{user_id}")
            summary_file = os.path.join(user_dir, "user_summary.txt")
            
            with open(summary_file, 'w', encoding='utf-8') as f:
                user_info = summary['user_info']
                f.write("="*60 + "\n")
                f.write(f"👤 USER SUMMARY: {user_id}\n")
                f.write("="*60 + "\n")
                f.write(f"📅 Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"🧵 Total threads: {len(summary['threads'])}\n")
                f.write(f"💬 Total messages: {summary['total_messages']}\n")
                
                if summary['threads']:
                    avg_msg = summary['total_messages'] / len(summary['threads'])
                    f.write(f"📈 Avg messages/thread: {avg_msg:.1f}\n")
                
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
        
        # Tạo master summary
        master_summary = os.path.join(base_conv_dir, "conversations_summary.txt")
        with open(master_summary, 'w', encoding='utf-8') as f:
            f.write("="*80 + "\n")
            f.write("📊 CONVERSATIONS EXPORT SUMMARY\n")
            f.write("="*80 + "\n")
            f.write(f"📅 Export time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"👥 Total users: {len(user_summary)}\n")
            f.write(f"🧵 Total threads exported: {exported_count}\n")
            f.write(f"💬 Total messages: {sum(s['total_messages'] for s in user_summary.values())}\n\n")
            
            f.write("📁 Directory Structure:\n")
            f.write("-" * 40 + "\n")
            for user_id, summary in user_summary.items():
                user_info = summary['user_info']
                display_name = (user_info.get('username', '') or 
                              user_info.get('name', '') or 
                              (user_id[:8] if user_id else 'unknown'))
                f.write(f"📁 user_{user_id}/ ({display_name})\n")
                f.write(f"   📄 user_summary.txt\n")
                for thread_info in summary['threads']:
                    filename = os.path.basename(thread_info['file_path'])
                    f.write(f"   📄 {filename} ({thread_info['message_count']} messages)\n")
                f.write("\n")
        
        print(f"\n✅ Đã xuất {exported_count} conversations cho {len(user_summary)} users")
        print(f"📁 Structure: conversations/user_[id]/thread_[id].txt")
        print(f"📊 Master summary: {master_summary}")
        
        return {
            'exported_count': exported_count,
            'users_count': len(user_summary),
            'master_summary': master_summary,
            'user_summaries': {uid: os.path.join(base_conv_dir, f"user_{uid}", "user_summary.txt") 
                             for uid in user_summary.keys()}
        }

    def export_conversations_to_txt(self, threads: List[Dict[str, Any]], max_conversations: int = 10):
        """Export conversations ra file txt format dễ đọc theo cấu trúc user/thread"""
        return self.export_conversations_by_user_thread(threads, max_conversations)

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
        
        print("\n🏆 TOP 10 USERS CÓ NHIỀU THREADS NHẤT (KÈM METADATA & CONVERSATIONS):")
        print("-" * 80)
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
            
            print(f"{i:2d}. [{user['thread_count']} threads, {total_messages} messages] {username}")
            print(f"    📧 Email: {email}")
            print(f"    👤 Name: {name}")
            print(f"    📱 Phone: {phone if phone else 'N/A'}")
            print(f"    💬 Messages: {total_user_messages} user, {total_messages-total_user_messages} AI (avg: {avg_messages}/thread)")
            print(f"    🆔 User ID: {user['user_id'][:8]}...{user['user_id'][-8:]}")
            print()
        
        print("\n📊 PHÂN PHỐI SỐ THREADS/USER:")
        print("-" * 40)
        user_thread_count = report['user_stats']['user_thread_count']
        for thread_count, user_count in sorted(user_thread_count.items())[:10]:
            print(f"{thread_count} threads: {user_count} users")

    def get_conversation_sample(self, threads: List[Dict[str, Any]], sample_size: int = 5):
        """Lấy mẫu hội thoại từ một số threads"""
        print(f"\n💬 LẤY MẪU HỘI THOẠI TỪ {sample_size} THREADS:")
        print("-" * 60)
        
        sample_threads = threads[:sample_size]
        
        for i, thread in enumerate(sample_threads, 1):
            thread_id = thread['thread_id']
            print(f"\n{i}. Thread ID: {thread_id}")
            print("=" * 50)
            
            history_data = self.get_thread_history(thread_id)
            if history_data:
                conversation = self.extract_conversation_from_history(history_data)
                
                if conversation:
                    print(f"📝 Tìm thấy {len(conversation)} tin nhắn trong cuộc hội thoại:")
                    print("-" * 40)
                    
                    for j, msg in enumerate(conversation[:10]):  # Hiển thị tối đa 10 tin nhắn
                        role = msg['role']
                        content = str(msg['content'])
                        timestamp = msg['timestamp']
                        
                        # Format content để hiển thị đẹp
                        if len(content) > 200:
                            content = content[:200] + "..."
                        
                        # Icon cho role
                        icon = "👤" if role == "User" else "🤖"
                        
                        print(f"\n{j+1}. {icon} {role}:")
                        if timestamp:
                            print(f"   ⏰ {timestamp}")
                        print(f"   💭 {content}")
                        
                        if j < len(conversation) - 1:
                            print("   " + "-" * 30)
                    
                    if len(conversation) > 10:
                        print(f"\n   ... và {len(conversation) - 10} tin nhắn khác")
                else:
                    print("   ❌ Không tìm thấy hội thoại trong history này")
                    print("   🔍 Đang thử phân tích cấu trúc dữ liệu...")
                    
                    # Debug: hiển thị cấu trúc dữ liệu
                    if history_data:
                        first_item = history_data[0]
                        print(f"   📊 Keys trong history item: {list(first_item.keys())}")
                        
                        values = first_item.get('values', [])
                        if values and len(values) > 0 and isinstance(values[0], dict):
                            print(f"   📊 Keys trong values[0]: {list(values[0].keys())}")
            else:
                print("   ❌ Không thể lấy được dữ liệu history")


def cleanup_output_files(keep_latest: int = 3, base_dir: str = "reports"):
    """Dọn dẹp các files output cũ theo cấu trúc thư mục mới"""
    import os
    import glob
    import shutil
    from datetime import datetime, timedelta
    
    print(f"\n🧹 Dọn dẹp thư mục {base_dir}, giữ lại {keep_latest} ngày gần nhất...")
    
    if not os.path.exists(base_dir):
        print(f"⚠️ Thư mục {base_dir} không tồn tại")
        return
    
    # Lấy danh sách các thư mục ngày
    date_dirs = []
    for item in os.listdir(base_dir):
        item_path = os.path.join(base_dir, item)
        if os.path.isdir(item_path) and len(item) == 10 and item.count('-') == 2:  # YYYY-MM-DD format
            try:
                date_obj = datetime.strptime(item, '%Y-%m-%d')
                date_dirs.append((date_obj, item_path))
            except ValueError:
                continue
    
    # Sắp xếp theo ngày (mới nhất trước)
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
    
    # Hiển thị các thư mục còn lại
    remaining_dirs = [os.path.basename(d[1]) for d in date_dirs[:keep_latest]]
    if remaining_dirs:
        print(f"📁 Còn lại {len(remaining_dirs)} thư mục: {', '.join(remaining_dirs)}")

def main():
    parser = argparse.ArgumentParser(description='Thread Analytics Tool')
    parser.add_argument('--max-threads', type=int, help='Số lượng threads tối đa để phân tích')
    parser.add_argument('--export-csv', action='store_true', help='Xuất dữ liệu ra CSV')
    parser.add_argument('--chat-sample', type=int, default=5, help='Số lượng threads để lấy mẫu hội thoại')
    parser.add_argument('--export-conversations-txt', type=int, default=10, help='Xuất N cuộc hội thoại ra file TXT (mặc định: 10)')
    parser.add_argument('--export-conversations-json', type=int, default=0, help='Xuất N cuộc hội thoại ra file JSON')
    parser.add_argument('--output', help='Tên file để lưu báo cáo (không cần extension)')
    parser.add_argument('--json-report', action='store_true', help='Lưu báo cáo dạng JSON thay vì text')
    
    args = parser.parse_args()
    
    # Khởi tạo analytics
    analytics = ThreadAnalytics()
    
    # Lấy dữ liệu threads
    threads = analytics.fetch_all_threads(max_threads=args.max_threads)
    
    if not threads:
        print("Không có dữ liệu threads để phân tích!")
        return
    
    # Tạo báo cáo
    report = analytics.generate_report(threads)
    
    # Hiển thị tóm tắt
    analytics.print_summary(report)
    
    # Lưu báo cáo - mặc định là text format
    if args.json_report:
        output_file = args.output + '.json' if args.output else None
        report_file = analytics.save_report(report, output_file)
    else:
        output_file = args.output + '.txt' if args.output else None
        report_file = analytics.save_report_as_text(report, output_file)
    
    # Xuất CSV nếu được yêu cầu
    if args.export_csv:
        analytics.export_to_csv(report)
    
    # Lấy mẫu conversation
    if args.chat_sample > 0:
        analytics.get_conversation_sample(threads, args.chat_sample)
    
    # Xuất conversations với structure user/thread
    if args.export_conversations_json or args.export_conversations_txt:
        print(f"\n📥 Xuất conversations cho {args.export_conversations_json or args.export_conversations_txt} threads đầu tiên...")
        result = analytics.export_conversations_by_user_thread(threads, args.export_conversations_json or args.export_conversations_txt)
        print(f"✅ Đã xuất {result['exported_count']} conversations cho {result['users_count']} users")
    
    # Dọn dẹp files cũ
    cleanup_output_files(keep_latest=3, base_dir=analytics.output_base_dir)
    
    print(f"\n✅ Hoàn thành! Báo cáo đã được lưu tại: {report_file}")


if __name__ == "__main__":
    main() 