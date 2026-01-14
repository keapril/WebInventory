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
# 設定值
# ==========================================
CUSTOM_BUCKET_NAME = "product-system-900c4.firebasestorage.app"

# 品項類型
ITEM_TYPES = ["儀器", "線材"]

# 地點選項
LOCATION_OPTIONS = ["北辦", "中辦", "南辦", "高辦", "醫院"]

# 預設配件清單 (分類)
ACCESSORY_CATEGORIES = {
    "主機類": [
        "ViewMate主機", "Claris主機", "Claris放大器", "EP4主機", 
        "ICE module P9-31C", "RecordConnect-WMC"
    ],
    "螢幕顯示": [
        "觸控螢幕", "螢幕(含支架)", "螢幕spliter", "電腦螢幕圓盤底座"
    ],
    "探頭": [
        "L14-5sp transducer", "P4-1c transducer", "P7-3c transducer", "L8-3 transducer"
    ],
    "線材": [
        "電源線", "電源線(放大器)", "電源線(連接延長線)", "HDMI", 
        "DVI公-DVI公", "DVI公-VGA公", "VGA公-VGA公", 
        "DVI公-VGA母_轉接頭", "DVI公-HDMI母_轉接頭", "DP公-DVI母_轉接頭",
        "HDMI母-DVI公", "HDMI公-HDMI公", "網路線轉粗光纖", 
        "細光纖", "粗光纖", "USB延長線(含轉接頭)", "延長線", 
        "RS232", "Hemo cable血壓線", "BMC香蕉線", "EKG線", "ECG cable"
    ],
    "分接器": [
        "Junction box", "Junction box_C1 module 1", "Junction box 2_C1 module 2",
        "DVI spliter", "HDMI spliter"
    ],
    "其他": [
        "Catheter Interface Module", "ViewFlex™ Xtra ICE Catheter",
        "模擬Sheath", "模擬心臟模型", "晶片", "變壓器", "穩壓器",
        "滑鼠", "鍵盤", "記錄器reference", "刺激器cable"
    ]
}

# --- 2. Firebase 初始化 ---
firebase_app = None
if not firebase_admin._apps:
    try:
        if "firebase" not in st.secrets:
            st.error("系統錯誤：找不到 Firebase 金鑰配置。")
            st.stop()
        
        token_content = st.secrets["firebase"]["text_key"]
        try:
            key_dict = json.loads(token_content, strict=False)
        except json.JSONDecodeError:
            try:
                key_dict = json.loads(token_content.replace('\n', '\\n'), strict=False)
            except:
                st.error("系統錯誤：金鑰解析失敗。")
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

