#!/usr/bin/env python3
"""
Dynamic Thread Analytics Dashboard
Dashboard hoàn toàn động - fetch dữ liệu trực tiếp từ API
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta, date
import json
from collections import Counter, defaultdict
from typing import Dict, List, Any, Optional
from thread_analytics import ThreadAnalytics

# Page config
st.set_page_config(
    page_title="Dynamic Thread Analytics Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .metric-card {
        background-color: #f0f2f6;
        border-radius: 10px;
        padding: 1rem;
        border-left: 5px solid #1f77b4;
    }
    .conversation-msg {
        margin: 10px 0;
        padding: 10px;
        border-radius: 8px;
    }
    .user-msg {
        background-color: #e3f2fd;
        border-left: 4px solid #2196f3;
    }
    .ai-msg {
        background-color: #f3e5f5;
        border-left: 4px solid #9c27b0;
    }
    .date-filter {
        background-color: #e8f5e8;
        border-radius: 8px;
        padding: 20px;
        margin: 10px 0;
        border-left: 4px solid #4caf50;
    }
    .welcome-box {
        background-color: #fff3cd;
        border-radius: 8px;
        padding: 20px;
        margin: 20px 0;
        border-left: 4px solid #ffc107;
    }
    .success-box {
        background-color: #d4edda;
        border-radius: 8px;
        padding: 15px;
        margin: 10px 0;
        border-left: 4px solid #28a745;
    }
</style>
""", unsafe_allow_html=True)

def display_welcome_message():
    """Hiển thị thông báo chào mừng"""
    st.markdown("""
    <div class="welcome-box">
        <h2>🎯 Chào mừng đến với Dynamic Thread Analytics Dashboard!</h2>
        <p><strong>Dashboard này hoàn toàn động - không cần file báo cáo có sẵn!</strong></p>
        <h4>📋 Hướng dẫn sử dụng:</h4>
        <ol>
            <li>📅 <strong>Chọn khoảng thời gian:</strong> Từ ngày → Đến ngày</li>
            <li>⚙️ <strong>Cài đặt:</strong> Số lượng threads tối đa để phân tích</li>
            <li>🚀 <strong>Bắt đầu:</strong> Nhấn "Bắt Đầu Thống Kê"</li>
            <li>📊 <strong>Xem kết quả:</strong> Biểu đồ, bảng dữ liệu, conversations</li>
        </ol>
        <p><em>✨ Tất cả dữ liệu được fetch trực tiếp từ API theo thời gian thực!</em></p>
    </div>
    """, unsafe_allow_html=True)

@st.cache_data(ttl=300)  # Cache 5 phút
def fetch_and_analyze_threads(date_from=None, date_to=None, max_threads=1000):
    """Fetch và analyze threads theo khoảng thời gian"""
    try:
        analytics = ThreadAnalytics()
        
        # Fetch all threads với progress
        progress_container = st.container()
        with progress_container:
            st.info("🔄 Đang kết nối API và lấy dữ liệu threads...")
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            progress_bar.progress(0.2)
            status_text.text("📡 Đang gọi API threads/search...")
            
            all_threads = analytics.fetch_all_threads(max_threads=max_threads)
            
            if not all_threads:
                st.error("❌ Không thể lấy dữ liệu từ API hoặc không có threads")
                return None, []
            
            progress_bar.progress(0.5)
            status_text.text(f"✅ Đã lấy được {len(all_threads)} threads")
        
        # Filter threads by date if specified
        filtered_threads = []
        if date_from or date_to:
            progress_bar.progress(0.7)
            status_text.text("📅 Đang lọc dữ liệu theo ngày...")
            
            for thread in all_threads:
                updated_at = thread.get('updated_at')
                if updated_at:
                    try:
                        dt = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
                        thread_date = dt.date()
                        
                        # Check date range
                        if date_from and thread_date < date_from:
                            continue
                        if date_to and thread_date > date_to:
                            continue
                            
                        filtered_threads.append(thread)
                    except (ValueError, AttributeError):
                        continue
        else:
            filtered_threads = all_threads
        
        if not filtered_threads:
            st.warning("⚠️ Không có dữ liệu trong khoảng thời gian đã chọn")
            return None, []
        
        # Generate report from filtered threads
        progress_bar.progress(0.9)
        status_text.text("📊 Đang phân tích và tạo báo cáo...")
        
        report = analytics.generate_report(filtered_threads)
        
        progress_bar.progress(1.0)
        status_text.text("✅ Hoàn tất!")
        
        # Clear progress after success
        progress_container.empty()
        
        return report, filtered_threads
        
    except Exception as e:
        st.error(f"❌ Lỗi khi fetch dữ liệu: {str(e)}")
        st.exception(e)  # Show full error for debugging
        return None, []

