"""
Metrics components for Tebbi Analytics Dashboard
"""

import streamlit as st
from datetime import datetime
from typing import Dict, Optional, Any
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

def display_overview_metrics(report: Dict[str, Any]):
    """Hiển thị metrics tổng quan"""
    summary = report.get('summary', {})
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="📊 Tổng Threads",
            value=summary.get('total_threads', 0),
            help="Tổng số threads trong khoảng thời gian"
        )
    
    with col2:
        st.metric(
            label="👥 Tổng Users",
            value=summary.get('total_users', 0),
            help="Số lượng users duy nhất"
        )
    
    with col3:
        st.metric(
            label="💬 TB Threads/User",
            value=summary.get('avg_threads_per_user', 0),
            help="Trung bình số threads trên mỗi user"
        )
    
    with col4:
        analysis_date = summary.get('analysis_date', '')
        if analysis_date:
            formatted_date = analysis_date.split('T')[0]
            st.metric(
                label="📅 Ngày Phân Tích",
                value=formatted_date,
                help="Ngày thực hiện phân tích"
            )


def display_tool_calling_metrics(tool_calling_stats: Dict[str, Any]):
    """Hiển thị metrics tool calling"""
    st.subheader("🔧 Tool Calling Statistics")
    
    # Metrics hàng 1
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="🎯 Create Lead",
            value=tool_calling_stats.get('create_lead', 0),
            help="Tổng số lần gọi create_lead"
        )
    
    with col2:
        st.metric(
            label="📧 Send Email",
            value=tool_calling_stats.get('send_email', 0),
            help="Tổng số lần gọi send_email/send_html_email"
        )
    
    with col3:
        st.metric(
            label="🔧 Total Tool Calls",
            value=tool_calling_stats.get('total_tool_calls', 0),
            help="Tổng số lần gọi tất cả tools"
        )
    
    with col4:
        threads_with_tools = tool_calling_stats.get('threads_with_any_tool', 0)
        st.metric(
            label="📈 Threads with Tools",
            value=threads_with_tools,
            help="Số threads có sử dụng tools"
        )
    
    # Metrics hàng 2
    col5, col6 = st.columns(2)
    
    with col5:
        threads_create_lead = tool_calling_stats.get('threads_with_create_lead', 0)
        st.metric(
            label="🎯 Threads w/ Create Lead",
            value=threads_create_lead,
            help="Số threads có gọi create_lead"
        )
    
    with col6:
        threads_send_html_email = tool_calling_stats.get('threads_with_send_html_email', 0)
        st.metric(
            label="📧 Threads w/ Send HTML Email",
            value=threads_send_html_email,
            help="Số threads có gọi send_html_email"
        )