# --- 3. UI 設計：日式清爽文青風格 ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Zen+Kaku+Gothic+New:wght@300;400;500;700&family=Noto+Serif+TC:wght@400;600&display=swap');

    :root {
        /* 莫蘭迪色系 - 柔和低飽和度 */
        --primary: #9EAAB7;       /* 淺灰藍 */
        --accent: #D4B5B0;        /* 豆沙粉 */
        --bg: #F5F3F0;            /* 淺米灰 */
        --card: #FDFCFA;
        --text: #6B6B6B;          /* 柔和灰 */
        --text-light: #A3A3A3;    /* 淡灰 */
        --border: #E5DED8;        /* 淺駝邊框 */
        --hover: #EBE7E3;
        --tag-bg: #C9B8A2;        /* 淺卡其 */
        --font-main: 'Zen Kaku Gothic New', 'Noto Serif TC', sans-serif;
    }

    /* 全局 */
    .stApp {
        background-color: var(--bg);
        color: var(--text);
        font-family: var(--font-main);
    }
    
    /* 側邊欄 */
    section[data-testid="stSidebar"] {
        background-color: #FFFFFF;
        border-right: 1px solid var(--border);
    }
    
    .sidebar-brand {
        font-size: 1.1rem;
        font-weight: 500;
        color: var(--text);
        padding: 1.5rem 0 1rem;
        margin-bottom: 1.5rem;
        letter-spacing: 0.1em;
        border-bottom: 1px solid var(--border);
    }

    h1, h2, h3 {
        font-family: var(--font-main) !important;
        color: var(--text) !important;
        font-weight: 500 !important;
        letter-spacing: 0.05em;
    }
    
    h1 { font-size: 1.5rem !important; }
    h2 { font-size: 1.2rem !important; }
    h3 { font-size: 1rem !important; }

    /* 卡片 - 日式簡約 */
    .item-card {
        background: var(--card);
        border: 1px solid var(--border);
        border-radius: 4px;
        padding: 16px 20px;
        margin-bottom: 8px;
        display: flex;
        align-items: center;
        gap: 20px;
        transition: all 0.2s ease;
    }
    .item-card:hover {
        background: var(--hover);
        border-color: var(--accent);
    }

    .item-thumb {
        width: 56px;
        height: 56px;
        border-radius: 4px;
        background: #F5F6F5;
        border: 1px solid var(--border);
        object-fit: cover;
        flex-shrink: 0;
    }
    .item-thumb-empty {
        width: 56px;
        height: 56px;
        border-radius: 4px;
        background: linear-gradient(135deg, #F8F9F8 0%, #ECEEED 100%);
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 0.8rem;
        color: var(--text-light);
        flex-shrink: 0;
    }

    .item-content {
        flex-grow: 1;
        display: grid;
        grid-template-columns: 2fr 1.5fr 1fr;
        gap: 16px;
        align-items: center;
    }
    
    .item-main { }
    .item-name { 
        font-size: 0.95rem; 
        font-weight: 500; 
        color: var(--text); 
        margin-bottom: 4px;
        letter-spacing: 0.02em;
    }
    .item-sku {
        font-size: 0.75rem;
        color: var(--text-light);
        font-family: monospace;
    }

    .item-meta { 
        font-size: 0.8rem; 
        color: var(--text-light);
        line-height: 1.6;
    }

    .item-stock { 
        text-align: right;
    }
    .stock-num { 
        font-size: 1.3rem; 
        font-weight: 500; 
        color: var(--text);
    }
    
    /* 標籤 - 莫蘭迪配色 */
    .tag {
        display: inline-block;
        font-size: 0.7rem;
        padding: 2px 8px;
        border-radius: 2px;
        margin-top: 4px;
        letter-spacing: 0.05em;
    }
    .tag-normal { background: #E8EBE4; color: #7A8B7F; border: 1px solid #D4DAD0; }
    .tag-warning { background: #F5EDE3; color: #B89968; border: 1px solid #E8DCC8; }
    .tag-danger { background: #F0E3E1; color: #B88B87; border: 1px solid #E3CCC8; }
    .tag-type { background: #EAE8E6; color: #9EAAB7; border: 1px solid #D8D4D0; }
    
    /* 按鈕 - 莫蘭迪配色 */
    div.stButton > button {
        border-radius: 4px;
        font-weight: 400;
        border: 1px solid var(--border);
        background: white;
        color: var(--text);
        padding: 0.5rem 1.2rem;
        letter-spacing: 0.05em;
        transition: all 0.2s ease;
    }
    div.stButton > button:hover {
        border-color: var(--primary);
        background: var(--hover);
    }
    div.stButton > button[kind="primary"] {
        background: #D4B5B0;
        color: white;
        border: none;
    }
    div.stButton > button[kind="primary"]:hover {
        background: #C5A6A1;
    }
    
    /* Form Submit 按鈕 - 莫蘭迪豆沙粉 */
    button[type="submit"] {
        background-color: #D4B5B0 !important;
        color: white !important;
        border: none !important;
    }
    button[type="submit"]:hover {
        background-color: #C5A6A1 !important;
    }
    
    /* 輸入欄位 - 莫蘭迪配色 */
    .stTextInput input, .stNumberInput input, 
    .stSelectbox div[data-baseweb="select"], .stTextArea textarea {
        border-radius: 4px;
        border-color: #E5DED8 !important;
        background-color: #FDFCFA !important;
        font-family: var(--font-main);
    }
    .stTextInput input:focus, .stTextArea textarea:focus {
        border-color: #D4B5B0 !important;
        box-shadow: 0 0 0 1px #D4B5B0 !important;
    }
    
    /* Tabs 標籤樣式 */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: transparent;
    }
    .stTabs [data-baseweb="tab"] {
        font-size: 0.9rem;
        letter-spacing: 0.05em;
        background-color: #EBE7E3;
        color: #6B6B6B;
        border-radius: 6px 6px 0 0;
        padding: 0.5rem 1.2rem;
    }
    .stTabs [aria-selected="true"] {
        background-color: #D4B5B0 !important;
        color: white !important;
    }
    
    /* 分類區塊 */
    .category-section {
        background: #FDFDFB;
        border: 1px solid var(--border);
        border-radius: 4px;
        padding: 12px 16px;
        margin-bottom: 8px;
    }
    .category-title {
        font-size: 0.8rem;
        font-weight: 500;
        color: var(--primary);
        margin-bottom: 10px;
        padding-bottom: 8px;
        border-bottom: 1px solid var(--border);
        letter-spacing: 0.1em;
    }
    
    .block-container { padding-top: 2rem; }
    
    /* 細節調整 */
    .stRadio > div { gap: 1rem; }
    
    /* 配件標籤 */
    .acc-list {
        font-size: 0.75rem;
        color: var(--text-light);
        margin-top: 4px;
    }
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
                "Accessories": d.get("accessories", ""),
                "ItemType": d.get("itemType", "儀器")
            })
        
        default_cols = ["SKU", "Code", "Category", "Number", "Name", "ImageFile", "Stock", "Location", "SN", "WarrantyStart", "WarrantyEnd", "Accessories", "ItemType"]
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
        return pd.DataFrame(columns=["SKU", "Code", "Category", "Number", "Name", "ImageFile", "Stock", "Location", "SN", "WarrantyStart", "WarrantyEnd", "Accessories", "ItemType"])

def load_log():
    try:
        docs = db.collection(COLLECTION_logs).order_by("timestamp", direction=firestore.Query.DESCENDING).limit(100).stream()
        data = [doc.to_dict() for doc in docs]
        if not data: return pd.DataFrame(columns=["Time", "User", "Type", "SKU", "Name", "Quantity", "Note"])
        return pd.DataFrame(data)
    except:
        return pd.DataFrame(columns=["Time", "User", "Type", "SKU", "Name", "Quantity", "Note"])

def save_data_row(row_data):
    ws = row_data.get("WarrantyStart")
    we = row_data.get("WarrantyEnd")
    
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
        "accessories": str(row_data.get("Accessories", "")),
        "itemType": str(row_data.get("ItemType", "儀器")),
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
    """檢查保固狀態（90 天提醒週期）"""
    if pd.isna(warranty_end): return None, None
    try:
        end_date = pd.to_datetime(warranty_end)
        today = pd.Timestamp.now()
        days_left = (end_date - today).days
        if days_left < 0: return "已過期", days_left
        elif days_left <= 90: return "即將到期", days_left  # 改為 90 天（一季）
        else: return "正常", days_left
    except: return None, None

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

def parse_accessories(acc_str):
    if not acc_str or acc_str == "":
        return {}
    try:
        return json.loads(acc_str)
    except:
        return {"備註": acc_str}

def format_accessories_display(acc_str, max_items=3):
    acc_dict = parse_accessories(acc_str)
    if not acc_dict:
        return ""
    
    items = list(acc_dict.items())[:max_items]
    result = ", ".join([f"{k} ×{v}" if isinstance(v, int) else f"{k}" for k, v in items])
    if len(acc_dict) > max_items:
        result += f" 等 {len(acc_dict)} 項"
    return result

# R2 公開網域
R2_PUBLIC_DOMAIN = "https://pub-12069eb186dd414482e689701534d8d5.r2.dev"

# 處理圖片 URL（支援多種格式）
@st.cache_data(ttl=3600)  # 快取 1 小時
def get_displayable_image_url(img_url):
    """
    處理圖片 URL，支援以下格式：
    1. 相對路徑 (images/xxx.jpg) → 加上 R2 public domain
    2. 完整 R2 URL → 直接返回
    3. Firebase Storage URL → 產生簽名 URL
    4. 其他完整 URL → 直接返回
    """
    if not img_url:
        return None
    
    img_url = str(img_url).strip()
    
    # 空字串檢查
    if not img_url or img_url.lower() in ('none', 'nan', ''):
        return None
    
    # 情況 1: 相對路徑（不是以 http 開頭，也不是 data: URI）
    if not img_url.startswith("http") and not img_url.startswith("data:"):
        # 加上 R2 public domain 前綴
        if img_url.startswith("/"):
            img_url = img_url[1:]  # 移除開頭的斜線
        return f"{R2_PUBLIC_DOMAIN}/{img_url}"
    
    # 情況 2: Data URI（base64 編碼的圖片）
    if img_url.startswith("data:"):
        return img_url
    
    # 情況 3: Firebase Storage URL → 產生簽名 URL
    if "storage.googleapis.com" in img_url or "firebasestorage.app" in img_url:
        try:
            import urllib.parse
            parsed = urllib.parse.urlparse(img_url)
            path_parts = parsed.path.split('/', 2)  # ['', 'bucket-name', 'path/to/file']
            if len(path_parts) >= 3:
                blob_path = urllib.parse.unquote(path_parts[2])  # 解碼 URL 編碼的中文
                blob = bucket.blob(blob_path)
                # 產生 1 小時有效的簽名 URL
                signed_url = blob.generate_signed_url(
                    version="v4",
                    expiration=timedelta(hours=1),
                    method="GET"
                )
                return signed_url
        except Exception as e:
            # 如果產生簽名 URL 失敗，返回原始 URL
            pass
    
    # 情況 4: Cloudflare R2 完整 URL 或其他 URL → 直接返回
    return img_url

# --- 5. 主程式介面 ---

def main():
    st.sidebar.markdown("""
    <div class='sidebar-brand'>WebInventory</div>
    """, unsafe_allow_html=True)
    
    df = load_data()
    warranty_alerts = get_warranty_alerts(df)
    
    if warranty_alerts:
        with st.sidebar.expander(f"保固提醒 ({len(warranty_alerts)})", expanded=True):
            for alert in warranty_alerts[:5]:
                days = alert['DaysLeft']
                day_text = f"過期 {abs(days)} 天" if days < 0 else f"剩餘 {days} 天"
                st.markdown(f"""
                <div style='padding:8px 0; border-bottom:1px solid #E8ECEB; font-size:0.8rem;'>
                    <div style='color:#2D3436;'>{alert['Name']}</div>
                    <div style='color:#8B9A9C; font-size:0.75rem;'>{alert['SKU']} · {day_text}</div>
                </div>
                """, unsafe_allow_html=True)

    menu_options = [
        "總覽", 
        "資料維護",
        "異動紀錄",
        "保固管理"
    ]
    
    page = st.sidebar.radio("", menu_options, label_visibility="collapsed")

    if page == "總覽": page_search()
    elif page == "資料維護": page_maintenance()
    elif page == "異動紀錄": page_reports()
    elif page == "保固管理": page_warranty_management()

def render_item_card(row):
    """渲染項目卡片 - 使用 Streamlit 原生元件"""
    raw_img_url = row.get('ImageFile', '')
    img_url = get_displayable_image_url(raw_img_url)
    item_type = row.get('ItemType', '儀器')
    
    try: stock = int(row['Stock'])
    except: stock = 0
    
    # 標籤
    tags = []
    tags.append(f'<span class="tag tag-type">{item_type}</span>')
    if stock == 0:
        tags.append('<span class="tag tag-danger">無庫存</span>')
    elif stock <= 5:
        tags.append('<span class="tag tag-warning">低庫存</span>')
        
    warranty_status, _ = check_warranty_status(row.get('WarrantyEnd'))
    if warranty_status == "已過期":
        tags.append('<span class="tag tag-danger">過保</span>')

    tags_html = " ".join(tags)

    # 配件
    acc_str = row.get('Accessories', '')
    acc_display = format_accessories_display(acc_str)

    # 使用 Streamlit 原生元件佈局
    with st.container():
        col_img, col_info, col_stock = st.columns([1, 4, 1])
        
        with col_img:
            if img_url:
                try:
                    st.image(img_url, width=60)
                except:
                    type_label = "器" if item_type == "儀器" else "線"
                    st.markdown(f'<div class="item-thumb-empty">{type_label}</div>', unsafe_allow_html=True)
            else:
                type_label = "器" if item_type == "儀器" else "線"
                st.markdown(f'<div class="item-thumb-empty">{type_label}</div>', unsafe_allow_html=True)
        
        with col_info:
            st.markdown(f"""
            <div class="item-main">
                <div class="item-name">{row['Name']}</div>
                <div class="item-sku">{row['SKU']}</div>
                <div class="item-meta">{row['Category']} · {row['Location'] if row['Location'] else '-'}</div>
                {'<div class="acc-list">' + acc_display + '</div>' if acc_display else ''}
            </div>
            """, unsafe_allow_html=True)
        
        with col_stock:
            st.markdown(f"""
            <div class="item-stock">
                <div class="stock-num">{stock}</div>
                <div>{tags_html}</div>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown('<hr style="margin: 8px 0; border: none; border-top: 1px solid #E8ECEB;">', unsafe_allow_html=True)

@st.dialog("產品詳細資訊", width="large")
def show_product_detail(row):
    """顯示產品詳細資訊對話框"""
    # 使用緊湊佈局減少留白
    st.markdown("""
    <style>
    div[data-testid="stDialog"] > div {
        padding: 1rem 1.5rem !important;
    }
    div[data-testid="stDialog"] h2 {
        font-size: 1.4rem !important;
        margin-bottom: 0.3rem !important;
        color: #6B6B6B !important;
    }
    div[data-testid="stDialog"] p {
        font-size: 0.9rem !important;
        line-height: 1.4 !important;
        margin-bottom: 0.5rem !important;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # 圖片顯示（限制寬度以適應手機）
    img_url = get_displayable_image_url(row.get('ImageFile', ''))
    if img_url:
        st.image(img_url, width=300)
    else:
        st.caption("📷 無產品圖片")
    
    # 基本資訊
    st.markdown(f"## {row['Name']}")
    st.caption(f"SKU: `{row['SKU']}`")
    st.markdown("")
    
    # 詳細資訊（分欄，緊湊）
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"**類型** {row.get('ItemType', 'N/A')}")
        st.markdown(f"**分類** {row.get('Category', 'N/A')}")
        st.markdown(f"**地點** {row.get('Location', 'N/A')}")
        if row.get('SN'):
            st.markdown(f"**序號** {row['SN']}")
    
    with col2:
        st.markdown(f"**庫存** {row.get('Stock', 0)}")
        if row.get('WarrantyStart'):
            st.markdown(f"**保固起** {row['WarrantyStart']}")
        if row.get('WarrantyEnd'):
            warranty_status, days_left = check_warranty_status(row['WarrantyEnd'])
            if warranty_status:
                status_color = "🟢" if warranty_status == "正常" else "🟡" if warranty_status == "即將到期" else "🔴"
                st.markdown(f"**保固迄** {row['WarrantyEnd']} {status_color}")
    
    # 配件資訊
    if row.get('Accessories'):
        st.markdown("")
        st.markdown("**📦 配件**")
        try:
            acc_dict = json.loads(row['Accessories'])
            acc_list = [f"{name} x{qty}" for name, qty in acc_dict.items()]
            st.caption(" · ".join(acc_list))
        except:
            st.caption(row['Accessories'])

def render_product_card_with_detail(row):
    """渲染產品卡片（帶詳情按鈕）"""
    raw_img_url = row.get('ImageFile', '')
    img_url = get_displayable_image_url(raw_img_url)
    item_type = row.get('ItemType', '儀器')
    
    try: stock = int(row['Stock'])
    except: stock = 0
    
    # 標籤
    tags = []
    tags.append(f'<span class="tag tag-type">{item_type}</span>')
    if stock == 0:
        tags.append('<span class="tag tag-danger">無庫存</span>')
    elif stock <= 5:
        tags.append('<span class="tag tag-warning">低庫存</span>')
        
    warranty_status, _ = check_warranty_status(row.get('WarrantyEnd'))
    if warranty_status == "已過期":
        tags.append('<span class="tag tag-danger">過保</span>')

    tags_html = " ".join(tags)

    # 配件
    acc_str = row.get('Accessories', '')
    acc_display = format_accessories_display(acc_str)

    # 使用 Streamlit 原生元件佈局
    with st.container():
        col_img, col_info, col_stock, col_action = st.columns([1, 4, 1, 1])
        
        with col_img:
            if img_url:
                try:
                    st.image(img_url, width=60)
                except:
                    type_label = "器" if item_type == "儀器" else "線"
                    st.markdown(f'<div class="item-thumb-empty">{type_label}</div>', unsafe_allow_html=True)
            else:
                type_label = "器" if item_type == "儀器" else "線"
                st.markdown(f'<div class="item-thumb-empty">{type_label}</div>', unsafe_allow_html=True)
        
        with col_info:
            st.markdown(f"""
            <div class="item-main">
                <div class="item-name">{row['Name']}</div>
                <div class="item-sku">{row['SKU']}</div>
                <div class="item-meta">{row['Category']} · {row['Location'] if row['Location'] else '-'}</div>
                {'<div class="acc-list">' + acc_display + '</div>' if acc_display else ''}
            </div>
            """, unsafe_allow_html=True)
        
        with col_stock:
            st.markdown(f"""
            <div class="item-stock">
                <div class="stock-num">{stock}</div>
                <div>{tags_html}</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col_action:
            if st.button("📋 詳情", key=f"detail_{row['SKU']}", use_container_width=True):
                show_product_detail(row)
        
        st.markdown('<hr style="margin: 8px 0; border: none; border-top: 1px solid #E8ECEB;">', unsafe_allow_html=True)

def page_search():
    """總覽頁面 - 首頁風格（莫蘭迪）"""
    
    # 1. 歡迎區（置中，移除統計）
    st.markdown("""
    <div style="text-align: center; padding: 40px 0 30px 0;">
        <h1 style="font-size: 2.2rem; font-weight: 300; color: #9EAAB7; margin-bottom: 12px;">📦 WebInventory</h1>
        <p style="color: #A3A3A3; font-size: 1rem; letter-spacing: 0.05em;">儀器與線材庫存管理系統</p>
    </div>
    """, unsafe_allow_html=True)
    
    df = load_data()
    
    # 2. 搜尋區（簡化、優雅）
    st.markdown("")
    search_col1, search_col2, search_col3 = st.columns([1, 2, 1])
    
    with search_col1:
        search_mode = st.radio("搜尋模式", ["模糊搜尋", "精確搜尋"], horizontal=True, label_visibility="collapsed")
    
    with search_col2:
        search_term = st.text_input(
            "搜尋", 
            placeholder="🔍 輸入名稱、SKU 或關鍵字...",
            label_visibility="collapsed"
        )
    
    # 3. 篩選條件（摺疊，柔和色調）
    with st.expander("🎛 進階篩選", expanded=False):
        fc1, fc2, fc3, fc4 = st.columns(4)
        
        # 使用固定的標準選項
        filter_type = fc1.multiselect("類型", options=ITEM_TYPES)
        
        # 分類：從實際資料動態生成
        available_categories = sorted([cat for cat in df['Category'].dropna().unique() if cat])
        filter_category = fc2.multiselect("分類", options=available_categories)
        
        # 地點：使用固定的標準地點清單
        filter_location = fc3.multiselect("地點", options=LOCATION_OPTIONS)
        
        # S/N 搜尋
        filter_sn = fc4.text_input("S/N 序號", placeholder="輸入序號...")
    
    # 4. 判斷是否有搜尋條件
    has_search = search_term or filter_type or filter_category or filter_location or filter_sn
    
    if has_search:
        # 套用篩選條件
        result = df.copy()
        
        # 類型篩選
        if filter_type: 
            result = result[result['ItemType'].isin(filter_type)]
        
        # 分類篩選
        if filter_category: 
            result = result[result['Category'].isin(filter_category)]
        
        # 地點篩選（智能匹配）
        if filter_location:
            # 使用模糊匹配找出相似的地點
            def match_location(loc):
                if pd.isna(loc):
                    return False
                loc_str = str(loc)
                for filter_loc in filter_location:
                    # 例如：選「北辦」可以匹配到「北辦」、「醫院-XXX-北辦」等
                    if filter_loc in loc_str:
                        return True
                return False
            
            result = result[result['Location'].apply(match_location)]
        
        # S/N 篩選
        if filter_sn:
            result = result[result['SN'].astype(str).str.contains(filter_sn, case=False, na=False)]
        
        # 關鍵字搜尋
        if search_term:
            if search_mode == "精確搜尋":
                # 精確搜尋：完全匹配
                mask = (
                    (result['Name'].astype(str) == search_term) |
                    (result['SKU'].astype(str) == search_term) |
                    (result['SN'].astype(str) == search_term)
                )
            else:
                # 模糊搜尋：包含關鍵字
                mask = result.astype(str).apply(lambda x: x.str.contains(search_term, case=False, na=False)).any(axis=1)
            
            result = result[mask]
        
        # 顯示搜尋結果
        st.markdown(f"### 搜尋結果（{len(result)} 筆）")
        
        if len(result) == 0:
            st.warning("😕 找不到符合條件的產品")
        else:
            for index, row in result.iterrows():
                render_product_card_with_detail(row)
    else:
        # 無搜尋時顯示提示
        st.info("👆 請輸入關鍵字或使用進階篩選來搜尋產品")

def page_warranty_management():
    st.markdown("### 保固管理")
    df = load_data()
    alerts = get_warranty_alerts(df)
    
    if not alerts:
        st.success("目前沒有保固到期的設備")
        return

    st.dataframe(pd.DataFrame(alerts), use_container_width=True)

def page_operation(op_type):
    st.markdown(f"### {op_type}作業")
    
    col1, col2 = st.columns([1, 3])
    qty = col1.number_input("數量", min_value=1, value=1)
    
    if "scan_input" not in st.session_state: 
        st.session_state.scan_input = ""
    
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
            st.error(f"庫存不足，目前: {current}")
            return
        
        doc_ref.update({'stock': new_stock, 'updatedAt': firestore.SERVER_TIMESTAMP})
        save_log({
            "Time": get_taiwan_time(),
            "User": "Admin",
            "Type": op_type,
            "SKU": sku,
            "Name": data.get('name', ''),
            "Quantity": qty,
            "Note": ""
        })
        st.cache_data.clear()
        st.toast(f"{op_type}成功: {sku}")
    else:
        st.error(f"SKU 不存在: {sku}")

def page_maintenance():
    # 標題樣式優化
    st.markdown("""
    <div style="padding: 1rem 0; border-bottom: 2px solid #D4B5B0; margin-bottom: 1.5rem;">
        <h2 style="font-size: 1.8rem; font-weight: 400; color: #9EAAB7; margin: 0; letter-spacing: 0.05em;">📝 資料維護</h2>
        <p style="font-size: 0.9rem; color: #A3A3A3; margin: 0.3rem 0 0 0;">新增、編輯與管理產品資料</p>
    </div>
    """, unsafe_allow_html=True)
    
    tabs = st.tabs(["➕ 新增", "✏️ 編輯", "🖼 圖片", "📦 批次上傳"])
    
    with tabs[0]:
        st.markdown("#### 品項類型")
        item_type = st.radio(
            "選擇類型",
            ITEM_TYPES,
            horizontal=True,
            label_visibility="collapsed",
            key="add_type"
        )
        st.markdown("---")
        
        if item_type == "儀器":
            # 地點選擇（form 外）
            st.markdown("##### 地點")
            selected_loc = st.selectbox("選擇地點", LOCATION_OPTIONS, key="new_inst_loc")
            
            # 醫院資訊（條件顯示）
            hosp_name = ""
            is_stationed = "否"
            if selected_loc == "醫院":
                hc1, hc2 = st.columns(2)
                hosp_name = hc1.text_input("醫院名稱")
                is_stationed = hc2.radio("是否留院", ["是", "否"], horizontal=True)
            
            st.markdown("---")
            
            with st.form("add_instrument"):
                st.markdown("##### 新增儀器")
                
                c1, c2 = st.columns(2)
                name = c1.text_input("儀器名稱 *")
                sn = c2.text_input("S/N 序號")
                
                c3, c4, c5 = st.columns(3)
                code = c3.text_input("設備類型")
                cat = c4.text_input("分類")
                num = c5.text_input("編碼")
                
                st.markdown("##### 合約保固日")
                w1, w2 = st.columns(2)
                ws = w1.date_input("起始", value=None)
                we = w2.date_input("結束", value=None)
                
                st.markdown("##### 配件")
                st.caption("打勾並輸入數量，數量欄位始終可見")
                acc_data = {}
                
                for cat_name, items in ACCESSORY_CATEGORIES.items():
                    with st.expander(f"{cat_name} ({len(items)})"):
                        for i, acc_name in enumerate(items):
                            acc_col1, acc_col2 = st.columns([3, 1])
                            checked = acc_col1.checkbox(acc_name, key=f"acc_{cat_name}_{i}")
                            qty = acc_col2.number_input("qty", min_value=1, value=1, key=f"qty_{cat_name}_{i}", label_visibility="collapsed")
                            if checked:
                                acc_data[acc_name] = qty
                
                other_acc = st.text_input("其他配件")
                if other_acc:
                    acc_data["其他"] = other_acc
                
                stock = st.number_input("庫存數量", min_value=0, value=1)
                
                st.markdown("##### 產品圖片")
                uploaded_img = st.file_uploader("上傳圖片", type=["jpg","png","jpeg"], key="img_instrument")
                
                if st.form_submit_button("新增", type="primary", use_container_width=True):
                    if not name.strip():
                        st.error("請輸入儀器名稱")
                    else:
                        # 處理地點
                        if selected_loc == "醫院" and hosp_name:
                            stationed_text = "留院" if is_stationed == "是" else "非留院"
                            final_loc = f"醫院-{hosp_name}-{stationed_text}"
                        else:
                            final_loc = selected_loc
                        
                        sku = f"{code}-{cat}-{num}" if all([code, cat, num]) else f"INS-{int(time.time())}"
                        acc_json = json.dumps(acc_data, ensure_ascii=False) if acc_data else ""
                        
                        # 上傳圖片
                        img_url = ""
                        if uploaded_img:
                            img_url = upload_image_to_firebase(uploaded_img, sku)
                            if not img_url:
                                st.warning("圖片上傳失敗，但產品已建檔")
                        
                        save_data_row({
                            "SKU": sku, "Code": code, "Category": cat, "Number": num,
                            "Name": name, "SN": sn, "Location": final_loc, "Stock": stock,
                            "WarrantyStart": ws, "WarrantyEnd": we,
                            "Accessories": acc_json, "ItemType": "儀器",
                            "ImageFile": img_url
                        })
                        st.success(f"已新增: {name}")
                        st.balloons()
        
        else:
            # 地點選擇（form 外）
            st.markdown("##### 地點")
            selected_loc_cable = st.selectbox("選擇地點", LOCATION_OPTIONS, key="new_cable_loc")
            
            st.markdown("---")
            
            with st.form("add_cable"):
                st.markdown("##### 新增線材")
                
                name = st.text_input("線材名稱 *")
                c1, c2 = st.columns(2)
                code = c1.text_input("代碼")
                cat = c2.text_input("分類")
                
                c3, c4 = st.columns(2)
                stock = c3.number_input("庫存數量", min_value=0, value=1)
                
                st.markdown("##### 產品圖片")
                uploaded_img = st.file_uploader("上傳圖片", type=["jpg","png","jpeg"], key="img_cable")
                
                if st.form_submit_button("新增", type="primary", use_container_width=True):
                    if not name.strip():
                        st.error("請輸入線材名稱")
                    else:
                        sku = f"CBL-{code}-{int(time.time())}" if code else f"CBL-{int(time.time())}"
                        
                        # 上傳圖片
                        img_url = ""
                        if uploaded_img:
                            img_url = upload_image_to_firebase(uploaded_img , sku)
                            if not img_url:
                                st.warning("圖片上傳失敗，但產品已建檔")
                        
                        save_data_row({
                            "SKU": sku, "Code": code, "Category": cat,
                            "Name": name, "Location": selected_loc_cable, "Stock": stock,
                            "ItemType": "線材",
                            "ImageFile": img_url
                        })
                        st.success(f"已新增: {name}")

    with tabs[1]:
        st.markdown("### 產品編輯")
        st.caption("選擇產品後即可編輯資訊")
        
        df = load_data()
        
        if df.empty:
            st.warning("目前沒有任何產品")
        else:
            # 1. 產品選擇
            product_options = [f"{row['Name']} ({row['SKU']})" for _, row in df.iterrows()]
            selected_product = st.selectbox("選擇要編輯的產品", options=product_options, key="edit_select")
            
            if selected_product:
                # 取得選中的產品資料
                selected_index = product_options.index(selected_product)
                product_data = df.iloc[selected_index].to_dict()
                sku = product_data['SKU']
                item_type = product_data.get('ItemType', '儀器')
                
                st.info(f"📌 **SKU**: `{sku}` · **類型**: {item_type}")
                
                # 基本資訊（form 外）
                st.markdown("##### 基本資訊")
                col1, col2 = st.columns(2)
                name = col1.text_input("產品名稱 *", value=product_data.get('Name', ''), key=f"edit_name_{sku}")
                sn = col2.text_input("S/N 序號", value=product_data.get('SN', '') if pd.notna(product_data.get('SN')) else '', key=f"edit_sn_{sku}")
                
                # 分類資訊（form 外）
                st.markdown("##### 分類資訊")
                col3, col4, col5 = st.columns(3)
                code = col3.text_input("設備類型", value=product_data.get('Code', '') if pd.notna(product_data.get('Code')) else '', key=f"edit_code_{sku}")
                category = col4.text_input("分類", value=product_data.get('Category', '') if pd.notna(product_data.get('Category')) else '', key=f"edit_cat_{sku}")
                number = col5.text_input("編碼", value=product_data.get('Number', '') if pd.notna(product_data.get('Number')) else '', key=f"edit_num_{sku}")
                
                # 地點選擇（form 外）
                st.markdown("##### 地點")
                current_location = product_data.get('Location', '')
                
                # 解析地點資訊
                if '醫院-' in str(current_location):
                    parts = str(current_location).split('-')
                    default_loc = "醫院"
                    default_hosp = parts[1] if len(parts) > 1 else ""
                    default_stationed = "是" if len(parts) > 2 and "留院" in parts[2] else "否"
                else:
                    default_loc = current_location if current_location in LOCATION_OPTIONS else LOCATION_OPTIONS[0]
                    default_hosp = ""
                    default_stationed = "是"
                
                selected_loc = st.selectbox("選擇地點", options=LOCATION_OPTIONS, index=LOCATION_OPTIONS.index(default_loc) if default_loc in LOCATION_OPTIONS else 0, key=f"edit_loc_{sku}")
                
                # 醫院資訊（條件顯示）
                hosp_name = ""
                is_stationed = "否"
                if selected_loc == "醫院":
                    hc1, hc2 = st.columns(2)
                    hosp_name = hc1.text_input("醫院名稱", value=default_hosp, key=f"edit_hosp_{sku}")
                    is_stationed = hc2.radio("是否留院", ["是", "否"], index=0 if default_stationed == "是" else 1, horizontal=True, key=f"edit_stationed_{sku}")
                
                st.markdown("---")
                
                # 2. 編輯表單
                with st.form("edit_product_form"):
                    # 庫存
                    st.markdown("##### 庫存")
                    stock = st.number_input("數量", min_value=0, value=int(product_data.get('Stock', 0)))
                    
                    # 保固（僅儀器類型）
                    if item_type == "儀器":
                        st.markdown("##### 合約保固日")
                        w1, w2 = st.columns(2)
                        
                        current_ws = product_data.get('WarrantyStart')
                        current_we = product_data.get('WarrantyEnd')
                        
                        ws = w1.date_input("起始", value=pd.to_datetime(current_ws).date() if pd.notna(current_ws) else None)
                        we = w2.date_input("結束", value=pd.to_datetime(current_we).date() if pd.notna(current_we) else None)
                        
                        # 配件
                        st.markdown("##### 配件")
                        st.caption("編輯配件資訊（打勾並輸入數量）")
                        
                        # 解析既有配件
                        existing_acc = {}
                        acc_str = product_data.get('Accessories', '')
                        if acc_str and pd.notna(acc_str):
                            try:
                                existing_acc = json.loads(acc_str)
                            except:
                                pass
                        
                        acc_data = {}
                        for cat_name, items in ACCESSORY_CATEGORIES.items():
                            with st.expander(f"{cat_name} ({len(items)})", expanded=False):
                                for i, acc_name in enumerate(items):
                                    acc_col1, acc_col2 = st.columns([3, 1])
                                    is_checked = acc_name in existing_acc
                                    checked = acc_col1.checkbox(acc_name, value=is_checked, key=f"edit_acc_{cat_name}_{i}")
                                    qty = acc_col2.number_input("qty", min_value=1, value=existing_acc.get(acc_name, 1), key=f"edit_qty_{cat_name}_{i}", label_visibility="collapsed")
                                    if checked:
                                        acc_data[acc_name] = qty
                    
                    # 圖片
                    st.markdown("##### 產品圖片")
                    current_img_url = product_data.get('ImageFile', '')
                    if current_img_url and pd.notna(current_img_url):
                        display_url = get_displayable_image_url(current_img_url)
                        if display_url:
                            st.image(display_url, caption="當前圖片", width=200)
                    else:
                        st.caption("目前無圖片")
                    
                    uploaded_img = st.file_uploader("上傳新圖片（將替換原圖片）", type=["jpg","png","jpeg"], key="edit_img")
                    
                    # 提交按鈕
                    st.markdown("---")
                    col_save, col_delete = st.columns([2, 1])
                    
                    with col_save:
                        save_button = st.form_submit_button("💾 儲存變更", type="primary", use_container_width=True)
                    
                    with col_delete:
                        delete_button = st.form_submit_button("🗑️ 刪除產品", use_container_width=True)
                    
                    # 處理提交
                    if save_button:
                        if not name.strip():
                            st.error("請輸入產品名稱")
                        else:
                            # 處理地點
                            if selected_loc == "醫院" and hosp_name:
                                stationed_text = "留院" if is_stationed == "是" else "非留院"
                                final_loc = f"醫院-{hosp_name}-{stationed_text}"
                            else:
                                final_loc = selected_loc
                            
                            # 上傳新圖片（如果有）
                            img_url = current_img_url
                            if uploaded_img:
                                new_img_url = upload_image_to_firebase(uploaded_img, sku)
                                if new_img_url:
                                    img_url = new_img_url
                                    st.success("圖片已更新")
                                else:
                                    st.warning("圖片上傳失敗，其他資訊已更新")
                            
                            # 組裝資料
                            update_data = {
                                "SKU": sku,
                                "Name": name,
                                "SN": sn,
                                "Code": code,
                                "Category": category,
                                "Number": number,
                                "Location": final_loc,
                                "Stock": stock,
                                "ItemType": item_type,
                                "ImageFile": img_url
                            }
                            
                            # 儀器特有欄位
                            if item_type == "儀器":
                                update_data["WarrantyStart"] = ws
                                update_data["WarrantyEnd"] = we
                                update_data["Accessories"] = json.dumps(acc_data, ensure_ascii=False) if acc_data else ""
                            
                            # 儲存
                            save_data_row(update_data)
                            st.cache_data.clear()
                            st.success(f"✅ 已更新: {name}")
                            st.balloons()
                            time.sleep(1)
                            st.rerun()
                    
                    if delete_button:
                        # 刪除產品
                        db.collection(COLLECTION_products).document(sku).delete()
                        st.cache_data.clear()
                        st.success(f"🗑️ 已刪除: {name}")
                        time.sleep(1)
                        st.rerun()

    with tabs[2]:
        df_cur = load_data()
        if not df_cur.empty:
            st.markdown("##### 圖片管理")
            sel = st.selectbox("選擇項目", df_cur['SKU'].unique())
            
            # 顯示目前的圖片狀況
            selected_row = df_cur[df_cur['SKU'] == sel].iloc[0]
            raw_img = selected_row.get('ImageFile', '')
            processed_url = get_displayable_image_url(raw_img)
            
            st.markdown("**診斷資訊：**")
            st.code(f"資料庫原始值: {raw_img}\n處理後 URL: {processed_url}", language="text")
            
            # 嘗試顯示圖片
            if processed_url:
                st.markdown("**圖片預覽：**")
                try:
                    st.image(processed_url, width=200)
                except Exception as e:
                    st.error(f"圖片載入失敗: {e}")
            
            st.markdown("---")
            f = st.file_uploader("上傳新圖片", type=["jpg","png"])
            if f and st.button("更新"):
                url = upload_image_to_firebase(f, sel)
                if url:
                    db.collection(COLLECTION_products).document(sel).update({"imageFile": url})
                    st.cache_data.clear()
                    st.success("圖片已更新")
                    st.rerun()

    with tabs[3]:
        st.markdown("##### CSV 匯入")
        up_csv = st.file_uploader("選擇 CSV", type=["csv"])
        if up_csv:
            df_im = pd.read_csv(up_csv)
            st.dataframe(df_im.head())
            if st.button("匯入"):
                for i, r in df_im.iterrows():
                    save_data_row(r)
                st.success("匯入完成")
        
        st.markdown("---")
        st.markdown("##### 批次圖片上傳")
        st.caption("檔名可以是完整 SKU，或只包含部分關鍵字（程式會智能匹配）")
        imgs = st.file_uploader("選擇圖片", accept_multiple_files=True, key="batch_img")
        if imgs and st.button("上傳圖片"):
            # 先載入所有產品的 SKU
            all_products_df = load_data()
            all_skus = all_products_df['SKU'].tolist()
            
            bar = st.progress(0)
            success_count = 0
            fail_count = 0
            match_details = []
            
            for i, f in enumerate(imgs):
                filename = f.name.rsplit('.', 1)[0]  # 去掉副檔名
                
                # 智能匹配 SKU
                matched_sku = None
                match_type = None
                
                # 1. 精確匹配
                if filename in all_skus:
                    matched_sku = filename
                    match_type = "精確"
                else:
                    # 2. 模糊匹配（忽略空格、大小寫）
                    normalized_filename = filename.replace(" ", "").replace("-", "").lower()
                    for sku in all_skus:
                        normalized_sku = sku.replace(" ", "").replace("-", "").lower()
                        if normalized_filename == normalized_sku:
                            matched_sku = sku
                            match_type = "模糊"
                            break
                    
                    # 3. 部分匹配（檔名包含在 SKU 中）
                    if not matched_sku:
                        for sku in all_skus:
                            if filename in sku:
                                matched_sku = sku
                                match_type = "部分"
                                break
                
                if matched_sku:
                    # 上傳圖片到 R2
                    url = upload_image_to_firebase(f, matched_sku)
                    
                    if url:
                        # 更新資料庫
                        try:
                            db.collection(COLLECTION_products).document(matched_sku).update({"imageFile": url})
                            success_count += 1
                            match_details.append(f"✅ {filename} → {matched_sku} ({match_type}匹配)")
                        except Exception as e:
                            fail_count += 1
                            match_details.append(f"⚠️ {filename}: 圖片已上傳但資料庫更新失敗")
                    else:
                        fail_count += 1
                        match_details.append(f"❌ {filename}: 圖片上傳失敗")
                else:
                    fail_count += 1
                    match_details.append(f"❌ {filename}: 找不到對應的產品 SKU")
                
                bar.progress((i+1)/len(imgs))
            
            # 顯示結果
            st.cache_data.clear()
            st.success(f"✅ 完成！成功 {success_count} 筆，失敗 {fail_count} 筆")
            
            # 顯示詳細匹配結果
            with st.expander("查看詳細匹配結果"):
                for detail in match_details:
                    st.text(detail)
            
            if success_count > 0:
                st.rerun()

def page_reports():
    st.markdown("### 異動紀錄")
    st.dataframe(load_log(), use_container_width=True)

if __name__ == "__main__":
    main()