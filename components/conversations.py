"""
Conversation components for Tebbi Analytics Dashboard
"""

import streamlit as st
from datetime import datetime
from typing import Dict, List, Any
from utils.data_processing import get_user_display_name, organize_conversations_by_user, process_user_options

def display_conversations_browser(conversations_data: List[dict], report_data: dict = None):
    """Hiển thị trình duyệt conversations"""
    if not conversations_data:
        st.warning("⚠️ Không có dữ liệu conversations")
        return
    
    st.subheader("💬 Conversations Browser")
    
    # Organize by user
    users_conversations = organize_conversations_by_user(conversations_data)
    
    if not users_conversations:
        st.warning("⚠️ Không tìm thấy conversations")
        return
    
    # User selector với tên đầy đủ - lấy thông tin từ analytics data
    threads_per_user = report_data.get('threads_per_user', {}) if report_data else {}
    user_options = process_user_options(users_conversations, threads_per_user)
    
    selected_user_display = st.selectbox(
        "👤 Chọn User:",
        list(user_options.keys()),
        help="Chọn user để xem conversations"
    )
    
    if not selected_user_display:
        return
    
    selected_user_id = user_options[selected_user_display]
    user_convs = users_conversations[selected_user_id]
    
    # Show user info - Lấy từ analytics data
    user_metadata = {}
    
    # Lấy user info từ analytics data (threads_per_user)
    if selected_user_id in threads_per_user:
        user_metadata = threads_per_user[selected_user_id].get('user_info', {})
    
    with st.expander("👤 User Information", expanded=True):
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.write(f"**User ID:** {selected_user_id}")
            st.write(f"**Name:** {user_metadata.get('name', 'N/A')}")
            st.write(f"**Username:** {user_metadata.get('username', 'N/A')}")
            st.write(f"**Email:** {user_metadata.get('email', 'N/A')}")
            st.write(f"**Phone:** {user_metadata.get('phoneNumber', user_metadata.get('phone', 'N/A'))}")
            user_stats = threads_per_user.get(selected_user_id, {})
            st.write(f"**💬 Tổng messages:** {user_stats.get('total_messages', 'N/A')}")
            st.write(f"**💬 Messages của user:** {user_stats.get('total_user_messages', 'N/A')}")
        
        with col2:
            st.metric("📝 Total Threads", len(user_convs))
        
        # Debug info to see what's available
        with st.expander("🔍 Debug - User Data Sources", expanded=False):
            st.write("**User info từ analytics data:**")
            if selected_user_id in threads_per_user:
                analytics_user_data = threads_per_user[selected_user_id]
                st.json(analytics_user_data)
            else:
                st.write("Không tìm thấy trong analytics data")
            
            st.write("**User metadata hiện tại:**")
            st.json(user_metadata)
            
            st.write("**Sample conversation metadata:**")
            if user_convs:
                sample_metadata = user_convs[0].get('metadata', {})
                st.json(sample_metadata)
    
    # Thread selector
    thread_options = {}
    for conv in user_convs:
        thread_id = conv.get('thread_id', '')
        message_count = conv.get('message_count', 0)
        updated_at = conv.get('updated_at', '')[:10] if conv.get('updated_at') else 'N/A'
        thread_options[f"Thread {thread_id}... ({message_count} msg) - {updated_at}"] = conv
    
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
    
    if not conversation:
        st.warning("⚠️ Không có messages hợp lệ")
        return
        
    # Display messages
    for msg in conversation:
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
            # Lấy user name từ analytics data
            user_info_for_display = {}
            if selected_user_id in threads_per_user:
                user_info_for_display = threads_per_user[selected_user_id].get('user_info', {})
            user_name = get_user_display_name(user_info_for_display, selected_user_id)
            
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