@st.cache_data(ttl=300)
def get_conversations_for_threads(threads, max_conversations=20):
    """Lấy conversations cho các threads"""
    try:
        analytics = ThreadAnalytics()
        conversations = []
        
        # Progress tracking
        progress_container = st.container()
        with progress_container:
            st.info(f"💬 Đang lấy conversations cho {min(len(threads), max_conversations)} threads...")
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            total_threads = min(len(threads), max_conversations)
            
            for i, thread in enumerate(threads[:max_conversations]):
                thread_id = thread.get('thread_id')
                if not thread_id:
                    continue
                
                # Update progress
                progress = (i + 1) / total_threads
                progress_bar.progress(progress)
                status_text.text(f"💬 Xử lý thread {i+1}/{total_threads}: {thread_id[:16]}...")
                
                # Get conversation
                history_data = analytics.get_thread_history(thread_id)
                if history_data:
                    conversation = analytics.extract_conversation_from_history(history_data)
                    
                    if conversation:
                        conv_data = {
                            'thread_id': thread_id,
                            'created_at': thread.get('created_at', ''),
                            'updated_at': thread.get('updated_at', ''),
                            'message_count': len(conversation),
                            'conversation': conversation,
                            'metadata': thread.get('metadata', {})
                        }
                        conversations.append(conv_data)
            
            progress_bar.progress(1.0)
            status_text.text("✅ Hoàn tất tải conversations!")
        
        # Clear progress after success
        progress_container.empty()
        
        return conversations
        
    except Exception as e:
        st.error(f"❌ Lỗi khi lấy conversations: {str(e)}")
        return []

def display_date_filter():
    """Hiển thị bộ lọc ngày"""
    st.markdown('<div class="date-filter">', unsafe_allow_html=True)
    st.subheader("📅 Chọn Khoảng Thời Gian Thống Kê")
    
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col1:
        date_from = st.date_input(
            "Từ ngày:",
            value=date.today() - timedelta(days=7),
            max_value=date.today(),
            help="Chọn ngày bắt đầu thống kê"
        )
    
    with col2:
        date_to = st.date_input(
            "Đến ngày:",
            value=date.today(),
            max_value=date.today(),
            help="Chọn ngày kết thúc thống kê"
        )
    
    with col3:
        max_threads = st.number_input(
            "Giới hạn threads:",
            min_value=10,
            max_value=5000,
            value=500,
            step=50,
            help="Số lượng threads tối đa để phân tích (nhiều hơn = chậm hơn)"
        )
    
    # Validate dates
    if date_from > date_to:
        st.error("❌ Ngày bắt đầu không thể sau ngày kết thúc!")
        return None, None, max_threads
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Show selected range info
    days_diff = (date_to - date_from).days + 1
    st.markdown(f"""
    <div class="success-box">
        📊 <strong>Sẽ thống kê:</strong> {date_from} ➜ {date_to} ({days_diff} ngày)<br>
        ⚙️ <strong>Giới hạn:</strong> Tối đa {max_threads} threads
    </div>
    """, unsafe_allow_html=True)
    
    return date_from, date_to, max_threads

