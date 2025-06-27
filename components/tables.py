"""
Table components for Tebbi Analytics Dashboard
"""

import streamlit as st
import pandas as pd
from datetime import datetime
from typing import Dict, List, Any
from utils.data_processing import process_threads_data

def display_data_tables(report_data: dict):
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
            df_user = process_threads_data(threads_per_user)
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
                username = data.get('user_info', {}).get('username', '') or data.get('username', '')
                all_users_data.append({
                    'STT': len(all_users_data) + 1,
                    'User ID': user_id,
                    'Display Name': username or data.get('email', '').split('@')[0] if data.get('email') else user_id[:8],
                    'Username': username,
                    'Email': data.get('email', ''),
                    'Thread Count': data.get('thread_count', 0),
                    'Total Messages': data.get('total_messages', 0),
                    'User Messages': data.get('total_user_messages', 0),
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
                    "Total Messages": st.column_config.NumberColumn("Total Messages", width="small"),
                    "User Messages": st.column_config.NumberColumn("User Messages", width="small"),
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
                # Đảm bảo luôn có cột Username
                def get_username(user_info, user_id):
                    if isinstance(user_info, dict):
                        if user_info.get('username'):
                            return user_info['username']
                        elif user_info.get('email'):
                            return user_info['email'].split('@')[0]
                    return user_id[:8]
                df_top['Username'] = df_top.apply(lambda row: get_username(row.get('user_info', {}), row.get('user_id', '')), axis=1)
                st.write(f"**🏆 Top users:** {len(df_top)}")
                st.dataframe(df_top, use_container_width=True, height=400)
        else:
            st.warning("⚠️ Không có dữ liệu top users") 