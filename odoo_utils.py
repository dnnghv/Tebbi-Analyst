import requests
import pandas as pd
import streamlit as st
from datetime import date, timedelta

# Mapping tag và stage
TAG_IDS = {
    9: "Hotel",
    10: "Tour",
    11: "Ticket",
    12: "Flight",
    13: "eSIM",
    14: "VISA",
    15: "Combo",
    16: "MICE",
    17: "Restaurants",
    18: "Car Rental",
    19: "Cruise",
    20: "Team Buildings"
}

STAGE_IDS = {
    1: "New",
    2: "Qualified",
    3: "Proposition",
    4: "Won",
    5: "Lost",
    6: "Cancelled",
    7: "Pending",
    8: "Contacted",
    9: "Follow Up"
}

def get_odoo_leads(date_from=None, date_to=None, state=None, tags=None, limit=1000):
    """Lấy danh sách lead từ Odoo qua JSON-RPC, trả về DataFrame"""
    ODOO_URL = st.secrets["ODOO_URL"]
    ODOO_DB = st.secrets["ODOO_DB"]
    ODOO_USER = st.secrets["ODOO_USER"]
    ODOO_PASSWORD = st.secrets["ODOO_PASSWORD"]
    if not all([ODOO_URL, ODOO_DB, ODOO_USER, ODOO_PASSWORD]):
        return None, "Chưa cấu hình đủ thông tin Odoo trong biến môi trường!"
    auth_data = {
        "jsonrpc": "2.0",
        "method": "call",
        "params": {
            "db": ODOO_DB,
            "login": ODOO_USER,
            "password": ODOO_PASSWORD
        },
        "id": 1
    }
    auth_url = f"{ODOO_URL}/web/session/authenticate"
    try:
        auth_response = requests.post(auth_url, json=auth_data)
        auth_res = auth_response.json()
        if not auth_res.get('result') or not auth_res['result'].get('uid'):
            return None, "Đăng nhập Odoo thất bại!"
        session_id = auth_response.cookies.get('session_id')
        if not session_id:
            return None, "Không lấy được session_id từ Odoo!"
    except Exception as e:
        return None, f"Lỗi khi đăng nhập Odoo: {e}"
    # 2. Build domain filter
    domain = []
    if date_from:
        domain.append(['create_date', '>=', str(date_from)])
    if date_to:
        domain.append(['create_date', '<=', str(date_to)])
    if state:
        domain.append(['stage_id', '=', state])
    if tags:
        domain.append(['tag_ids', 'in', tags])
    # Lọc theo tên người tạo là 'AI Lead Generation'
    domain.append(['create_uid.name', '=', 'AI Lead Generation'])
    # 3. Call search_read
    headers = {'Content-Type': 'application/json', 'Cookie': f'session_id={session_id}'}
    dataset_url = f"{ODOO_URL}/web/dataset/call_kw"
    payload = {
        "jsonrpc": "2.0",
        "method": "call",
        "params": {
            "model": "crm.lead",
            "method": "search_read",
            "args": [],
            "kwargs": {
                "domain": domain,
                "fields": [
                    "id", "create_date", "stage_id", "tag_ids", "name", "email_from", "phone", "contact_name", "description", "create_uid"
                ],
                "limit": limit
            }
        },
        "id": 2
    }
    try:
        res = requests.post(dataset_url, json=payload, headers=headers).json()
        leads = res.get('result', [])
        if not leads:
            return pd.DataFrame(), None
        df = pd.DataFrame(leads)
        return df, None
    except Exception as e:
        return None, f"Lỗi khi lấy danh sách lead: {e}"

def map_tags(tag_list):
    if isinstance(tag_list, list):
        return [TAG_IDS.get(tag, str(tag)) for tag in tag_list]
    return [TAG_IDS.get(tag_list, str(tag_list))] if tag_list else []

def map_stage(stage):
    if isinstance(stage, list) and len(stage) > 0:
        # Odoo có thể trả về [id, name]
        return stage[1]
    if isinstance(stage, int):
        return STAGE_IDS.get(stage, str(stage))
    return str(stage) 