def display_overview_metrics(report_data):
    """Hiển thị tổng quan metrics"""
    if not report_data:
        st.error("❌ Không có dữ liệu để hiển thị")
        return
    
    st.subheader("📈 Tổng Quan Dữ Liệu")
    
    # Debug: show report structure
    st.write("🔍 **Debug - Report keys:**", list(report_data.keys()))
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        # Try different possible keys
        total_threads = (
            report_data.get('total_threads', 0) or 
            report_data.get('summary', {}).get('total_threads', 0) or
            len(report_data.get('threads_by_date', {}))
        )
        st.metric(
            label="📝 Tổng Threads",
            value=f"{total_threads:,}",
            help="Tổng số threads trong khoảng thời gian"
        )
    
    with col2:
        # Try different possible keys
        total_users = (
            report_data.get('total_users', 0) or
            report_data.get('summary', {}).get('total_users', 0) or
            len(report_data.get('threads_per_user', {})) or
            len(report_data.get('user_stats', {}).get('threads_per_user', {}))
        )
        st.metric(
            label="👥 Tổng Users",
            value=f"{total_users:,}",
            help="Tổng số users có hoạt động"
        )
    
    with col3:
        # Try different possible keys
        avg_threads = (
            report_data.get('average_threads_per_user', 0) or
            report_data.get('summary', {}).get('avg_threads_per_user', 0) or
            (total_threads / total_users if total_users > 0 else 0)
        )
        st.metric(
            label="📊 TB Threads/User",
            value=f"{avg_threads:.1f}",
            help="Trung bình số threads mỗi user"
        )
    
    with col4:
        # Find peak day from threads_by_date
        threads_by_date = report_data.get('threads_by_date', {})
        if threads_by_date:
            peak_date = max(threads_by_date.items(), key=lambda x: x[1])
            peak_count = peak_date[1]
            peak_date_str = peak_date[0]
        else:
            peak_date_str = report_data.get('peak_date', 'N/A')
            peak_count = report_data.get('peak_threads', 0)
            
        st.metric(
            label="🔥 Peak Day",
            value=f"{peak_count}",
            help=f"Ngày có nhiều threads nhất: {peak_date_str}"
        )

def create_threads_timeline_chart(report_data):
    """Tạo biểu đồ timeline threads theo ngày"""
    if not report_data or 'threads_by_date' not in report_data:
        st.warning("⚠️ Không có dữ liệu timeline")
        return
    
    threads_by_date = report_data['threads_by_date']
    if not threads_by_date:
        st.warning("⚠️ Không có dữ liệu threads theo ngày")
        return
    
    # Convert to DataFrame
    df = pd.DataFrame(list(threads_by_date.items()), columns=['Date', 'Threads'])
    df['Date'] = pd.to_datetime(df['Date'])
    df = df.sort_values('Date')
    
    # Create chart
    fig = px.line(
        df, 
        x='Date', 
        y='Threads',
        title='📈 Threads Timeline',
        markers=True,
        line_shape='linear'
    )
    
    fig.update_layout(
        xaxis_title="Ngày",
        yaxis_title="Số Threads",
        hovermode='x unified',
        showlegend=False,
        height=400
    )
    
    fig.update_traces(
        line=dict(color='#1f77b4', width=3),
        marker=dict(size=8, color='#ff7f0e'),
        hovertemplate='<b>%{y}</b> threads<br>%{x|%Y-%m-%d}<extra></extra>'
    )
    
    st.plotly_chart(fig, use_container_width=True)

def create_user_distribution_chart(report_data):
    """Tạo biểu đồ phân bố user"""
    if not report_data or 'threads_per_user' not in report_data:
        st.warning("⚠️ Không có dữ liệu user distribution")
        return
    
    threads_per_user = report_data['threads_per_user']
    if not threads_per_user:
        st.warning("⚠️ Không có dữ liệu threads per user")
        return
    
    # Count distribution
    thread_counts = [data.get('thread_count', 0) for data in threads_per_user.values()]
    
    # Create bins
    bins = [1, 2, 3, 5, 10, 20, 50, float('inf')]
    labels = ['1', '2', '3-4', '5-9', '10-19', '20-49', '50+']
    
    distribution = Counter()
    for count in thread_counts:
        for i, bin_max in enumerate(bins):
            if count <= bin_max:
                distribution[labels[i]] += 1
                break
    
    # Create DataFrame
    df = pd.DataFrame(list(distribution.items()), columns=['Range', 'Users'])
    df = df.sort_values('Users', ascending=False)
    
    # Create bar chart
    fig = px.bar(
        df,
        x='Range',
        y='Users',
        title='👥 User Distribution by Thread Count',
        color='Users',
        color_continuous_scale='viridis',
        text='Users'
    )
    
    fig.update_layout(
        xaxis_title="Số Threads",
        yaxis_title="Số Users",
        showlegend=False,
        height=400
    )
    
    fig.update_traces(
        texttemplate='%{text}',
        textposition='outside',
        hovertemplate='<b>%{y}</b> users<br>có %{x} threads<extra></extra>'
    )
    
    st.plotly_chart(fig, use_container_width=True)

