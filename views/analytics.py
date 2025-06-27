"""
Analytics page for Tebbi Analytics Dashboard
"""

import streamlit as st
from datetime import datetime, timedelta, date
from typing import Dict, List, Any, Optional, Tuple
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from utils.thread_analytics import ThreadAnalytics
from components.metrics import display_overview_metrics, display_tool_calling_metrics, create_tool_calling_charts, display_tool_calling_tables, display_combined_metrics_and_charts, display_combined_data_tables
from components.charts import (
    create_threads_timeline_chart,
    create_user_distribution_chart,
    create_top_message_users_chart,
    create_top_thread_users_chart,
    create_messages_timeline_chart,
    create_user_message_distribution_chart,
    create_user_message_chart
)
from components.conversations import display_conversations_browser
from components.tables import display_data_tables
from utils.date_utils import parse_date_range

def display_welcome_message():
    """Hiển thị thông báo chào mừng"""
    st.markdown("""
    <div class="welcome-box">
        <h2>🎯 Chào mừng đến với Tebbi AI Analytics Dashboard!</h2>
        <h4>📋 Hướng dẫn sử dụng:</h4>
        <ol>
            <li>📅 <strong>Chọn khoảng thời gian:</strong> Từ ngày → Đến ngày</li>
            <li>🚀 <strong>Bắt đầu:</strong> Nhấn "Bắt Đầu Thống Kê"</li>
            <li>📊 <strong>Xem kết quả:</strong> Biểu đồ, bảng dữ liệu, conversations</li>
        </ol>
        <p><em>✨ Tất cả dữ liệu được fetch trực tiếp từ API theo thời gian thực!</em></p>
    </div>
    """, unsafe_allow_html=True)

def display_date_filter() -> Tuple[date, date]:
    """Hiển thị bộ lọc ngày"""
    st.markdown('<div class="date-filter">', unsafe_allow_html=True)
    st.subheader("📅 Chọn Khoảng Thời Gian Thống Kê")
    
    col1, col2 = st.columns(2)
    
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
    
    # Validate dates
    if date_from > date_to:
        st.error("❌ Ngày bắt đầu không thể sau ngày kết thúc!")
        return None, None
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Show selected range info
    days_diff = (date_to - date_from).days + 1
    st.markdown(f"""
    <div class="success-box">
        📊 <strong>Sẽ thống kê:</strong> {date_from} ➜ {date_to} ({days_diff} ngày)
    </div>
    """, unsafe_allow_html=True)
    
    return date_from, date_to

@st.cache_data(ttl=300)  # Cache 5 phút
def fetch_and_analyze_threads(date_from: Optional[date] = None, date_to: Optional[date] = None) -> Tuple[Dict, List]:
    """Fetch và analyze threads theo khoảng thời gian"""
    try:
        analytics = ThreadAnalytics()
        
        # Fetch all threads với progress
        progress_container = st.container()
        with progress_container:
            st.info("🔄 Đang kết nối API và lấy dữ liệu threads/search...")
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            progress_bar.progress(0.2)
            status_text.text("📡 Đang gọi API threads/search...")
            
            all_threads = analytics.fetch_all_threads()  # Không giới hạn số lượng thread
            
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
def get_conversations_for_threads(threads: List[dict]) -> List[dict]:
    """Lấy conversations cho các threads"""
    try:
        analytics = ThreadAnalytics()
        conversations = []
        
        # Progress tracking
        progress_container = st.container()
        with progress_container:
            st.info(f"💬 Đang lấy conversations cho {len(threads)} threads...")
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            total_threads = len(threads)
            
            for i, thread in enumerate(threads):
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

