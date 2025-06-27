"""
Chart components for Tebbi Analytics Dashboard
"""

import streamlit as st
import plotly.express as px
import pandas as pd
from datetime import datetime
from typing import Dict, List
from collections import Counter

def create_threads_timeline_chart(report_data: dict):
    """Tạo biểu đồ timeline threads theo ngày"""
    if not report_data or 'threads_by_date' not in report_data:
        st.warning("⚠️ Không có dữ liệu timeline")
        return
    
    threads_by_date = report_data['threads_by_date']
    if not threads_by_date:
        st.warning("⚠️ Không có dữ liệu threads theo ngày")
        return
    
    df = pd.DataFrame(list(threads_by_date.items()), columns=['Date', 'Threads'])
    df['Date'] = pd.to_datetime(df['Date'])
    df = df.sort_values('Date')
    
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

def create_user_distribution_chart(report_data: dict):
    """Tạo biểu đồ phân bố user theo số threads"""
    if not report_data or 'threads_per_user' not in report_data:
        st.warning("⚠️ Không có dữ liệu user distribution")
        return
    
    threads_per_user = report_data['threads_per_user']
    if not threads_per_user:
        st.warning("⚠️ Không có dữ liệu threads per user")
        return
    
    thread_counts = [data.get('thread_count', 0) for data in threads_per_user.values()]
    if len(thread_counts) == 0:
        st.warning("⚠️ Không có dữ liệu threads per user")
        return
    
    bins = [0, 1, 2, 4, 9, 19, 49, 99, 199, 499, 999, float('inf')]
    labels = ['1', '2', '3-4', '5-9', '10-19', '20-49', '50-99', '100-199', '200-499', '500-999', '1000+']
    s = pd.Series(thread_counts)
    cat = pd.cut(s, bins=bins, labels=labels, right=True, include_lowest=True)
    distribution = cat.value_counts().sort_index()
    
    df = pd.DataFrame({'Range': distribution.index, 'Users': distribution.values})
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

def create_top_message_users_chart(report_data: dict, top_n: int = 10):
    """Tạo biểu đồ top user có nhiều message nhất"""
    if not report_data or 'threads_per_user' not in report_data:
        st.warning("⚠️ Không có dữ liệu top message users")
        return
    
    threads_per_user = report_data['threads_per_user']
    data = []
    for user_id, info in threads_per_user.items():
        user_info = info.get('user_info', {})
        display_name = user_info.get('username') or user_info.get('email', '').split('@')[0] if user_info.get('email') else user_id[:8]
        data.append({
            'User': display_name,
            'Messages': info.get('total_messages', 0),
            'User_ID': user_id
        })
    
    df = pd.DataFrame(data)
    df = df.sort_values('Messages', ascending=True).tail(top_n)
    
    fig = px.bar(
        df,
        x='Messages',
        y='User',
        orientation='h',
        title=f'🏆 Top {top_n} Users by Message Count',
        color='Messages',
        color_continuous_scale='plasma',
        text='Messages',
        hover_data={'User_ID': True}
    )
    
    fig.update_layout(
        yaxis={'categoryorder': 'total ascending'},
        xaxis_title="Số Messages",
        yaxis_title="User",
        showlegend=False,
        height=max(400, len(df) * 25 + 100)
    )
    
    fig.update_traces(
        texttemplate='%{text}',
        textposition='outside',
        hovertemplate='<b>%{y}</b><br>%{x} messages<br>ID: %{customdata[0]}<extra></extra>'
    )
    
    st.plotly_chart(fig, use_container_width=True)

def create_messages_timeline_chart(report_data: dict):
    """Tạo biểu đồ timeline messages theo ngày"""
    if not report_data or 'user_stats' not in report_data or 'thread_conversations' not in report_data['user_stats']:
        st.warning("⚠️ Không có dữ liệu timeline messages")
        return
    
    messages_by_date = {}
    for conv in report_data['user_stats']['thread_conversations'].values():
        date = conv.get('created_at', '')[:10]
        msg_count = conv.get('total_messages', 0)
        if date:
            messages_by_date[date] = messages_by_date.get(date, 0) + msg_count
    
    if not messages_by_date:
        st.warning("⚠️ Không có dữ liệu messages theo ngày")
        return
    
    df = pd.DataFrame(list(messages_by_date.items()), columns=['Date', 'Messages'])
    df['Date'] = pd.to_datetime(df['Date'])
    df = df.sort_values('Date')
    
    fig = px.line(
        df,
        x='Date',
        y='Messages',
        title='💬 Messages Timeline',
        markers=True,
        line_shape='linear'
    )
    
    fig.update_layout(
        xaxis_title="Ngày",
        yaxis_title="Số Messages",
        hovermode='x unified',
        showlegend=False,
        height=400
    )
    
    fig.update_traces(
        line=dict(color='#e45756', width=3),
        marker=dict(size=8, color='#ffc300'),
        hovertemplate='<b>%{y}</b> messages<br>%{x|%Y-%m-%d}<extra></extra>'
    )
    
    st.plotly_chart(fig, use_container_width=True)

