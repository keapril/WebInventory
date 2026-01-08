# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import io
import json
import time
import requests
import boto3
from botocore.exceptions import NoCredentialsError
from PIL import Image
from datetime import datetime, timedelta, timezone, date

# Firebase 相關套件
import firebase_admin
from firebase_admin import credentials, firestore, storage

# --- 1. 網頁基礎設定 ---
st.set_page_config(
    page_title="WebInventory",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==========================================
# 🔧【設定值】Bucket 名稱 (Firebase Fallback)
# ==========================================
CUSTOM_BUCKET_NAME = "product-system-900c4.firebasestorage.app"

# --- 2. Firebase 初始化 ---
firebase_app = None
if not firebase_admin._apps:
    try:
        if "firebase" not in st.secrets:
            st.error("系統錯誤:找不到 Firebase 金鑰配置。")
            st.stop()
        
        token_content = st.secrets["firebase"]["text_key"]
        try:
            key_dict = json.loads(token_content, strict=False)
        except json.JSONDecodeError:
            try:
                key_dict = json.loads(token_content.replace('\n', '\\n'), strict=False)
            except:
                st.error("系統錯誤:金鑰解析失敗。")
                st.stop()

        if "private_key" in key_dict:
            key_dict["private_key"] = key_dict["private_key"].replace("\\n", "\n")

        cred = credentials.Certificate(key_dict)
        firebase_app = firebase_admin.initialize_app(cred, {
            'storageBucket': CUSTOM_BUCKET_NAME
        })
    except Exception as e:
        st.error(f"連線失敗: {e}")
        st.stop()
else:
    try:
        firebase_app = firebase_admin.get_app()
    except Exception:
        firebase_app = None

if not firebase_app:
    st.error("Firebase 未初始化。")
    st.stop()

db = firestore.client(app=firebase_app)
try:
    bucket = storage.bucket(name=CUSTOM_BUCKET_NAME)
except Exception as e:
    pass 

COLLECTION_products = "instrument_consumables" 
COLLECTION_logs = "consumables_logs"

# --- 3. UI 設計：專業 SaaS 風格 (Enterprise Clean) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Noto+Sans+TC:wght@400;500;700&display=swap');

    :root {
        --primary-color: #2563EB;   /* 專業藍 */
        --bg-color: #F3F4F6;        /* 淺灰底色 */
        --card-bg: #FFFFFF;         /* 純白卡片 */
        --text-main: #111827;       /* 深灰 */
        --text-sub: #6B7280;        /* 次要灰 */
        --border-color: #E5E7EB;    /* 邊框灰 */
        --shadow-sm: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
        --font-family: 'Inter', 'Noto Sans TC', sans-serif;
    }

    /* 全局設定 */
    .stApp {
        background-color: var(--bg-color);
        color: var(--text-main);
        font-family: var(--font-family);
    }
    
    section[data-testid="stSidebar"] {
        background-color: #FFFFFF;
        border-right: 1px solid var(--border-color);
    }
    .sidebar-brand {
        font-size: 1.25rem;
        font-weight: 700;
        color: var(--text-main);
        padding: 1rem 0;
        border-bottom: 1px solid var(--border-color);
        margin-bottom: 1.5rem;
        display: flex;
        align-items: center;
        gap: 10px;
    }

    h1, h2, h3 {
        font-family: var(--font-family) !important;
        color: var(--text-main) !important;
        font-weight: 600 !important;
        letter-spacing: -0.025em;
    }

    /* SaaS 卡片設計 */
    .saas-card {
        background-color: var(--card-bg);
        border: 1px solid var(--border-color);
        border-radius: 8px;
        padding: 16px;
        margin-bottom: 12px;
        box-shadow: var(--shadow-sm);
        display: flex;
        align-items: center;
        gap: 16px;
        transition: border-color 0.15s ease-in-out;
    }
    .saas-card:hover {
        border-color: var(--primary-color);
    }

    .saas-thumb {
        width: 64px;
        height: 64px;
        border-radius: 6px;
        background-color: #F9FAFB;
        border: 1px solid var(--border-color);
        object-fit: cover;
        flex-shrink: 0;
    }
    .saas-thumb-placeholder {
        width: 64px;
        height: 64px;
        border-radius: 6px;
        background-color: #F3F4F6;
        color: #9CA3AF;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.2rem;
        flex-shrink: 0;
    }

    .saas-content {
        flex-grow: 1;
        display: grid;
        grid-template-columns: 2fr 1.5fr 1.5fr;
        gap: 12px;
        align-items: center;
    }
    
    .col-main { display: flex; flex-direction: column; }
    .item-title { font-size: 1rem; font-weight: 600; color: var(--text-main); margin-bottom: 4px; }
    .item-sku {
        font-size: 0.8rem;
        font-family: monospace;
        color: var(--text-sub);
        background: #F3F4F6;
        padding: 2px 6px;
        border-radius: 4px;
        display: inline-block;
        width: fit-content;
    }

    .col-meta { font-size: 0.85rem; color: var(--text-sub); }
    .meta-row { display: flex; align-items: center; gap: 6px; margin-bottom: 2px; }

    .col-stock { text-align: right; display: flex; flex-direction: column; align-items: flex-end; }
    .stock-number { font-size: 1.25rem; font-weight: 600; color: var(--text-main); }
    
    .status-badge {
        font-size: 0.75rem;
        padding: 2px 8px;
        border-radius: 99px;
        font-weight: 500;
        display: inline-flex;
        align-items: center;
        gap: 4px;
    }
    .badge-success { background: #ECFDF5; color: #059669; border: 1px solid #D1FAE5; }
    .badge-warning { background: #FFFBEB; color: #D97706; border: 1px solid #FEF3C7; }
    .badge-danger { background: #FEF2F2; color: #DC2626; border: 1px solid #FEE2E2; }
    
    div.stButton > button {
        border-radius: 6px;
        font-weight: 500;
        border: 1px solid #D1D5DB;
        background: white;
        color: #374151;
        box-shadow: var(--shadow-sm);
    }
    div.stButton > button:hover {
        border-color: #9CA3AF;
        background: #F9FAFB;
        color: #111;
    }
    div.stButton > button[kind="primary"] {
        background: var(--primary-color);
        color: white;
        border: none;
    }
    div.stButton > button[kind="primary"]:hover {
        background: #1D4ED8;
    }
    
    .stTextInput input, .stNumberInput input, .stSelectbox div[data-baseweb="select"], .stTextArea textarea {
        border-radius: 6px;
        border-color: #D1D5DB;
    }
    
    .block-container { padding-top: 2rem; }
    </style>
    """, unsafe_allow_html=True)

# --- 4. 核心函數庫 ---

def get_taiwan_time():
    tz = timezone(timedelta(hours=8))
    return datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")

@st.cache_data(ttl=300)
def load_data():
    try:
        docs = db.collection(COLLECTION_products).stream()
        data = []
        for doc in docs:
            d = doc.to_dict()
            data.append({
                "SKU": doc.id,
                "Code": d.get("code", ""),
                "Category": d.get("categoryName", ""),
                "Number": d.get("number", ""),
                "Name": d.get("name", ""),
                "ImageFile": d.get("imageFile", ""),
                "Stock": d.get("stock", 0),
                "Location": d.get("location", ""),
                "SN": d.get("sn", ""),
                "WarrantyStart": d.get("warrantyStart", ""),
                "WarrantyEnd": d.get("warrantyEnd", ""),
                "Accessories": d.get("accessories", "") # 🆕 新增配件欄位
            })
        
        default_cols = ["SKU", "Code", "Category", "Number", "Name", "ImageFile", "Stock", "Location", "SN", "WarrantyStart", "WarrantyEnd", "Accessories"]
        if not data: return pd.DataFrame(columns=default_cols)
        df = pd.DataFrame(data)
        for col in default_cols:
            if col not in df.columns: df[col] = ""
        
        df["WarrantyStart"] = pd.to_datetime(df["WarrantyStart"], errors='coerce')
        df["WarrantyEnd"] = pd.to_datetime(df["WarrantyEnd"], errors='coerce')
        df["Stock"] = pd.to_numeric(df["Stock"], errors='coerce').fillna(0).astype(int)
        return df
    except Exception as e:
        st.error(f"資料讀取錯誤: {e}")
        return pd.DataFrame(columns=default_cols)

def load_log():
    try:
        docs = db.collection(COLLECTION_logs).order_by("timestamp", direction=firestore.Query.DESCENDING).limit(100).stream()
        data = [doc.to_dict() for doc in docs]
        if not data: return pd.DataFrame(columns=["Time", "User", "Type", "SKU", "Name", "Quantity", "Note"])
        return pd.DataFrame(data)
    except:
        return pd.DataFrame(columns=["Time", "User", "Type", "SKU", "Name", "Quantity", "Note"])

def save_data_row(row_data):
    """修正版：增加對空日期 (NaT) 的防呆機制"""
    ws = row_data.get("WarrantyStart")
    we = row_data.get("WarrantyEnd")
    
    # --- 🔧 修正：嚴格檢查日期格式 ---
    def clean_date(d):
        if pd.isna(d) or str(d).strip() == "" or str(d).lower() == "nat":
            return ""
        if isinstance(d, (datetime, pd.Timestamp, date)):
            return d.strftime('%Y-%m-%d')
        return str(d)

    ws = clean_date(ws)
    we = clean_date(we)
    # -----------------------------------------------

    try: stock_val = int(row_data.get("Stock", 0))
    except: stock_val = 0
    
    sku = str(row_data.get("SKU", ""))
    if not sku: return

    data_dict = {
        "code": str(row_data.get("Code", "")),
        "categoryName": str(row_data.get("Category", "")),
        "number": str(row_data.get("Number", "")),
        "name": str(row_data.get("Name", "")),
        "imageFile": str(row_data.get("ImageFile", "")),
        "stock": stock_val,
        "location": str(row_data.get("Location", "")),
        "sn": str(row_data.get("SN", "")),
        "warrantyStart": ws,
        "warrantyEnd": we,
        "accessories": str(row_data.get("Accessories", "")), # 🆕 儲存配件
        "updatedAt": firestore.SERVER_TIMESTAMP
    }
    db.collection(COLLECTION_products).document(sku).set(data_dict, merge=True)
    st.cache_data.clear()

def save_log(entry):
    entry["timestamp"] = firestore.SERVER_TIMESTAMP
    db.collection(COLLECTION_logs).add(entry)

def delete_all_products_logic():
    docs = db.collection(COLLECTION_products).stream()
    count = 0
    batch = db.batch()
    for doc in docs:
        batch.delete(doc.reference)
        count += 1
        if count % 400 == 0:
            batch.commit()
            batch = db.batch()
    if count > 0 and count % 400 != 0:
        batch.commit()
    st.cache_data.clear()
    return count

def upload_image_to_firebase(uploaded_file, sku, bucket_override=None):
    """Cloudflare R2 上傳邏輯"""
    if uploaded_file is None: return None
    
    try:
        r2_conf = st.secrets["cloudflare"]
        endpoint = r2_conf["endpoint"]
        access_key = r2_conf["access_key"]
        secret_key = r2_conf["secret_key"]
        bucket_name = r2_conf["bucket_name"]
        public_domain = r2_conf["public_domain"]
        
        image = Image.open(uploaded_file)
        if image.mode in ("RGBA", "P"): image = image.convert("RGB")
        max_width = 800
        if image.width > max_width:
            ratio = max_width / float(image.width)
            new_height = int(float(image.height) * ratio)
            image = image.resize((max_width, new_height), Image.Resampling.LANCZOS)
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format='JPEG', quality=80)
        img_byte_arr.seek(0)

        s3_client = boto3.client(
            's3',
            endpoint_url=endpoint,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key
        )
        safe_sku = "".join([c for c in sku if c.isalnum() or c in ('-','_')])
        file_name = f"images/{safe_sku}-{int(time.time())}.jpg"
        
        s3_client.upload_fileobj(
            img_byte_arr,
            bucket_name,
            file_name,
            ExtraArgs={'ContentType': 'image/jpeg'}
        )
        return f"{public_domain}/{file_name}"
        
    except Exception as e:
        try:
            target_bucket = bucket_override if bucket_override else bucket
            safe_sku = "".join([c for c in sku if c.isalnum() or c in ('-','_')])
            blob_name = f"images/{safe_sku}-{int(time.time())}.jpg"
            blob = target_bucket.blob(blob_name)
            blob.upload_from_file(uploaded_file, content_type=uploaded_file.type)
            blob.make_public()
            return blob.public_url
        except Exception as fb_e:
            st.error(f"上傳失敗: {e} | {fb_e}")
            return None

def check_warranty_status(warranty_end):
    if pd.isna(warranty_end): return None, None
    try:
        end_date = pd.to_datetime(warranty_end)
        today = pd.Timestamp.now()
        days_left = (end_date - today).days
        if days_left < 0: return "已過期", days_left
        elif days_left <= 30: return "即將到期", days_left
        else: return "正常", days_left
    except: return None, None

def get_stock_alert_level(stock):
    if stock == 0: return "無庫存"
    elif stock <= 3: return "極低"
    elif stock <= 5: return "偏低"
    else: return "正常"

def get_warranty_alerts(df):
    alerts = []
    for idx, row in df.iterrows():
        if pd.notna(row['WarrantyEnd']):
            status, days = check_warranty_status(row['WarrantyEnd'])
            if status in ["已過期", "即將到期"]:
                alerts.append({
                    'SKU': row['SKU'],
                    'Name': row['Name'],
                    'Category': row['Category'],
                    'Location': row['Location'],
                    'WarrantyEnd': row['WarrantyEnd'],
                    'Status': status,
                    'DaysLeft': days
                })
    return sorted(alerts, key=lambda x: x['DaysLeft'])

# --- 5. 主程式介面 ---

def main():
    st.sidebar.markdown("""
    <div class='sidebar-brand'>
        <span>📦</span> WebInventory
    </div>
    """, unsafe_allow_html=True)
    
    df = load_data()
    warranty_alerts = get_warranty_alerts(df)
    
    if warranty_alerts:
        with st.sidebar.expander(f"⚠️ 保固提醒 ({len(warranty_alerts)})", expanded=True):
            for alert in warranty_alerts[:5]:
                days = alert['DaysLeft']
                color = "#DC2626" if days < 0 else "#D97706"
                day_text = f"過期 {abs(days)} 天" if days < 0 else f"剩 {days} 天"
                st.markdown(f"""
                <div style='padding:8px 0; border-bottom:1px solid #F3F4F6;'>
                    <div style='font-size:0.85rem; font-weight:600; color:{color};'>{alert['Name']}</div>
                    <div style='font-size:0.75rem; color:#6B7280;'>{alert['SKU']} · {day_text}</div>
                </div>
                """, unsafe_allow_html=True)

    menu_options = [
        "總覽與查詢", 
        "入庫作業", 
        "出庫作業", 
        "資料維護",
        "異動紀錄",
        "保固管理"
    ]
    
    page = st.sidebar.radio("功能選單", menu_options, label_visibility="collapsed")

    if page == "總覽與查詢": page_search()
    elif page == "入庫作業": page_operation("入庫")
    elif page == "出庫作業": page_operation("出庫")
    elif page == "資料維護": page_maintenance()
    elif page == "異動紀錄": page_reports()
    elif page == "保固管理": page_warranty_management()

def render_saas_card(row):
    """渲染專業 SaaS 風格卡片"""
    img_url = row.get('ImageFile', '')
    has_img = img_url and str(img_url).startswith("http")
    
    if has_img:
        img_html = f'<img src="{img_url}" class="saas-thumb">'
    else:
        img_html = '<div class="saas-thumb-placeholder">📦</div>'
    
    try: stock = int(row['Stock'])
    except: stock = 0
    
    status_html = ""
    if stock == 0:
        status_html += '<span class="status-badge badge-danger">缺貨</span>'
    elif stock <= 5:
        status_html += '<span class="status-badge badge-warning">低庫存</span>'
        
    warranty_status, _ = check_warranty_status(row.get('WarrantyEnd'))
    if warranty_status == "已過期":
        status_html += ' <span class="status-badge badge-danger">過保</span>'
    
    if not status_html:
        status_html = '<span class="status-badge badge-success">正常</span>'

    # 顯示部分配件資訊 (若有)
    acc = row.get('Accessories', '')
    acc_html = ""
    if acc:
        acc_short = (acc[:15] + '...') if len(acc) > 15 else acc
        acc_html = f'<div class="meta-row" style="color:#6B7280; font-size:0.8rem; margin-top:4px;"><span>🔩</span> {acc_short}</div>'

    html = f"""<div class="saas-card">
{img_html}
<div class="saas-content">
<div class="col-main">
    <div class="item-title">{row['Name']}</div>
    <div class="item-sku">{row['SKU']}</div>
</div>
<div class="col-meta">
    <div class="meta-row"><span>📁</span> {row['Category']}</div>
    <div class="meta-row"><span>📍</span> {row['Location'] if row['Location'] else '-'}</div>
    {acc_html}
</div>
<div class="col-stock">
    <div class="stock-number">{stock}</div>
    <div style="margin-top:4px;">{status_html}</div>
</div>
</div>
</div>"""
    st.markdown(html, unsafe_allow_html=True)

def page_search():
    st.title("總覽 Overview")
    df = load_data()
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("總品項", len(df))
    c2.metric("低庫存", len(df[df['Stock'] <= 5]))
    c3.metric("無庫存", len(df[df['Stock'] == 0]))
    warranty_alerts = get_warranty_alerts(df)
    c4.metric("保固注意", len(warranty_alerts))
    
    st.markdown("---")
    
    with st.expander("🔍 篩選與搜尋", expanded=False):
        fc1, fc2, fc3 = st.columns(3)
        filter_category = fc1.multiselect("分類", options=df['Category'].unique().tolist())
        filter_location = fc2.multiselect("地點", options=df['Location'].unique().tolist())
        filter_stock = fc3.selectbox("庫存狀態", ["全部", "正常", "低庫存", "無庫存"])
    
    search_term = st.text_input("搜尋", placeholder="輸入名稱、SKU 或配件關鍵字...")
    
    result = df.copy()
    if filter_category: result = result[result['Category'].isin(filter_category)]
    if filter_location: result = result[result['Location'].isin(filter_location)]
    if filter_stock == "低庫存": result = result[result['Stock'] <= 5]
    elif filter_stock == "無庫存": result = result[result['Stock'] == 0]
    
    if search_term:
        # 搜尋範圍也加入配件欄位
        mask = result.astype(str).apply(lambda x: x.str.contains(search_term, case=False, na=False)).any(axis=1)
        result = result[mask]
    
    st.caption(f"共 {len(result)} 筆項目")
    
    for index, row in result.iterrows():
        render_saas_card(row)

def page_warranty_management():
    st.title("保固管理")
    df = load_data()
    alerts = get_warranty_alerts(df)
    
    if not alerts:
        st.success("目前沒有保固到期的設備")
        return

    st.dataframe(pd.DataFrame(alerts), use_container_width=True)

def page_operation(op_type):
    st.title(f"{op_type}作業")
    c1, c2 = st.columns([1, 3])
    qty = c1.number_input("數量", min_value=1, value=1)
    
    if "scan_input" not in st.session_state: st.session_state.scan_input = ""
    def on_scan():
        if st.session_state.scan_box:
            process_stock(st.session_state.scan_box, qty, op_type)
            st.session_state.scan_box = ""
    st.text_input("掃描或輸入 SKU", key="scan_box", on_change=on_scan)

def process_stock(sku, qty, op_type):
    doc_ref = db.collection(COLLECTION_products).document(sku)
    doc = doc_ref.get()
    
    if doc.exists:
        data = doc.to_dict()
        current = data.get('stock', 0)
        new_stock = current + qty if op_type == "入庫" else current - qty
        
        if new_stock < 0:
            st.error(f"❌ 庫存不足!目前: {current}")
            return
        
        doc_ref.update({'stock': new_stock, 'updatedAt': firestore.SERVER_TIMESTAMP})
        save_log({
            "Time": get_taiwan_time(),
            "User": "Admin",
            "Type": op_type,
            "SKU": sku,
            "Name": data.get('name', ''),
            "Quantity": qty,
            "Note": "Manual Ops"
        })
        st.cache_data.clear()
        st.toast(f"✅ {op_type}成功: {sku}")
    else:
        st.error(f"❌ SKU 不存在: {sku}")

def page_maintenance():
    st.title("資料維護")
    tabs = st.tabs(["新增項目", "編輯表格 (可刪除)", "更換圖片", "匯入 CSV", "匯入圖片", "系統重置"])
    
    with tabs[0]:
        with st.form("add_form"):
            c1, c2 = st.columns(2)
            code = c1.text_input("Code")
            cat = c2.text_input("Category")
            c3, c4 = st.columns(2)
            num = c3.text_input("Number")
            name = c4.text_input("Name")
            c5, c6 = st.columns(2)
            sn = c5.text_input("S/N")
            
            # 🆕 1. 地點改為下拉選單
            loc_options = ["北", "中", "南", "醫院"]
            selected_loc = c6.selectbox("地點", loc_options)
            
            # 🆕 2. 保固改為合約保固日
            st.markdown("#### 合約保固日")
            w1, w2 = st.columns(2)
            ws = w1.date_input("開始日期", value=None)
            we = w2.date_input("結束日期", value=None)
            
            # 🆕 3. 新增配件欄位
            st.markdown("#### 儀器箱配件")
            accessories = st.text_area("配件類型及數量", placeholder="例如: 電源線x1, 傳輸線x2...", height=68)
            
            stock = st.number_input("Stock", 0, value=1)
            
            # 醫院名稱處理
            hosp_input = ""
            if selected_loc == "醫院":
                hosp_input = st.text_input("請輸入醫院名稱")

            if st.form_submit_button("新增"):
                final_loc = f"醫院-{hosp_input}" if selected_loc == "醫院" and hosp_input else selected_loc
                sku = f"{code}-{cat}-{num}"
                save_data_row({
                    "SKU":sku, "Code":code, "Category":cat, "Number":num, 
                    "Name":name, "SN":sn, "Location":final_loc, "Stock":stock,
                    "WarrantyStart": ws, "WarrantyEnd": we,
                    "Accessories": accessories
                })
                st.success(f"已新增: {sku}")

    with tabs[1]:
        st.info("💡 提示：選取列後按 Delete 鍵可標記刪除，最後按按鈕同步。")
        df = load_data()
        original_skus = set(df["SKU"].astype(str).tolist()) if not df.empty else set()

        col_config = {
            "SKU": st.column_config.TextColumn("SKU", disabled=True),
            "WarrantyStart": st.column_config.DateColumn("合約保固起"),
            "WarrantyEnd": st.column_config.DateColumn("合約保固迄"),
            "Accessories": st.column_config.TextColumn("儀器箱配件", width="large"),
            "ImageFile": st.column_config.ImageColumn("圖片"),
        }
        
        edited = st.data_editor(
            df, 
            num_rows="dynamic", 
            use_container_width=True, 
            key="data_editor_main", 
            column_config=col_config
        )
        
        if st.button("儲存變更 (包含刪除)", type="primary"):
            with st.spinner("同步中..."):
                current_skus = set(edited["SKU"].astype(str).tolist()) if not edited.empty else set()
                deleted_skus = original_skus - current_skus
                
                del_count = 0
                for del_sku in deleted_skus:
                    if del_sku and del_sku != "nan":
                        db.collection(COLLECTION_products).document(del_sku).delete()
                        del_count += 1
                
                upd_count = 0
                for i, row in edited.iterrows():
                    if row['SKU']: 
                        save_data_row(row)
                        upd_count += 1
                        
            st.success(f"✅ 完成！更新 {upd_count} 筆，刪除 {del_count} 筆。")
            time.sleep(1)
            st.cache_data.clear()
            st.rerun()

    with tabs[2]:
        df_cur = load_data()
        if not df_cur.empty:
            sel = st.selectbox("選擇商品", df_cur['SKU'].unique())
            f = st.file_uploader("上傳新圖片", type=["jpg","png"])
            if f and st.button("更新圖片"):
                url = upload_image_to_firebase(f, sel)
                if url:
                    db.collection(COLLECTION_products).document(sel).update({"imageFile": url})
                    st.success("圖片已更新")

    with tabs[3]:
        up_csv = st.file_uploader("CSV", type=["csv"])
        if up_csv:
            df_im = pd.read_csv(up_csv)
            if st.button("匯入 CSV"):
                for i, r in df_im.iterrows():
                    save_data_row(r)
                st.success("匯入完成")

    with tabs[4]:
        st.write("批次圖片上傳 (檔名需為 SKU)")
        imgs = st.file_uploader("選擇圖片", accept_multiple_files=True)
        if imgs and st.button("上傳"):
            bar = st.progress(0)
            for i, f in enumerate(imgs):
                sku = f.name.rsplit('.', 1)[0]
                upload_image_to_firebase(f, sku)
                bar.progress((i+1)/len(imgs))
            st.success("完成")

    with tabs[5]:
        if st.button("清空資料庫"):
            delete_all_products_logic()
            st.rerun()

def page_reports():
    st.title("異動紀錄")
    st.dataframe(load_log(), use_container_width=True)

if __name__ == "__main__":
    main()