def create_tool_calling_charts(tool_calling_stats: Dict[str, Any]):
    """Tạo charts cho tool calling statistics"""
    
    # 1. Pie chart cho distribution of tool calls
    st.subheader("🥧 Tool Call Distribution")
    
    create_lead = tool_calling_stats.get('create_lead', 0)
    send_html_email = tool_calling_stats.get('send_html_email', 0)
    
    if create_lead > 0 or send_html_email > 0:
        tool_data = []
        if create_lead > 0:
            tool_data.append({'Tool': 'Create Lead', 'Count': create_lead, 'Color': '#FF6B6B'})
        if send_html_email > 0:
            tool_data.append({'Tool': 'Send HTML Email', 'Count': send_html_email, 'Color': '#4ECDC4'})
        
        if tool_data:
            df_tools = pd.DataFrame(tool_data)
            
            fig_pie = px.pie(
                df_tools, 
                values='Count', 
                names='Tool',
                color='Tool',
                color_discrete_map={
                    'Create Lead': '#FF6B6B',
                    'Send HTML Email': '#4ECDC4'
                },
                title="Distribution of Tool Calls"
            )
            fig_pie.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig_pie, use_container_width=True)
    else:
        st.info("Không có dữ liệu tool calling để hiển thị")
    
    # 2. Time series chart nếu có dữ liệu theo ngày
    tool_calls_by_date = tool_calling_stats.get('tool_calls_by_date', {})
    if tool_calls_by_date:
        st.subheader("📈 Tool Calls Over Time")
        
        date_data = []
        for date_str, stats in tool_calls_by_date.items():
            date_data.append({
                'Date': date_str,
                'Create Lead': stats.get('create_lead', 0),
                'Send HTML Email': stats.get('send_html_email', 0),
                'Total': stats.get('total', 0)
            })
        
        df_timeline = pd.DataFrame(date_data)
        df_timeline['Date'] = pd.to_datetime(df_timeline['Date'])
        df_timeline = df_timeline.sort_values('Date')
        
        # Line chart với multiple lines
        fig_timeline = go.Figure()
        
        fig_timeline.add_trace(go.Scatter(
            x=df_timeline['Date'],
            y=df_timeline['Create Lead'],
            mode='lines+markers',
            name='Create Lead',
            line=dict(color='#FF6B6B', width=3),
            marker=dict(size=8)
        ))
        
        fig_timeline.add_trace(go.Scatter(
            x=df_timeline['Date'],
            y=df_timeline['Send HTML Email'],
            mode='lines+markers',
            name='Send HTML Email',
            line=dict(color='#4ECDC4', width=3),
            marker=dict(size=8)
        ))
        

        
        fig_timeline.update_layout(
            title="Tool Calls Timeline",
            xaxis_title="Date",
            yaxis_title="Number of Calls",
            hovermode='x unified',
            showlegend=True
        )
        
        st.plotly_chart(fig_timeline, use_container_width=True)
    
    # 3. Bar chart cho top threads by tool usage
    tool_calls_by_thread = tool_calling_stats.get('tool_calls_by_thread', {})
    if tool_calls_by_thread:
        st.subheader("🏆 Top Threads by Tool Usage")
        
        thread_data = []
        for thread_id, thread_info in tool_calls_by_thread.items():
            tool_stats = thread_info.get('tool_stats', {})
            total_calls = tool_stats.get('total_tool_calls', 0)
            
            if total_calls > 0:  # Chỉ hiển thị threads có tool calls
                metadata = thread_info.get('thread_metadata', {})
                user_id = metadata.get('user_id', 'Unknown')
                
                thread_data.append({
                    'Thread ID': thread_id[:8] + '...',  # Rút gọn thread ID
                    'Full Thread ID': thread_id,
                    'User ID': user_id,
                    'Create Lead': tool_stats.get('create_lead', 0),
                    'Send HTML Email': tool_stats.get('send_html_email', 0),
                    'Total Calls': total_calls
                })
        
        if thread_data:
            df_threads = pd.DataFrame(thread_data)
            df_threads = df_threads.sort_values('Total Calls', ascending=False).head(20)  # Top 20
            
            fig_bar = go.Figure()
            
            fig_bar.add_trace(go.Bar(
                name='Create Lead',
                x=df_threads['Thread ID'],
                y=df_threads['Create Lead'],
                marker_color='#FF6B6B'
            ))
            
            fig_bar.add_trace(go.Bar(
                name='Send HTML Email',
                x=df_threads['Thread ID'],
                y=df_threads['Send HTML Email'],
                marker_color='#4ECDC4'
            ))
            

            
            fig_bar.update_layout(
                title="Top 20 Threads by Tool Usage",
                xaxis_title="Thread ID",
                yaxis_title="Number of Tool Calls",
                barmode='stack',
                xaxis={'categoryorder': 'total descending'}
            )
            
            st.plotly_chart(fig_bar, use_container_width=True)