def create_user_message_distribution_chart(report_data: dict):
    """Tạo biểu đồ phân bố user theo tổng message"""
    if not report_data or 'threads_per_user' not in report_data:
        st.warning("⚠️ Không có dữ liệu user message distribution")
        return
    
    threads_per_user = report_data['threads_per_user']
    if not threads_per_user:
        st.warning("⚠️ Không có dữ liệu threads per user")
        return
    
    message_counts = [data.get('total_messages', 0) for data in threads_per_user.values()]
    bins = [0, 1, 2, 3, 5, 10, 20, 50, 100, 200, 500, 1000, float('inf')]
    labels = ['0', '1', '2', '3-4', '5-9', '10-19', '20-49', '50-99', '100-199', '200-499', '500-999', '1000+']
    
    distribution = Counter()
    for count in message_counts:
        for i, bin_max in enumerate(bins[1:], 0):  # Start from second bin, index from 0
            if count <= bin_max:
                distribution[labels[i]] += 1
                break
    
    df = pd.DataFrame(list(distribution.items()), columns=['Range', 'Users'])
    
    fig = px.bar(
        df,
        x='Range',
        y='Users',
        title='👥 User Distribution by Message Count',
        color='Users',
        color_continuous_scale='viridis',
        text='Users'
    )
    
    fig.update_layout(
        xaxis_title="Số Messages",
        yaxis_title="Số Users",
        showlegend=False,
        height=400
    )
    
    fig.update_traces(
        texttemplate='%{text}',
        textposition='outside',
        hovertemplate='<b>%{y}</b> users<br>có %{x} messages<extra></extra>'
    )
    
    st.plotly_chart(fig, use_container_width=True)

def create_user_message_chart(report_data: dict, top_n: int = 20):
    """Tạo biểu đồ tổng số message theo user"""
    threads_per_user = report_data.get('threads_per_user', {})
    if not threads_per_user:
        st.warning("⚠️ Không có dữ liệu user message")
        return
    
    data = []
    for user_id, info in threads_per_user.items():
        user_info = info.get('user_info', {})
        display_name = user_info.get('username') or user_info.get('email', '').split('@')[0] if user_info.get('email') else user_id[:8]
        data.append({
            'User': display_name,
            'Total Messages': info.get('total_messages', 0)
        })
    
    df = pd.DataFrame(data)
    df = df.sort_values('Total Messages', ascending=False).head(top_n)
    
    fig = px.bar(
        df,
        x='User',
        y='Total Messages',
        title='🔢 Tổng số message theo User',
        text='Total Messages'
    )
    
    fig.update_traces(
        texttemplate='%{text}',
        textposition='outside'
    )
    
    fig.update_layout(
        xaxis_title='User',
        yaxis_title='Tổng Messages',
        height=400
    )
    
    st.plotly_chart(fig, use_container_width=True)

def create_top_thread_users_chart(report_data: dict, top_n: int = 10):
    """Tạo biểu đồ top user có nhiều thread nhất"""
    if not report_data or 'threads_per_user' not in report_data:
        st.warning("⚠️ Không có dữ liệu top thread users")
        return
    
    threads_per_user = report_data['threads_per_user']
    data = []
    for user_id, info in threads_per_user.items():
        user_info = info.get('user_info', {})
        display_name = user_info.get('username') or user_info.get('email', '').split('@')[0] if user_info.get('email') else user_id[:8]
        data.append({
            'User': display_name,
            'Threads': info.get('thread_count', 0),
            'User_ID': user_id
        })
    
    df = pd.DataFrame(data)
    df = df.sort_values('Threads', ascending=True).tail(top_n)
    
    fig = px.bar(
        df,
        x='Threads',
        y='User',
        orientation='h',
        title=f'👑 Top {top_n} Users by Thread Count',
        color='Threads',
        color_continuous_scale='blues',
        text='Threads',
        hover_data={'User_ID': True}
    )
    
    fig.update_layout(
        yaxis={'categoryorder': 'total ascending'},
        xaxis_title="Số Threads",
        yaxis_title="User",
        showlegend=False,
        height=max(400, len(df) * 25 + 100)
    )
    
    fig.update_traces(
        texttemplate='%{text}',
        textposition='outside',
        hovertemplate='<b>%{y}</b><br>%{x} threads<br>ID: %{customdata[0]}<extra></extra>'
    )
    
    st.plotly_chart(fig, use_container_width=True) 