def create_top_users_chart(report_data, top_n=10):
    """Tạo biểu đồ top users với tên thật"""
    if not report_data:
        st.warning("⚠️ Không có dữ liệu top users")
        return
    
    # Try to get top users from different possible locations
    top_users = (
        report_data.get('top_users', []) or 
        list(report_data.get('user_stats', {}).get('threads_per_user', {}).items())
    )
    
    if not top_users:
        st.warning("⚠️ Không có dữ liệu top users")
        return
    
    # Convert to DataFrame với tên người dùng thật
    df_data = []
    
    # Handle both formats: list of dicts or list of tuples
    for i, user in enumerate(top_users[:top_n]):
        if isinstance(user, dict):
            # Format: {user_id: '', thread_count: '', user_info: {}}
            user_id = user.get('user_id', '')
            thread_count = user.get('thread_count', 0)
            user_info = user.get('user_info', {})
        elif isinstance(user, tuple) and len(user) == 2:
            # Format: (user_id, {thread_count: '', user_info: {}})
            user_id = user[0]
            user_data = user[1]
            thread_count = user_data.get('thread_count', 0)
            user_info = user_data.get('user_info', {})
        else:
            continue
        
        # Get best display name - NO PREFIX!
        name = user_info.get('name', '').strip()
        username = user_info.get('username', '').strip()
        email = user_info.get('email', '').strip()
        
        if name:
            display_name = name
        elif username:
            display_name = username
        elif email:
            display_name = email.split('@')[0]
        else:
            # Use user_id directly, no prefix
            display_name = user_id[:8] if len(user_id) > 8 else user_id
        
        df_data.append({
            'User': display_name,
            'Threads': thread_count,
            'User_ID': user_id
        })
    
    if not df_data:
        st.warning("⚠️ Không có dữ liệu users hợp lệ")
        return
        
    df = pd.DataFrame(df_data)
    df = df.sort_values('Threads', ascending=True)  # Sort for horizontal bar
    
    # Create horizontal bar chart
    fig = px.bar(
        df,
        x='Threads',
        y='User',
        orientation='h',
        title=f'🏆 Top {len(df)} Users by Thread Count',
        color='Threads',
        color_continuous_scale='plasma',
        text='Threads',
        hover_data={'User_ID': True}
    )
    
    fig.update_layout(
        yaxis={'categoryorder': 'total ascending'},
        xaxis_title="Số Threads",
        yaxis_title="User",
        showlegend=False,
        height=max(400, len(df) * 25 + 100)  # Dynamic height
    )
    
    fig.update_traces(
        texttemplate='%{text}',
        textposition='outside',
        hovertemplate='<b>%{y}</b><br>%{x} threads<br>ID: %{customdata[0]}<extra></extra>'
    )
    
    st.plotly_chart(fig, use_container_width=True)

def get_user_display_name(user_info, user_id=None):
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
        return f"USER_{user_id[:8]}"
    else:
        return "UNKNOWN_USER"