def display_tool_calling_tables(tool_calling_stats: Dict[str, Any]):
    """Hiển thị bảng dữ liệu chi tiết tool calling"""
    
    st.subheader("📊 Data Tables")
    
    # Tạo tabs cho các tables khác nhau
    tab1, tab2, tab3 = st.tabs(["📅 Tool Calls by Date", "🏆 Top Threads", "🔍 Detailed Tool Calls"])
    
    # Tab 1: Tool Calls by Date
    with tab1:
        tool_calls_by_date = tool_calling_stats.get('tool_calls_by_date', {})
        if tool_calls_by_date:
            date_data = []
            for date_str, stats in tool_calls_by_date.items():
                date_data.append({
                    'Date': date_str,
                    'Create Lead': stats.get('create_lead', 0),
                    'Send HTML Email': stats.get('send_html_email', 0),
                    'Total': stats.get('total', 0)
                })
            
            df_dates = pd.DataFrame(date_data)
            df_dates = df_dates.sort_values('Date', ascending=False)
            st.dataframe(df_dates, use_container_width=True)
        else:
            st.info("Không có dữ liệu tool calls by date")
    
    # Tab 2: Top Threads with Tool Usage
    with tab2:
        tool_calls_by_thread = tool_calling_stats.get('tool_calls_by_thread', {})
        if tool_calls_by_thread:
            thread_data = []
            for thread_id, thread_info in tool_calls_by_thread.items():
                tool_stats = thread_info.get('tool_stats', {})
                total_calls = tool_stats.get('total_tool_calls', 0)
                
                if total_calls > 0:
                    metadata = thread_info.get('thread_metadata', {})
                    
                    thread_data.append({
                        'Thread ID': thread_id,
                        'User ID': metadata.get('user_id', ''),
                        'Created': thread_info.get('created_at', '')[:10],
                        'Create Lead': tool_stats.get('create_lead', 0),
                        'Send HTML Email': tool_stats.get('send_html_email', 0),
                        'Total Calls': total_calls
                    })
            
            if thread_data:
                df_threads = pd.DataFrame(thread_data)
                df_threads = df_threads.sort_values('Total Calls', ascending=False)
                st.dataframe(df_threads, use_container_width=True)
            else:
                st.info("Không có threads nào sử dụng tools")
        else:
            st.info("Không có dữ liệu tool calls by thread")
    
    # Tab 3: Detailed Tool Calls
    with tab3:
        detailed_calls = tool_calling_stats.get('detailed_calls', [])
        if detailed_calls:
            # Chỉ hiển thị create_lead và send_html_email calls
            filtered_calls = [
                call for call in detailed_calls 
                if call.get('function_name') in ['create_lead', 'send_html_email']
            ]
            
            if filtered_calls:
                df_detailed = pd.DataFrame(filtered_calls)
                
                # Rearrange columns với thêm arguments
                columns_order = ['timestamp', 'thread_id', 'function_name', 'arguments', 'call_id', 'message_type']
                df_detailed = df_detailed[columns_order]
                
                # Format timestamp
                df_detailed['timestamp'] = pd.to_datetime(df_detailed['timestamp']).dt.strftime('%Y-%m-%d %H:%M')
                
                # Format arguments - truncate nếu quá dài
                df_detailed['arguments'] = df_detailed['arguments'].apply(
                    lambda x: str(x)[:100] + '...' if len(str(x)) > 100 else str(x)
                )
                
                # Rename columns
                df_detailed.columns = ['Timestamp', 'Thread ID', 'Function', 'Arguments', 'Call ID', 'Message Type']
                
                # Show most recent first
                df_detailed = df_detailed.sort_values('Timestamp', ascending=False)
                
                st.dataframe(df_detailed, use_container_width=True)
                
                # Thêm expander để xem full arguments
                with st.expander("🔍 View Full Arguments Details"):
                    selected_call = st.selectbox(
                        "Select a tool call to view full arguments:",
                        options=range(len(filtered_calls)),
                        format_func=lambda x: f"{filtered_calls[x]['function_name']} - {filtered_calls[x]['call_id'][:8]}..." if x < len(filtered_calls) else ""
                    )
                    
                    if selected_call < len(filtered_calls):
                        call_detail = filtered_calls[selected_call]
                        st.json({
                            "Function": call_detail['function_name'],
                            "Call ID": call_detail['call_id'],
                            "Thread ID": call_detail['thread_id'],
                            "Timestamp": call_detail['timestamp'],
                            "Arguments": call_detail['arguments']
                        })
            else:
                st.info("Không có tool calls để hiển thị")
        else:
            st.info("Không có dữ liệu detailed tool calls")


