"""
Odoo Leads page for Tebbi Analytics Dashboard
"""

import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import plotly.express as px
from utils.odoo_utils import get_odoo_leads, TAG_IDS, STAGE_IDS, map_tags, map_stage

def odoo_lead_page():
    """Main function for Odoo Leads page"""
    st.title("📊 Odoo Lead Dashboard")
    st.markdown("""
    <div style='background-color:#f0f2f6; border-radius:8px; padding:16px; margin-bottom:16px;'>
        <b>Chức năng:</b> Thống kê, lọc và phân tích các Lead được tạo bởi <span style='color:#1976d2;'>AI Lead Generation</span> trên Odoo.<br>
        <ul style='margin:8px 0 0 18px;'>
            <li>Chọn khoảng ngày, trạng thái, tags để lọc.</li>
            <li>Kết quả chỉ hiển thị các lead do <b>AI Lead Generation</b> tạo.</li>
            <li>Có thể tải bảng dữ liệu về file CSV.</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)

    with st.expander("🔎 Bộ lọc dữ liệu", expanded=True):
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            odoo_date_from = st.date_input("Lead từ ngày", value=date.today() - timedelta(days=7), key="odoo_date_from")
        with col2:
            odoo_date_to = st.date_input("Lead đến ngày", value=date.today(), key="odoo_date_to")
        with col3:
            # Selectbox cho trạng thái
            stage_options = ["Tất cả"] + [f"{v} (ID:{k})" for k, v in STAGE_IDS.items()]
            stage_display = st.selectbox("Trạng thái (stage_id)", stage_options, key="odoo_state")
            if stage_display != "Tất cả":
                odoo_state = int(stage_display.split("ID:")[-1].replace(")", ""))
            else:
                odoo_state = None
        with col4:
            # Selectbox cho tags (multi-select)
            tag_options = [f"{v} (ID:{k})" for k, v in TAG_IDS.items()]
            selected_tags = st.multiselect("Tags", tag_options, key="odoo_tags")
            tags_list = [int(tag.split("ID:")[-1].replace(")", "")) for tag in selected_tags]
        st.caption("*Chỉ hiển thị các lead do <b>AI Lead Generation</b> tạo ra*", unsafe_allow_html=True)
        filter_btn = st.button("🔍 Thống kê Lead Odoo", use_container_width=True)

    if filter_btn:
        with st.spinner("Đang lấy dữ liệu lead từ Odoo..."):
            df, err = get_odoo_leads(
                date_from=odoo_date_from,
                date_to=odoo_date_to,
                state=odoo_state,
                tags=tags_list if tags_list else None
            )
            if err:
                st.error(err)
            elif df is not None and not df.empty:
                st.success(f"Tổng số lead: {len(df)} ✅")
                # Tổng quan
                n_tags = df['tag_ids'].explode().nunique() if 'tag_ids' in df else 0
                n_stages = df['stage_id'].apply(lambda x: x[0] if isinstance(x, list) else x).nunique() if 'stage_id' in df else 0
                st.markdown(f"""
                <div style='background:#e3f2fd; border-radius:8px; padding:10px 18px; margin-bottom:10px;'>
                    <b>📊 Tổng quan:</b> <br>
                    <b>- Số lead:</b> <span style='color:#1976d2;'>{len(df)}</span> &nbsp;|&nbsp;
                    <b>- Số tag khác nhau:</b> <span style='color:#388e3c;'>{n_tags}</span> &nbsp;|&nbsp;
                    <b>- Số trạng thái:</b> <span style='color:#f57c00;'>{n_stages}</span>
                </div>
                """, unsafe_allow_html=True)
                # Timeline chart
                df['create_date'] = pd.to_datetime(df['create_date'])
                df['date'] = df['create_date'].dt.date
                timeline = df.groupby('date').size().reset_index(name='Leads')
                fig1 = px.line(timeline, x='date', y='Leads', markers=True, title='Timeline số lượng lead theo ngày')
                fig1.update_layout(margin=dict(l=10, r=10, t=40, b=10), height=320)
                st.plotly_chart(fig1, use_container_width=True)

                # Pie chart cho phân bố lead theo tags
                df_tags = df.explode('tag_ids')
                tag_counts = df_tags['tag_ids'].value_counts()
                tag_data = pd.DataFrame({
                    'Tag': [TAG_IDS.get(tag, str(tag)) for tag in tag_counts.index],
                    'Count': tag_counts.values
                })
                fig_pie = px.pie(
                    tag_data,
                    values='Count',
                    names='Tag',
                    title='Phân bố Lead theo Tags',
                    color_discrete_sequence=px.colors.qualitative.Set3
                )
                fig_pie.update_traces(textposition='inside', textinfo='percent+label')
                fig_pie.update_layout(margin=dict(l=10, r=10, t=40, b=10), height=320)
                st.plotly_chart(fig_pie, use_container_width=True)

                # By tag (map to names)
                df['tag_names'] = df['tag_ids'].apply(map_tags)
                tag_exploded = df.explode('tag_names')
                tag_counts = tag_exploded['tag_names'].value_counts().reset_index()
                tag_counts.columns = ['Tag', 'Leads']
                fig3 = px.bar(tag_counts, x='Tag', y='Leads', title='Số lượng lead theo tag', color='Leads', color_continuous_scale='Blues')
                fig3.update_layout(margin=dict(l=10, r=10, t=40, b=10), height=320)
                st.plotly_chart(fig3, use_container_width=True)
                # Mapping stage_id sang tên
                df['stage_name'] = df['stage_id'].apply(map_stage)
                # Hiển thị bảng dữ liệu lead trực tiếp
                df['tag_names'] = df['tag_names'].apply(lambda x: ', '.join(x) if isinstance(x, list) else str(x))
                # Thêm cột Creator chỉ lấy tên người tạo
                def extract_creator_name(create_uid):
                    if isinstance(create_uid, list) and len(create_uid) > 1:
                        return create_uid[1]
                    if isinstance(create_uid, str):
                        return create_uid
                    return str(create_uid)
                df['Creator'] = df['create_uid'].apply(extract_creator_name)
                st.markdown('### 📋 Bảng dữ liệu Lead')
                st.dataframe(
                    df[[
                        'id', 'name', 'create_date', 'stage_name', 'email_from', 'phone', 'contact_name', 'description', 'tag_names', 'Creator'
                    ]],
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        'id': st.column_config.NumberColumn("ID", width="small"),
                        'name': st.column_config.TextColumn("Tên Lead", width="large"),
                        'create_date': st.column_config.DatetimeColumn("Ngày tạo", width="medium"),
                        'stage_name': st.column_config.TextColumn("Trạng thái", width="medium"),
                        'email_from': st.column_config.TextColumn("Email khách hàng", width="large"),
                        'phone': st.column_config.TextColumn("SĐT", width="medium"),
                        'contact_name': st.column_config.TextColumn("Tên liên hệ", width="medium"),
                        'description': st.column_config.TextColumn("Mô tả", width="large"),
                        'tag_names': st.column_config.TextColumn("Tags", width="small"),
                        'Creator': st.column_config.TextColumn("Người tạo", width="medium")
                    }
                )
                # Nút tải về CSV
                csv = df.to_csv(index=False)
                st.download_button(
                    label="📥 Tải bảng dữ liệu CSV",
                    data=csv,
                    file_name=f"odoo_leads_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                    mime="text/csv"
                )
            else:
                st.warning('Không có dữ liệu lead phù hợp!') 