def display_conversations_browser(conversations_data):
    """Hiển thị trình duyệt conversations"""
    if not conversations_data:
        st.warning("⚠️ Không có dữ liệu conversations")
        return
    
    st.subheader("💬 Conversations Browser")
    
    # Organize by user
    users_conversations = defaultdict(list)
    for conv in conversations_data:
        metadata = conv.get('metadata', {})
        user_id = metadata.get('user_id', 'Unknown')
        users_conversations[user_id].append(conv)
    
    if not users_conversations:
        st.warning("⚠️ Không tìm thấy conversations")
        return
    
    # User selector với tên đầy đủ
    user_options = {}
    for user_id, convs in users_conversations.items():
        metadata = convs[0].get('metadata', {})
        display_name = get_user_display_name(metadata, user_id)
        
        # Thêm thông tin user_id vào display name để dễ nhận biết
        user_options[f"{display_name} ({len(convs)} threads) - ID: {user_id[:8]}"] = user_id
    
    selected_user_display = st.selectbox(
        "👤 Chọn User:",
        list(user_options.keys()),
        help="Chọn user để xem conversations"
    )
    
    if not selected_user_display:
        return
    
    selected_user_id = user_options[selected_user_display]
    user_convs = users_conversations[selected_user_id]
    
    # Show user info
    user_metadata = user_convs[0].get('metadata', {})
    
    with st.expander("👤 User Information", expanded=True):
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.write(f"**User ID:** {selected_user_id}")
            st.write(f"**Name:** {user_metadata.get('name', 'N/A')}")
            st.write(f"**Username:** {user_metadata.get('username', 'N/A')}")
            st.write(f"**Email:** {user_metadata.get('email', 'N/A')}")
            st.write(f"**Phone:** {user_metadata.get('phoneNumber', 'N/A')}")
        
        with col2:
            st.metric("📝 Total Threads", len(user_convs))
    
    # Thread selector
    thread_options = {}
    for conv in user_convs:
        thread_id = conv.get('thread_id', '')
        message_count = conv.get('message_count', 0)
        updated_at = conv.get('updated_at', '')[:10] if conv.get('updated_at') else 'N/A'
        thread_options[f"Thread {thread_id[:8]}... ({message_count} msg) - {updated_at}"] = conv
    
    selected_thread_display = st.selectbox(
        "💬 Chọn Thread:",
        list(thread_options.keys()),
        help="Chọn thread để xem conversation chi tiết"
    )
    
    if not selected_thread_display:
        return
    
    selected_conv = thread_options[selected_thread_display]
    
    # Display conversation
    st.markdown("---")
    st.subheader(f"💬 Conversation: {selected_conv.get('thread_id', '')[:16]}...")
    
    conversation = selected_conv.get('conversation', [])
    if not conversation:
        st.warning("⚠️ Không có dữ liệu conversation")
        return
    
    # Remove duplicates và display messages
    seen_messages = set()
    unique_messages = []
    
    for msg in conversation:
        # Tạo unique key cho message
        role = msg.get('role', '').lower()
        content = msg.get('content', '').strip()
        timestamp = msg.get('timestamp', '')
        
        if not content:
            continue
            
        # Unique key bao gồm role, content và timestamp
        msg_key = f"{role}:{content[:100]}:{timestamp}"
        
        if msg_key not in seen_messages:
            seen_messages.add(msg_key)
            unique_messages.append(msg)
    
    if not unique_messages:
        st.warning("⚠️ Không có messages hợp lệ")
        return
    
    st.info(f"📊 Hiển thị {len(unique_messages)} messages (đã loại bỏ {len(conversation) - len(unique_messages)} duplicates)")
    
    # Display unique messages
    for i, msg in enumerate(unique_messages):
        role = msg.get('role', '').lower()
        content = msg.get('content', '')
        timestamp = msg.get('timestamp', '')
        
        # Format timestamp
        time_display = ""
        if timestamp:
            try:
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                time_display = dt.strftime('%H:%M:%S')
            except:
                time_display = timestamp[:8] if timestamp else ""
        
        if role in ['user', 'human']:
            user_name = get_user_display_name(user_metadata, selected_user_id)
            st.markdown(f"""
            <div class="conversation-msg user-msg">
                <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
                    <strong>👤 {user_name}</strong>
                    <small style="color: #666;">{time_display}</small>
                </div>
                {content}
            </div>
            """, unsafe_allow_html=True)
        elif role in ['assistant', 'ai', 'bot']:
            st.markdown(f"""
            <div class="conversation-msg ai-msg">
                <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
                    <strong>🤖 AI Assistant</strong>
                    <small style="color: #666;">{time_display}</small>
                </div>
                {content}
            </div>
            """, unsafe_allow_html=True)