def display_combined_metrics_and_charts(report_data: Dict[str, Any]):
    """Hiển thị metrics và charts gộp chung"""
    
    st.subheader("📊 Tổng Quan Số Liệu")
    
    # === METRICS SECTION ===
    st.markdown("#### 📈 Số liệu tổng quan")
    
    # Overview metrics
    summary = report_data.get('summary', {})
    
    # Row 1: General metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="📊 Total Threads",
            value=f"{summary.get('total_threads', 0):,}",
            help="Tổng số threads được phân tích"
        )
    
    with col2:
        st.metric(
            label="👥 Total Users",
            value=f"{summary.get('total_users', 0):,}",
            help="Tổng số users"
        )
    
    with col3:
        avg_threads = summary.get('avg_threads_per_user', '0')
        st.metric(
            label="📈 Avg Threads/User",
            value=avg_threads,
            help="Trung bình threads mỗi user"
        )
    
    with col4:
        total_messages = summary.get('total_messages', 0)
        st.metric(
            label="💬 Total Messages",
            value=f"{total_messages:,}",
            help="Tổng số messages trong tất cả threads"
        )
    
    # Row 2: Message metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        user_messages = summary.get('user_messages', 0)
        st.metric(
            label="👤 User Messages",
            value=f"{user_messages:,}",
            help="Tổng số messages của users"
        )
    
    with col2:
        ai_messages = summary.get('ai_messages', 0)
        st.metric(
            label="🤖 AI Messages", 
            value=f"{ai_messages:,}",
            help="Tổng số messages của AI"
        )
    
    with col3:
        avg_messages = summary.get('avg_messages_per_user', 0)
        st.metric(
            label="📈 Avg Messages/User",
            value=f"{avg_messages:.1f}",
            help="Trung bình messages mỗi user"
        )
    
    with col4:
        avg_msg_thread = summary.get('avg_messages_per_thread', 0)
        st.metric(
            label="📈 Avg Messages/Thread",
            value=f"{avg_msg_thread:.1f}",
            help="Trung bình messages mỗi thread"
        )
    
    # Row 3: Peak day statistics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        peak_day = summary.get('peak_day', 'N/A')
        st.metric(
            label="📅 Peak Day",
            value=peak_day,
            help="Ngày có nhiều threads nhất"
        )
    
    with col2:
        peak_threads = summary.get('peak_threads', 0)
        st.metric(
            label="📊 Peak Threads",
            value=f"{peak_threads:,}",
            help="Số threads trong ngày peak"
        )
    
    with col3:
        # Activity days
        threads_by_date = report_data.get('threads_by_date', {})
        active_days = len(threads_by_date)
        st.metric(
            label="📅 Active Days",
            value=f"{active_days:,}",
            help="Số ngày có hoạt động"
        )
    
    with col4:
        # Average threads per day
        avg_threads_per_day = summary.get('total_threads', 0) / active_days if active_days > 0 else 0
        st.metric(
            label="📈 Avg Threads/Day",
            value=f"{avg_threads_per_day:.1f}",
            help="Trung bình threads mỗi ngày"
        )
    
    # Row 4: Tool calling metrics (if available)
    tool_calling_stats = report_data.get('tool_calling_stats', {})
    if tool_calling_stats:
        st.markdown("#### 🔧 Tool Calling Statistics")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                label="🔧 Total Tool Calls",
                value=f"{tool_calling_stats.get('total_tool_calls', 0):,}",
                help="Tổng số lần gọi tất cả tools"
            )
        
        with col2:
            st.metric(
                label="🎯 Create Lead Calls",
                value=f"{tool_calling_stats.get('create_lead', 0):,}",
                help="Số lần gọi create_lead"
            )
        
        with col3:
            st.metric(
                label="📧 Send HTML Email Calls",
                value=f"{tool_calling_stats.get('send_html_email', 0):,}",
                help="Số lần gọi send_html_email"
            )
        
        with col4:
            threads_with_tools = tool_calling_stats.get('threads_with_any_tool', 0)
            st.metric(
                label="📈 Threads with Tools",
                value=threads_with_tools,
                help="Số threads có sử dụng tools"
            )
    
    # === CHARTS SECTION ===
    st.markdown("---")
    st.subheader("📈 Biểu Đồ Thống Kê Tổng Hợp")
    
    # Create tabs for different chart categories
    tab1, tab2, tab3 = st.tabs(["📊 General Analytics", "🔧 Tool Calling", "👥 User Analytics"])
    
    # Tab 1: General Analytics
    with tab1:
        col1, col2 = st.columns(2)
        
        with col1:
            # Import charts từ components.charts
            from components.charts import (
                create_threads_timeline_chart,
                create_messages_timeline_chart,
                create_user_distribution_chart
            )
            
            create_threads_timeline_chart(report_data)
            create_user_distribution_chart(report_data)
        
        with col2:
            from components.charts import (
                create_top_thread_users_chart,
                create_top_message_users_chart
            )
            
            create_top_thread_users_chart(report_data)
            create_top_message_users_chart(report_data)
    
    # Tab 2: Tool Calling Charts
    with tab2:
        if tool_calling_stats:
            # Tool calling pie chart
            st.markdown("##### 🥧 Tool Call Distribution")
            create_lead = tool_calling_stats.get('create_lead', 0)
            send_html_email = tool_calling_stats.get('send_html_email', 0)
            
            if create_lead > 0 or send_html_email > 0:
                tool_data = []
                if create_lead > 0:
                    tool_data.append({'Tool': 'Create Lead', 'Count': create_lead, 'Color': '#FF6B6B'})
                if send_html_email > 0:
                    tool_data.append({'Tool': 'Send HTML Email', 'Count': send_html_email, 'Color': '#4ECDC4'})
                
                if tool_data:
                    df_tools = pd.DataFrame(tool_data)
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        fig_pie = px.pie(
                            df_tools, 
                            values='Count', 
                            names='Tool',
                            color='Tool',
                            color_discrete_map={
                                'Create Lead': '#FF6B6B',
                                'Send HTML Email': '#4ECDC4'
                            },
                            title="Distribution of Tool Calls"
                        )
                        fig_pie.update_traces(textposition='inside', textinfo='percent+label')
                        st.plotly_chart(fig_pie, use_container_width=True)
                    
                    with col2:
                        # Tool calls timeline if available
                        tool_calls_by_date = tool_calling_stats.get('tool_calls_by_date', {})
                        if tool_calls_by_date:
                            date_data = []
                            for date_str, stats in tool_calls_by_date.items():
                                date_data.append({
                                    'Date': date_str,
                                    'Create Lead': stats.get('create_lead', 0),
                                    'Send HTML Email': stats.get('send_html_email', 0),
                                    'Total': stats.get('total', 0)
                                })
                            
                            df_timeline = pd.DataFrame(date_data)
                            df_timeline['Date'] = pd.to_datetime(df_timeline['Date'])
                            df_timeline = df_timeline.sort_values('Date')
                            
                            # Line chart
                            fig_timeline = go.Figure()
                            
                            fig_timeline.add_trace(go.Scatter(
                                x=df_timeline['Date'],
                                y=df_timeline['Create Lead'],
                                mode='lines+markers',
                                name='Create Lead',
                                line=dict(color='#FF6B6B', width=3),
                                marker=dict(size=8)
                            ))
                            
                            fig_timeline.add_trace(go.Scatter(
                                x=df_timeline['Date'],
                                y=df_timeline['Send HTML Email'],
                                mode='lines+markers',
                                name='Send HTML Email',
                                line=dict(color='#4ECDC4', width=3),
                                marker=dict(size=8)
                            ))
                            
                            fig_timeline.update_layout(
                                title="Tool Calls Timeline",
                                xaxis_title="Date",
                                yaxis_title="Number of Calls",
                                hovermode='x unified',
                                showlegend=True
                            )
                            
                            st.plotly_chart(fig_timeline, use_container_width=True)
            else:
                st.info("Không có dữ liệu tool calling để hiển thị")
        else:
            st.info("Không có dữ liệu tool calling")
    
    # Tab 3: User Analytics
    with tab3:
        col1, col2 = st.columns(2)
        
        with col1:
            from components.charts import (
                create_user_message_distribution_chart,
                create_user_message_chart
            )
            
            create_user_message_distribution_chart(report_data)
        
        with col2:
            create_user_message_chart(report_data) 