def analytics_page():
    """Main function for Analytics page"""
    st.title("📊 Tebbi AI Analytics Dashboard")
    
    # Check if we have existing analysis results
    if 'report_data' not in st.session_state:
        display_welcome_message()
    
    # Date filter section
    date_from, date_to = display_date_filter()
    
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
            date_to=date_to
        )
        
        if report_data:
            # Store in session state
            st.session_state['report_data'] = report_data
            st.session_state['filtered_threads'] = filtered_threads
            st.session_state['analysis_params'] = {
                'date_from': date_from,
                'date_to': date_to
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
            ⏰ <strong>Thời điểm phân tích:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}<br>
            🟢 <b>Debug:</b> Đã lấy {len(st.session_state.get('filtered_threads', []))} threads, phân tích {report_data.get('summary', {}).get('total_threads', 0)} threads
        </div>
        """, unsafe_allow_html=True)
        
        # Combined Metrics and Charts
        display_combined_metrics_and_charts(report_data)
        
        # Combined Data Tables (tool calling + general)
        st.markdown("---")
        display_combined_data_tables(report_data)
        
        # Conversations browser section
        if filtered_threads:
            st.markdown("---")
            st.subheader("💬 Conversations Browser")
            
            with st.expander("💬 Tải và Xem Conversations", expanded=False):
                st.info("📌 **Lưu ý:** Tải conversations có thể mất thời gian tùy theo số lượng threads")
                
                load_conversations = st.button("📥 Tải Conversations", type="secondary", use_container_width=True)
                
                if load_conversations:
                    conversations_data = get_conversations_for_threads(filtered_threads)
                    if conversations_data:
                        st.session_state['conversations_data'] = conversations_data
                        st.success(f"✅ Đã tải {len(conversations_data)} conversations")
                    else:
                        st.warning("⚠️ Không tìm thấy conversations")
                
                # Display conversations if available
                if 'conversations_data' in st.session_state:
                    st.markdown("---")
                    display_conversations_browser(st.session_state['conversations_data'], report_data)
    
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
        except Exception as e:
            st.error("❌ API Error")
            st.write(f"**Error:** {str(e)}")

def create_charts(conversations):
    """Create visualization charts"""
    # Message distribution chart
    message_counts = [conv['message_count'] for conv in conversations]
    df_messages = pd.DataFrame({'message_count': message_counts})
    
    fig_dist = create_message_distribution_chart(df_messages)
    st.plotly_chart(fig_dist, use_container_width=True)

    # Timeline chart
    df_timeline = create_timeline_dataframe(conversations)
    fig_timeline = create_timeline_chart(df_timeline)
    st.plotly_chart(fig_timeline, use_container_width=True)

def create_message_distribution_chart(df):
    """Create message distribution chart"""
    max_messages = df['message_count'].max()
    bin_size = max(1, (max_messages - 0) // 20)  # Ensure at least 1 message per bin
    bins = list(range(0, max_messages + bin_size + 1, bin_size))
    
    hist_data = pd.cut(df['message_count'], bins=bins).value_counts().sort_index()
    
    fig = go.Figure(data=[go.Bar(
        x=[f"{int(b.left)}-{int(b.right)}" for b in hist_data.index],
        y=hist_data.values,
        text=hist_data.values,
        textposition='auto',
    )])
    
    fig.update_layout(
        title="Phân bố số lượng tin nhắn trong hội thoại",
        xaxis_title="Số lượng tin nhắn",
        yaxis_title="Số lượng hội thoại",
        showlegend=False
    )
    
    return fig

def create_timeline_dataframe(conversations):
    """Create timeline dataframe"""
    dates = [datetime.strptime(conv['created_at'][:10], '%Y-%m-%d').date() 
             for conv in conversations]
    return pd.DataFrame({'date': dates})

def create_timeline_chart(df):
    """Create timeline chart"""
    daily_counts = df['date'].value_counts().sort_index()
    
    fig = go.Figure(data=[go.Scatter(
        x=daily_counts.index,
        y=daily_counts.values,
        mode='lines+markers',
        line=dict(width=2),
        marker=dict(size=8),
    )])
    
    fig.update_layout(
        title="Số lượng hội thoại theo thời gian",
        xaxis_title="Ngày",
        yaxis_title="Số lượng hội thoại",
        showlegend=False
    )
    
    return fig 