def display_data_tables(report_data):
    """Hiển thị bảng dữ liệu"""
    if not report_data:
        st.warning("⚠️ Không có dữ liệu để hiển thị")
        return
    
    st.subheader("📋 Data Tables")
    
    tab1, tab2, tab3, tab4 = st.tabs(["📅 By Date", "👥 By User", "📋 All Users", "🏆 Top Users"])
    
    with tab1:
        threads_by_date = report_data.get('threads_by_date', {})
        if threads_by_date:
            df_date = pd.DataFrame(list(threads_by_date.items()), columns=['Date', 'Threads'])
            df_date = df_date.sort_values('Date', ascending=False)
            
            st.write(f"**📊 Tổng số ngày có hoạt động:** {len(df_date)}")
            st.dataframe(df_date, use_container_width=True, height=400)
            
            # Download button
            csv = df_date.to_csv(index=False)
            st.download_button(
                label="📥 Download CSV",
                data=csv,
                file_name=f"threads_by_date_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
        else:
            st.warning("⚠️ Không có dữ liệu theo ngày")
    
    with tab2:
        threads_per_user = report_data.get('threads_per_user', {})
        if threads_per_user:
            df_user = []
            for user_id, data in threads_per_user.items():
                df_user.append({
                    'User ID': user_id,
                    'Username': data.get('username', ''),
                    'Email': data.get('email', ''),
                    'Thread Count': data.get('thread_count', 0)
                })
            df_user = pd.DataFrame(df_user)
            df_user = df_user.sort_values('Thread Count', ascending=False)
            
            # Show statistics
            st.write(f"**👥 Tổng số users:** {len(df_user)}")
            st.write(f"**📊 Trong DataTable hiển thị:** {len(df_user)} users (tất cả)")
            
            # Debug: Show raw data count
            with st.expander("🔍 Debug Info - Raw Data"):
                st.write(f"**Raw threads_per_user keys:** {len(threads_per_user)}")
                st.write(f"**DataFrame rows:** {len(df_user)}")
                st.write("**First 5 User IDs from raw data:**")
                user_ids_sample = list(threads_per_user.keys())[:5]
                for uid in user_ids_sample:
                    data = threads_per_user[uid]
                    st.write(f"- {uid}: {data.get('thread_count', 0)} threads")
            
            # Show top stats
            if not df_user.empty:
                top_user = df_user.iloc[0]
                avg_threads = df_user['Thread Count'].mean()
                st.write(f"**🏆 User nhiều threads nhất:** {top_user['Thread Count']} threads")
                st.write(f"**📈 Trung bình threads/user:** {avg_threads:.1f}")
            
            # Display full table with pagination
            st.write("**⬇️ Bảng chi tiết tất cả users:**")
            st.dataframe(df_user, use_container_width=True, height=400)
            
            # Download button
            csv = df_user.to_csv(index=False)
            st.download_button(
                label="📥 Download CSV",
                data=csv,
                file_name=f"users_data_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
        else:
            st.warning("⚠️ Không có dữ liệu user")
    
    with tab3:
        # New tab: All Users - Enhanced view
        threads_per_user = report_data.get('threads_per_user', {})
        if threads_per_user:
            st.markdown("### 📋 Danh Sách Tất Cả Users")
            
            # Create enhanced user dataframe
            all_users_data = []
            for user_id, data in threads_per_user.items():
                all_users_data.append({
                    'STT': len(all_users_data) + 1,
                    'User ID': user_id,
                    'Display Name': data.get('username', '') or data.get('email', '').split('@')[0] if data.get('email') else user_id[:8],
                    'Username': data.get('username', ''),
                    'Email': data.get('email', ''),
                    'Thread Count': data.get('thread_count', 0),
                    'Last Active': data.get('last_active', 'N/A')
                })
            
            df_all_users = pd.DataFrame(all_users_data)
            df_all_users = df_all_users.sort_values('Thread Count', ascending=False)
            
            # Summary statistics
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("👥 Tổng Users", len(df_all_users))
            with col2:
                st.metric("📊 TB Threads/User", f"{df_all_users['Thread Count'].mean():.1f}")
            with col3:
                st.metric("🏆 Max Threads", df_all_users['Thread Count'].max())
            with col4:
                active_users = len(df_all_users[df_all_users['Thread Count'] > 0])
                st.metric("✅ Active Users", active_users)
            
            # Search and filter
            st.markdown("#### 🔍 Tìm Kiếm & Lọc")
            col1, col2 = st.columns(2)
            
            with col1:
                search_term = st.text_input("🔍 Tìm kiếm (User ID, Username, Email):", placeholder="Nhập từ khóa...")
            
            with col2:
                min_threads = st.number_input("Tối thiểu threads:", min_value=0, max_value=100, value=0)
            
            # Apply filters
            filtered_df = df_all_users.copy()
            
            if search_term:
                mask = (
                    filtered_df['User ID'].str.contains(search_term, case=False, na=False) |
                    filtered_df['Username'].str.contains(search_term, case=False, na=False) |
                    filtered_df['Email'].str.contains(search_term, case=False, na=False) |
                    filtered_df['Display Name'].str.contains(search_term, case=False, na=False)
                )
                filtered_df = filtered_df[mask]
            
            if min_threads > 0:
                filtered_df = filtered_df[filtered_df['Thread Count'] >= min_threads]
            
            # Show filtered results info
            if len(filtered_df) != len(df_all_users):
                st.info(f"🔍 Hiển thị {len(filtered_df)}/{len(df_all_users)} users (đã lọc)")
            else:
                st.info(f"📋 Hiển thị tất cả {len(df_all_users)} users")
            
            # Display the full table
            st.dataframe(
                filtered_df,
                use_container_width=True,
                height=500,
                column_config={
                    "STT": st.column_config.NumberColumn("STT", width="small"),
                    "User ID": st.column_config.TextColumn("User ID", width="medium"),
                    "Display Name": st.column_config.TextColumn("Display Name", width="medium"),
                    "Username": st.column_config.TextColumn("Username", width="medium"),
                    "Email": st.column_config.TextColumn("Email", width="large"),
                    "Thread Count": st.column_config.NumberColumn("Thread Count", width="small"),
                    "Last Active": st.column_config.TextColumn("Last Active", width="medium")
                },
                hide_index=True
            )
            
            # Download options
            col1, col2 = st.columns(2)
            with col1:
                csv_all = df_all_users.to_csv(index=False)
                st.download_button(
                    label="📥 Download All Users CSV",
                    data=csv_all,
                    file_name=f"all_users_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                    mime="text/csv"
                )
            
            with col2:
                if len(filtered_df) != len(df_all_users):
                    csv_filtered = filtered_df.to_csv(index=False)
                    st.download_button(
                        label="📥 Download Filtered CSV",
                        data=csv_filtered,
                        file_name=f"filtered_users_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                        mime="text/csv"
                    )
        else:
            st.warning("⚠️ Không có dữ liệu users")

    with tab4:
        top_users = report_data.get('top_users', [])
        if top_users:
            df_top = pd.DataFrame(top_users)
            if not df_top.empty:
                st.write(f"**🏆 Top users:** {len(df_top)}")
                st.dataframe(df_top, use_container_width=True, height=400)
        else:
            st.warning("⚠️ Không có dữ liệu top users")

def main():
    st.title("📊 Dynamic Thread Analytics Dashboard")
    st.markdown("**Dashboard hoàn toàn động** - Fetch dữ liệu trực tiếp từ API")
    
    # Check if we have existing analysis results
    if 'report_data' not in st.session_state:
        display_welcome_message()
    
    # Date filter section
    date_from, date_to, max_threads = display_date_filter()
    
    if date_from is None or date_to is None:
        st.stop()
    
    # Control buttons
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        analyze_button = st.button("🚀 Bắt Đầu Thống Kê", type="primary", use_container_width=True)
    
    with col2:
        if st.button("🗑️ Xóa Cache", help="Xóa cache để lấy dữ liệu mới"):
            st.cache_data.clear()
            # Clear all session state
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.success("✅ Cache đã được xóa")
            st.rerun()
    
    with col3:
        if st.button("🔄 Refresh Page", help="Làm mới trang"):
            st.rerun()
    
    # Analyze data when button clicked
    if analyze_button:
        # Show analysis starting message
        st.markdown("""
        <div class="success-box">
            🚀 <strong>Bắt đầu thống kê!</strong><br>
            📡 Đang kết nối tới API và lấy dữ liệu...
        </div>
        """, unsafe_allow_html=True)
        
        # Fetch and analyze
        report_data, filtered_threads = fetch_and_analyze_threads(
            date_from=date_from,
            date_to=date_to,
            max_threads=max_threads
        )
        
        if report_data:
            # Store in session state
            st.session_state['report_data'] = report_data
            st.session_state['filtered_threads'] = filtered_threads
            st.session_state['analysis_params'] = {
                'date_from': date_from,
                'date_to': date_to,
                'max_threads': max_threads
            }
            
            st.success(f"✅ Đã thống kê thành công {len(filtered_threads)} threads từ {date_from} đến {date_to}")
        else:
            st.error("❌ Không thể lấy dữ liệu hoặc không có dữ liệu trong khoảng thời gian đã chọn")
            st.stop()
    
    # Display results if available
    if 'report_data' in st.session_state and st.session_state['report_data']:
        report_data = st.session_state['report_data']
        filtered_threads = st.session_state.get('filtered_threads', [])
        analysis_params = st.session_state.get('analysis_params', {})
        
        # Show analysis info
        st.markdown(f"""
        <div class="success-box">
            📊 <strong>Kết quả phân tích:</strong> {len(filtered_threads)} threads<br>
            📅 <strong>Thời gian:</strong> {analysis_params.get('date_from')} ➜ {analysis_params.get('date_to')}<br>
            ⏰ <strong>Thời điểm phân tích:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        </div>
        """, unsafe_allow_html=True)
        
        # Metrics
        display_overview_metrics(report_data)
        
        # Charts section
        st.markdown("---")
        st.subheader("📈 Biểu Đồ Thống Kê")
        
        col1, col2 = st.columns(2)
        
        with col1:
            create_threads_timeline_chart(report_data)
            create_user_distribution_chart(report_data)
        
        with col2:
            create_top_users_chart(report_data)
        
        # Data tables
        st.markdown("---")
        display_data_tables(report_data)
        
        # Conversations browser section
        if filtered_threads:
            st.markdown("---")
            st.subheader("💬 Conversations Browser")
            
            with st.expander("💬 Tải và Xem Conversations", expanded=False):
                st.info("📌 **Lưu ý:** Tải conversations có thể mất thời gian tùy theo số lượng threads")
                
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    max_conv = st.slider("Số lượng conversations:", 5, 50, 20)
                    st.write(f"Sẽ tải conversations từ {max_conv} threads đầu tiên")
                
                with col2:
                    load_conversations = st.button("📥 Tải Conversations", type="secondary")
                
                if load_conversations:
                    conversations_data = get_conversations_for_threads(filtered_threads, max_conv)
                    if conversations_data:
                        st.session_state['conversations_data'] = conversations_data
                        st.success(f"✅ Đã tải {len(conversations_data)} conversations")
                    else:
                        st.warning("⚠️ Không tìm thấy conversations")
                
                # Display conversations if available
                if 'conversations_data' in st.session_state:
                    st.markdown("---")
                    display_conversations_browser(st.session_state['conversations_data'])
    
    # Sidebar với thông tin
    with st.sidebar:
        st.markdown("## ⚙️ Cài Đặt Dashboard")
        st.markdown("---")
        
        st.markdown("### 📊 Trạng thái hiện tại")
        if 'report_data' in st.session_state:
            st.success("✅ Có dữ liệu phân tích")
            if 'analysis_params' in st.session_state:
                params = st.session_state['analysis_params']
                st.write(f"**Từ:** {params.get('date_from')}")
                st.write(f"**Đến:** {params.get('date_to')}")
                st.write(f"**Threads:** {len(st.session_state.get('filtered_threads', []))}")
        else:
            st.info("⏳ Chưa có dữ liệu")
        
        st.markdown("---")
        st.markdown("### 🔗 API Connection")
        try:
            analytics = ThreadAnalytics()
            st.success("✅ API Ready")
            st.write(f"**Base URL:** {analytics.base_url}")
        except Exception as e:
            st.error("❌ API Error")
            st.write(f"**Error:** {str(e)}")
        
        st.markdown("---")
        st.markdown("### 💡 Mẹo sử dụng")
        st.markdown("""
        - 🚀 **Nhanh**: Chọn ít ngày + ít threads
        - 📊 **Đầy đủ**: Chọn nhiều ngày + nhiều threads  
        - 💬 **Conversations**: Tải sau khi có dữ liệu chính
        - 🗑️ **Reset**: Dùng "Xóa Cache" nếu có lỗi
        """)

if __name__ == "__main__":
    main() 