def display_combined_data_tables(report_data: Dict[str, Any]):
    """Hiển thị tất cả data tables gộp chung"""
    
    st.subheader("📊 Data Tables")
    
    # Get tool calling stats
    tool_calling_stats = report_data.get('tool_calling_stats', {})
    
    # Create tabs for all data tables
    if tool_calling_stats:
        # If we have tool calling data, show 6 tabs
        tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
            "📅 Tool Calls by Date", 
            "🏆 Top Threads (Tools)", 
            "🔍 Detailed Tool Calls",
            "📊 Threads by Date",
            "👥 Top Users", 
            "📈 User Statistics"
        ])
        
        # Tool calling tables
        with tab1:
            tool_calls_by_date = tool_calling_stats.get('tool_calls_by_date', {})
            if tool_calls_by_date:
                date_data = []
                for date_str, stats in tool_calls_by_date.items():
                    date_data.append({
                        'Date': date_str,
                        'Create Lead': stats.get('create_lead', 0),
                        'Send HTML Email': stats.get('send_html_email', 0),
                        'Total': stats.get('total', 0)
                    })
                
                df_dates = pd.DataFrame(date_data)
                df_dates = df_dates.sort_values('Date', ascending=False)
                st.dataframe(df_dates, use_container_width=True)
            else:
                st.info("Không có dữ liệu tool calls by date")
        
        with tab2:
            tool_calls_by_thread = tool_calling_stats.get('tool_calls_by_thread', {})
            if tool_calls_by_thread:
                thread_data = []
                for thread_id, thread_info in tool_calls_by_thread.items():
                    tool_stats = thread_info.get('tool_stats', {})
                    total_calls = tool_stats.get('total_tool_calls', 0)
                    
                    if total_calls > 0:
                        metadata = thread_info.get('thread_metadata', {})
                        
                        thread_data.append({
                            'Thread ID': thread_id,
                            'User ID': metadata.get('user_id', ''),
                            'Created': thread_info.get('created_at', '')[:10],
                            'Create Lead': tool_stats.get('create_lead', 0),
                            'Send HTML Email': tool_stats.get('send_html_email', 0),
                            'Total Calls': total_calls
                        })
            
                if thread_data:
                    df_threads = pd.DataFrame(thread_data)
                    df_threads = df_threads.sort_values('Total Calls', ascending=False)
                    st.dataframe(df_threads, use_container_width=True)
                else:
                    st.info("Không có threads nào sử dụng tools")
            else:
                st.info("Không có dữ liệu tool calls by thread")
        
        with tab3:
            detailed_calls = tool_calling_stats.get('detailed_calls', [])
            if detailed_calls:
                # Chỉ hiển thị create_lead và send_html_email calls
                filtered_calls = [
                    call for call in detailed_calls 
                    if call.get('function_name') in ['create_lead', 'send_html_email']
                ]
                
                if filtered_calls:
                    df_detailed = pd.DataFrame(filtered_calls)
                    
                    # Rearrange columns với thêm arguments
                    columns_order = ['timestamp', 'thread_id', 'function_name', 'arguments', 'call_id', 'message_type']
                    df_detailed = df_detailed[columns_order]
                    
                    # Format timestamp
                    df_detailed['timestamp'] = pd.to_datetime(df_detailed['timestamp']).dt.strftime('%Y-%m-%d %H:%M')
                    
                    # Format arguments - truncate nếu quá dài
                    df_detailed['arguments'] = df_detailed['arguments'].apply(
                        lambda x: str(x)[:100] + '...' if len(str(x)) > 100 else str(x)
                    )
                    
                    # Rename columns
                    df_detailed.columns = ['Timestamp', 'Thread ID', 'Function', 'Arguments', 'Call ID', 'Message Type']
                    
                    # Show most recent first
                    df_detailed = df_detailed.sort_values('Timestamp', ascending=False)
                    
                    st.dataframe(df_detailed, use_container_width=True)
                    
                    # Thêm expander để xem full arguments
                    with st.expander("🔍 View Full Arguments Details"):
                        selected_call = st.selectbox(
                            "Select a tool call to view full arguments:",
                            options=range(len(filtered_calls)),
                            format_func=lambda x: f"{filtered_calls[x]['function_name']} - {filtered_calls[x]['call_id'][:8]}..." if x < len(filtered_calls) else ""
                        )
                        
                        if selected_call < len(filtered_calls):
                            call_detail = filtered_calls[selected_call]
                            st.json({
                                "Function": call_detail['function_name'],
                                "Call ID": call_detail['call_id'],
                                "Thread ID": call_detail['thread_id'],
                                "Timestamp": call_detail['timestamp'],
                                "Arguments": call_detail['arguments']
                            })
                else:
                    st.info("Không có tool calls để hiển thị")
            else:
                st.info("Không có dữ liệu detailed tool calls")
    else:
        # If no tool calling data, show only general tables
        tab4, tab5, tab6 = st.tabs(["📊 Threads by Date", "👥 Top Users", "📈 User Statistics"])
    
    # General data tables (always show these)
    with tab4 if tool_calling_stats else tab1:
        # Threads by date table
        threads_by_date = report_data.get('threads_by_date', {})
        if threads_by_date:
            date_data = []
            for date, count in threads_by_date.items():
                date_data.append({'Date': date, 'Threads': count})
            
            df_dates = pd.DataFrame(date_data)
            df_dates = df_dates.sort_values('Date', ascending=False)
            st.dataframe(df_dates, use_container_width=True)
        else:
            st.info("Không có dữ liệu threads by date")
    
    with tab5 if tool_calling_stats else tab2:
        # Top users table
        top_users = report_data.get('top_users', [])
        if top_users:
            users_data = []
            for user in top_users:
                user_info = user.get('user_info', {})
                users_data.append({
                    'User ID': user['user_id'][:8] + '...',
                    'Full User ID': user['user_id'],
                    'Username': user_info.get('username', 'N/A'),
                    'Email': user_info.get('email', 'N/A'),
                    'Name': user_info.get('name', 'N/A'),
                    'Thread Count': user['thread_count'],
                    'Avg Messages': user.get('avg_messages_per_thread', 0),
                    'Total Messages': user.get('total_messages', 0)
                })
            
            df_users = pd.DataFrame(users_data)
            st.dataframe(df_users, use_container_width=True)
        else:
            st.info("Không có dữ liệu top users")
    
    with tab6 if tool_calling_stats else tab3:
        # User statistics table
        user_stats = report_data.get('user_stats', {})
        if user_stats and 'threads_per_user' in user_stats:
            stats_data = []
            threads_per_user = user_stats['threads_per_user']
            
            for user_id, user_data in threads_per_user.items():
                user_info = user_data.get('user_info', {})
                stats_data.append({
                    'User ID': user_id[:8] + '...',
                    'Full User ID': user_id,
                    'Username': user_info.get('username', 'N/A'),
                    'Email': user_info.get('email', 'N/A'),
                    'Threads': user_data.get('thread_count', 0),
                    'Total Messages': user_data.get('total_messages', 0),
                    'Avg Msg/Thread': user_data.get('avg_messages_per_thread', 0),
                    'First Thread': user_data.get('first_thread_time', 'N/A')[:10],
                    'Last Thread': user_data.get('last_thread_time', 'N/A')[:10],
                    'User Lifetime': user_data.get('user_lifetime_human', 'N/A')
                })
            
            df_stats = pd.DataFrame(stats_data)
            df_stats = df_stats.sort_values('Threads', ascending=False)
            st.dataframe(df_stats, use_container_width=True)
        else:
            st.info("Không có dữ liệu user statistics") 