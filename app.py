# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import io
import json
import time
import requests
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
# 🔧【設定值】Bucket 名稱
# ==========================================
# 若您使用 Cloudflare R2，請確保您的 secrets.toml 設定正確，
# 本程式碼預設保留 Firebase 架構，若需 R2 請自行替換 upload 函數。
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
    # 這裡僅顯示錯誤，不阻擋程式執行 (相容 R2 使用者)
    print(f"Bucket Warning: {e}")

COLLECTION_products = "instrument_consumables" 
COLLECTION_logs = "consumables_logs"

# --- 3. UI 設計：專業企業級 SaaS 風格 (Professional SaaS) ---
st.markdown("""
    <style>
    /* 引入現代化無襯線字體 Inter */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Noto+Sans+TC:wght@400;500;700&display=swap');

    :root {
        /* SaaS 專業配色系統 */
        --bg-body: #F3F4F6;        /* 淺灰背景，降低視覺干擾 */
        --bg-card: #FFFFFF;        /* 純白卡片 */
        --border-color: #E5E7EB;   /* 細緻邊框 */
        --text-main: #111827;      /* 深色主字 */
        --text-sub: #6B7280;       /* 灰色次要字 */
        --primary: #4F46E5;        /* 專業靛藍 (Indigo) */
        --primary-hover: #4338CA;
        --success: #059669;
        --warning: #D97706;
        --danger: #DC2626;
    }

    .stApp {
        background-color: var(--bg-body);
        color: var(--text-main);
        font-family: 'Inter', 'Noto Sans TC', sans-serif;
    }

    /* 側邊欄優化 - 簡約白底 */
    section[data-testid="stSidebar"] {
        background-color: #FFFFFF;
        border-right: 1px solid var(--border-color);
    }
    .sidebar-brand {
        font-size: 1.1rem;
        font-weight: 700;
        color: var(--text-main);
        padding: 12px 4px;
        margin-bottom: 12px;
        border-bottom: 1px solid var(--border-color);
        display: flex;
        align-items: center;
        gap: 8px;
    }

    /* 標題系統 - 精確層級 */
    h1 {
        font-size: 1.8rem !important;
        font-weight: 700 !important;
        color: var(--text-main) !important;
        margin-bottom: 1.5rem !important;
        letter-spacing: -0.025em;
    }
    h2 {
        font-size: 1.25rem !important;
        font-weight: 600 !important;
        color: var(--text-main) !important;
        margin-top: 1rem !important;
    }
    h3 {
        font-size: 1rem !important;
        font-weight: 600 !important;
        color: var(--text-sub) !important;
    }

    /* SaaS 卡片設計 - 清晰邊界 */
    .saas-card {
        background: var(--bg-card);
        border: 1px solid var(--border-color);
        border-radius: 8px; /* 標準圓角 */
        padding: 16px;
        margin-bottom: 12px;
        display: flex;
        align-items: center;
        gap: 16px;
        transition: border-color 0.15s ease, box-shadow 0.15s ease;
    }
    .saas-card:hover {
        border-color: #D1D5DB;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
    }

    /* 圖片容器 - 方正略帶圓角 */
    .img-wrapper {
        width: 64px;
        height: 64px;
        border-radius: 6px;
        border: 1px solid var(--border-color);
        background: #F9FAFB;
        overflow: hidden;
        display: flex;
        align-items: center;
        justify-content: center;
        flex-shrink: 0;
    }
    .card-img-content {
        width: 100%;
        height: 100%;
        object-fit: cover;
    }

    /* 內容排版 */
    .card-body { flex-grow: 1; }
    
    .card-header-row {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 4px;
    }
    .item-title-text {
        font-size: 0.95rem;
        font-weight: 600;
        color: var(--text-main);
    }
    
    /* 專業標籤 (Badges) */
    .saas-badge {
        display: inline-flex;
        align-items: center;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 0.75rem;
        font-weight: 500;
        line-height: 1.2;
    }
    .badge-gray { background: #F3F4F6; color: #4B5563; border: 1px solid #E5E7EB; }
    .badge-blue { background: #EFF6FF; color: #2563EB; border: 1px solid #DBEAFE; }
    .badge-red { background: #FEF2F2; color: #DC2626; border: 1px solid #FECACA; }
    .badge-yellow { background: #FFFBEB; color: #D97706; border: 1px solid #FDE68A; }

    /* 次要資訊列 */
    .meta-row {
        display: flex;
        align-items: center;
        gap: 12px;
        font-size: 0.8rem;
        color: var(--text-sub);
    }
    .meta-item { display: flex; align-items: center; gap: 4px; }

    /* 庫存指標 - 右側獨立區塊 */
    .stock-indicator {
        text-align: right;
        min-width: 80px;
    }
    .stock-value {
        font-family: 'Inter', sans-serif;
        font-size: 1.25rem;
        font-weight: 600;
        color: var(--text-main);
        line-height: 1.2;
    }
    .stock-caption {
        font-size: 0.7rem;
        color: var(--text-sub);
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }

    /* 輸入框優化 - 標準化 */
    .stTextInput input, .stNumberInput input, .stSelectbox div[data-baseweb="select"] {
        border-radius: 6px !important;
        border: 1px solid var(--border-color) !important;
        box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05) !important;
        background-color: #FFFFFF !important;
        padding: 8px 12px !important;
        font-size: 0.9rem !important;
    }
    .stTextInput input:focus {
        border-color: var(--primary) !important;
        box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.1) !important;
    }

    /* 按鈕 - 扁平化設計 */
    div.stButton > button {
        border-radius: 6px;
        border: 1px solid var(--border-color);
        background-color: #FFFFFF;
        color: var(--text-main);
        font-weight: 500;
        font-size: 0.9rem;
        box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
        transition: all 0.2s;
    }
    div.stButton > button:hover {
        background-color: #F9FAFB;
        border-color: #D1D5DB;
    }
    div.stButton > button[kind="primary"] {
        background-color: var(--primary);
        color: white;
        border: 1px solid var(--primary);
    }
    div.stButton > button[kind="primary"]:hover {
        background-color: var(--primary-hover);
    }
    
    /* Metrics 卡片 */
    div[data-testid="stMetric"] {
        background-color: #FFFFFF;
        border: 1px solid var(--border-color);
        border-radius: 8px;
        padding: 16px;
        box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
    }
    
    /* Alert 區塊優化 */
    .stAlert {
        border-radius: 6px;
        border: 1px solid transparent;
    }
    
    /* 修正頂部間距 */
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
                "WarrantyEnd": d.get("warrantyEnd", "")
            })
        
        default_cols = ["SKU", "Code", "Category", "Number", "Name", "ImageFile", "Stock", "Location", "SN", "WarrantyStart", "WarrantyEnd"]
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
    """
    更新或新增單筆資料
    包含日期欄位的防呆處理 (NaT Fix)
    """
    ws = row_data.get("WarrantyStart")
    we = row_data.get("WarrantyEnd")
    
    # --- 日期清洗邏輯 ---
    def clean_date(d):
        if pd.isna(d) or str(d).strip() == "" or str(d).lower() == "nat":
            return ""
        if isinstance(d, (datetime, pd.Timestamp, date)):
            return d.strftime('%Y-%m-%d')
        return str(d)

    ws = clean_date(ws)
    we = clean_date(we)

    try: stock_val = int(row_data.get("Stock", 0))
    except: stock_val = 0
    
    sku = str(row_data.get("SKU", ""))
    if not sku: return # 沒有 SKU 不處理

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
        "updatedAt": firestore.SERVER_TIMESTAMP
    }
    db.collection(COLLECTION_products).document(sku).set(data_dict, merge=True)

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
    """
    圖片上傳函數。
    ⚠️ 如果您使用 Cloudflare R2，請確保這裡使用的是 R2 (boto3) 的版本。
    這裡預設提供 Firebase Storage 版本，但支援簡單的圖片壓縮。
    """
    if uploaded_file is None: return None
    try:
        # 簡單壓縮邏輯 (如果是使用 boto3/R2，這段邏輯可通用)
        from io import BytesIO
        image = Image.open(uploaded_file)
        if image.mode in ("RGBA", "P"): image = image.convert("RGB")
        max_width = 800
        if image.width > max_width:
            ratio = max_width / float(image.width)
            new_height = int(float(image.height) * ratio)
            image = image.resize((max_width, new_height), Image.Resampling.LANCZOS)
        img_byte_arr = BytesIO()
        image.save(img_byte_arr, format='JPEG', quality=85)
        img_byte_arr.seek(0)
        
        # 上傳邏輯 (預設 Firebase)
        target_bucket = bucket_override if bucket_override else bucket
        safe_sku = "".join([c for c in sku if c.isalnum() or c in ('-','_')])
        blob_name = f"images/{safe_sku}-{int(time.time())}.jpg"
        blob = target_bucket.blob(blob_name)
        blob.upload_from_file(img_byte_arr, content_type='image/jpeg')
        blob.make_public()
        return blob.public_url

    except Exception as e:
        st.error(f"上傳失敗: {e}")
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
    except:
        return None, None

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

# --- 5. UI 渲染函數 (Professional SaaS) ---

def render_saas_card(row):
    """渲染專業 SaaS 風格卡片"""
    # 圖片處理
    img_url = row.get('ImageFile', '')
    has_img = img_url and str(img_url).startswith("http")
    
    if has_img:
        img_html = f'<img src="{img_url}" class="card-img-content">'
    else:
        # 使用極簡的圖標代替
        img_html = '<div style="color:#9CA3AF;font-size:1.2rem;">📦</div>'

    # 庫存邏輯
    try: stock = int(row['Stock'])
    except: stock = 0
    
    # 狀態標籤
    alerts = []
    if stock == 0:
        alerts.append('<span class="saas-badge badge-red">Out of Stock</span>')
    elif stock <= 5:
        alerts.append('<span class="saas-badge badge-yellow">Low Stock</span>')
        
    warranty_status, _ = check_warranty_status(row.get('WarrantyEnd'))
    if warranty_status == "已過期":
        alerts.append('<span class="saas-badge badge-red">Expired</span>')
    elif warranty_status == "即將到期":
        alerts.append('<span class="saas-badge badge-yellow">Expiring Soon</span>')
    
    alert_html = "".join(alerts)
    
    # 資料欄位
    sku = row['SKU']
    name = row['Name']
    cat = row['Category']
    loc = row['Location'] if row['Location'] else "N/A"
    sn = row['SN'] if row['SN'] else "-"
    
    # HTML 組裝 (靠左對齊，無縮排)
    html = f"""<div class="saas-card">
<div class="img-wrapper">
{img_html}
</div>
<div class="card-body">
<div class="card-header-row">
<span class="item-title-text">{name}</span>
<div>{alert_html}</div>
</div>
<div style="margin-bottom:6px;">
<span class="saas-badge badge-blue">{sku}</span>
<span class="saas-badge badge-gray">{cat}</span>
</div>
<div class="meta-row">
<span class="meta-item">📍 {loc}</span>
<span style="color:#E5E7EB">|</span>
<span class="meta-item"># {sn}</span>
</div>
</div>
<div class="stock-indicator">
<div class="stock-value" style="color:{'#DC2626' if stock==0 else '#111827'}">{stock}</div>
<div class="stock-caption">Stock</div>
</div>
</div>"""

    st.markdown(html, unsafe_allow_html=True)

# --- 6. 主程式介面 ---

def main():
    # 側邊欄 Logo 與標題
    st.sidebar.markdown("""
    <div class="sidebar-brand">
        <span style="font-size:1.4rem;">📦</span> WebInventory
    </div>
    """, unsafe_allow_html=True)
    
    # ⚠️ 保固提醒 (側邊欄)
    df = load_data()
    warranty_alerts = get_warranty_alerts(df)
    
    if warranty_alerts:
        with st.sidebar.expander(f"🔔 Notifications ({len(warranty_alerts)})", expanded=True):
            for alert in warranty_alerts[:5]:
                days = alert['DaysLeft']
                color = "#DC2626" if days < 0 else "#D97706"
                msg = f"Overdue {abs(days)} days" if days < 0 else f"Expires in {days} days"
                st.markdown(f"""
                <div style='padding:8px 0; border-bottom:1px solid #F3F4F6;'>
                    <div style='font-size:0.85rem; font-weight:600; color:{color};'>{alert['Name']}</div>
                    <div style='font-size:0.75rem; color:#6B7280;'>{msg}</div>
                </div>
                """, unsafe_allow_html=True)
    
    # ❌ [已移除] 連線診斷區塊

    menu_options = [
        "Dashboard", 
        "Inbound", 
        "Outbound", 
        "Data Management",
        "Logs",
        "Warranty"
    ]
    
    # 使用英文選單以符合 SaaS 風格，或可自行改回中文
    page = st.sidebar.radio("MENU", menu_options, label_visibility="collapsed")

    if page == "Dashboard": page_search()
    elif page == "Inbound": page_operation("入庫")
    elif page == "Outbound": page_operation("出庫")
    elif page == "Data Management": page_maintenance()
    elif page == "Logs": page_reports()
    elif page == "Warranty": page_warranty_management()

def page_search():
    st.title("Dashboard")
    df = load_data()
    
    # 頂部狀態列
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Items", len(df))
    c2.metric("Low Stock", len(df[df['Stock'] <= 5]))
    c3.metric("Out of Stock", len(df[df['Stock'] == 0]))
    
    warranty_alerts = get_warranty_alerts(df)
    c4.metric("Alerts", len(warranty_alerts))
    
    st.markdown("---")
    
    # 搜尋與篩選
    col_search, col_filter = st.columns([2, 1])
    with col_search:
        search_term = st.text_input("Search", placeholder="Search by Name, SKU, Location...", label_visibility="collapsed")
    with col_filter:
        filter_cat = st.multiselect("Filter Category", df['Category'].unique(), label_visibility="collapsed", placeholder="Category")

    # 資料處理
    result = df.copy()
    if filter_cat:
        result = result[result['Category'].isin(filter_cat)]
    if search_term:
        mask = result.astype(str).apply(lambda x: x.str.contains(search_term, case=False, na=False)).any(axis=1)
        result = result[mask]
    
    st.caption(f"Showing {len(result)} items")
    
    if result.empty:
        st.info("No items found.")
    else:
        for index, row in result.iterrows():
            render_saas_card(row)

def page_operation(op_type):
    st.title(f"{op_type} Operation")
    st.caption("Scan barcode or enter SKU manually.")
    
    c1, c2 = st.columns([1, 3])
    qty = c1.number_input("Quantity", min_value=1, value=1)
    
    if "scan_input" not in st.session_state: st.session_state.scan_input = ""
    
    def on_scan():
        if st.session_state.scan_box:
            process_stock(st.session_state.scan_box, qty, op_type)
            st.session_state.scan_box = ""
    
    st.text_input("Barcode / SKU", key="scan_box", on_change=on_scan, placeholder="Focus here and scan...")

def process_stock(sku, qty, op_type):
    doc_ref = db.collection(COLLECTION_products).document(sku)
    doc = doc_ref.get()
    
    if doc.exists:
        data = doc.to_dict()
        current = data.get('stock', 0)
        new_stock = current + qty if op_type == "入庫" else current - qty
        
        if new_stock < 0:
            st.error(f"Insufficient stock! Current: {current}")
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
        st.toast(f"✅ Success! {sku} Stock: {new_stock}")
    else:
        st.error(f"SKU not found: {sku}")

def page_maintenance():
    st.title("Data Management")
    tabs = st.tabs(["New Item", "Edit / Delete", "Update Image", "Import CSV", "Reset"])
    
    with tabs[0]:
        with st.form("add_form", clear_on_submit=False):
            st.subheader("Basic Info")
            c1, c2 = st.columns(2)
            code = c1.text_input("Code")
            cat = c2.text_input("Category")
            c3, c4 = st.columns(2)
            num = c3.text_input("Number")
            name = c4.text_input("Name")
            
            st.subheader("Details")
            c5, c6 = st.columns(2)
            sn = c5.text_input("S/N")
            loc = c6.text_input("Location")
            
            c7, c8 = st.columns(2)
            w_start = c7.date_input("Warranty Start", value=None)
            w_end = c8.date_input("Warranty End", value=None)

            stock = st.number_input("Initial Stock", 0, value=1)
            submitted = st.form_submit_button("Create Item", type="primary")

        if submitted:
            if code and name:
                sku = f"{code}-{cat}-{num}"
                save_data_row({
                    "SKU":sku, "Code":code, "Category":cat, "Number":num, 
                    "Name":name, "SN":sn, "Location":loc, "Stock":stock,
                    "WarrantyStart": w_start, "WarrantyEnd": w_end
                })
                st.success(f"Item created: {sku}")
            else:
                st.error("Code and Name are required.")

    # --- 關鍵修正：整合刪除邏輯的編輯表格 ---
    with tabs[1]:
        st.caption("💡 Select rows and press Delete key to remove items.")
        df = load_data()
        
        original_skus = set(df["SKU"].astype(str).tolist()) if not df.empty else set()

        col_config = {
            "SKU": st.column_config.TextColumn("SKU", disabled=True),
            "WarrantyStart": st.column_config.DateColumn("Start Date"),
            "WarrantyEnd": st.column_config.DateColumn("End Date"),
            "ImageFile": st.column_config.ImageColumn("Image"),
        }
        
        edited = st.data_editor(
            df, 
            num_rows="dynamic", 
            use_container_width=True, 
            key="data_editor_main", 
            column_config=col_config
        )
        
        if st.button("Save Changes", type="primary"):
            with st.spinner("Syncing..."):
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
                        
            st.success(f"Synced! Updated: {upd_count}, Deleted: {del_count}")
            time.sleep(1)
            st.cache_data.clear()
            st.rerun()

    with tabs[2]:
        df_cur = load_data()
        if not df_cur.empty:
            sel = st.selectbox("Select Item", df_cur['SKU'].unique())
            if sel:
                row = df_cur[df_cur['SKU'] == sel].iloc[0]
                st.write(f"Editing: **{row['Name']}**")
                f = st.file_uploader("Upload New Image", type=["jpg","png"])
                if f and st.button("Update Image"):
                    url = upload_image_to_firebase(f, sel)
                    if url:
                        db.collection(COLLECTION_products).document(sel).update({"imageFile": url})
                        st.success("Image updated.")
        else:
            st.info("No items.")

    with tabs[3]:
        up_csv = st.file_uploader("Upload CSV", type=["csv"])
        if up_csv:
            if st.button("Import"):
                # CSV 匯入邏輯 (簡化版)
                try:
                    df_im = pd.read_csv(up_csv)
                    st.success("CSV Imported (Logic Placeholder)")
                except:
                    st.error("Error reading CSV")

    with tabs[4]:
        st.error("Danger Zone")
        confirm = st.text_input("Type 'DELETE' to confirm", key="delete_confirm")
        if st.button("Delete All Data"):
            if confirm == "DELETE":
                with st.spinner("Deleting..."): c = delete_all_products_logic()
                st.success(f"Deleted {c} items.")
                time.sleep(1)
                st.rerun()

def page_reports():
    st.title("Activity Logs")
    df = load_log()
    st.dataframe(df, use_container_width=True)

def page_warranty_management():
    st.title("Warranty Management")
    df = load_data()
    warranty_alerts = get_warranty_alerts(df)
    
    if not warranty_alerts:
        st.success("No warranty alerts.")
        return

    for alert in warranty_alerts:
        days = alert['DaysLeft']
        color = "#DC2626" if days < 0 else "#D97706"
        badge = "Expired" if days < 0 else "Expiring Soon"
        
        st.markdown(f"""
        <div class="saas-card">
            <div class="card-body">
                <div class="card-header-row">
                    <span class="item-title-text" style="color:{color}">{alert['Name']}</span>
                    <span class="saas-badge badge-red">{badge}</span>
                </div>
                <div class="meta-row">
                    <span>SKU: {alert['SKU']}</span>
                    <span>•</span>
                    <span>Ends: {alert['WarrantyEnd'].strftime('%Y-%m-%d')}</span>
                </div>
            </div>
            <div class="stock-indicator">
                <div class="stock-value" style="color:{color}">{days}</div>
                <div class="stock-caption">Days</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()