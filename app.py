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
        --primary: #5C6B73;       /* 藍灰 */
        --accent: #9DB4C0;        /* 淡藍灰 */
        --bg: #FAFAF8;            /* 米白 */
        --card: #FFFFFF;
        --text: #2D3436;          /* 墨色 */
        --text-light: #8B9A9C;    /* 淡墨 */
        --border: #E8ECEB;        /* 淡線 */
        --hover: #F5F7F6;
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
    
    /* 標籤 */
    .tag {
        display: inline-block;
        font-size: 0.7rem;
        padding: 2px 8px;
        border-radius: 2px;
        margin-top: 4px;
        letter-spacing: 0.05em;
    }
    .tag-normal { background: #F0F4F3; color: #5C7A6B; border: 1px solid #D8E4DE; }
    .tag-warning { background: #FEF9F0; color: #B8860B; border: 1px solid #F5E6C8; }
    .tag-danger { background: #FDF5F5; color: #B85450; border: 1px solid #F0D8D8; }
    .tag-type { background: #F5F7FA; color: var(--primary); border: 1px solid var(--border); }
    
    /* 按鈕 */
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
        background: var(--primary);
        color: white;
        border: none;
    }
    div.stButton > button[kind="primary"]:hover {
        background: #4A5960;
    }
    
    /* 輸入欄位 */
    .stTextInput input, .stNumberInput input, 
    .stSelectbox div[data-baseweb="select"], .stTextArea textarea {
        border-radius: 4px;
        border-color: var(--border);
        font-family: var(--font-main);
    }
    .stTextInput input:focus, .stTextArea textarea:focus {
        border-color: var(--accent);
        box-shadow: none;
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
    .stTabs [data-baseweb="tab"] { 
        font-size: 0.85rem;
        letter-spacing: 0.05em;
    }
    
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
    if pd.isna(warranty_end): return None, None
    try:
        end_date = pd.to_datetime(warranty_end)
        today = pd.Timestamp.now()
        days_left = (end_date - today).days
        if days_left < 0: return "已過期", days_left
        elif days_left <= 30: return "即將到期", days_left
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

# 處理圖片 URL（支援 Firebase Storage 舊圖片）
@st.cache_data(ttl=3600)  # 快取 1 小時
def get_displayable_image_url(img_url):
    """處理圖片 URL，將 Firebase Storage URL 轉換為可存取的簽名 URL"""
    if not img_url or not str(img_url).startswith("http"):
        return None
    
    img_url = str(img_url)
    
    # 檢查是否為 Firebase Storage URL
    if "storage.googleapis.com" in img_url or "firebasestorage.app" in img_url:
        try:
            # 從 URL 中提取 blob 路徑
            # URL 格式: https://storage.googleapis.com/bucket-name/path/to/file
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
    
    # Cloudflare R2 或其他 URL 直接返回
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
        "入庫", 
        "出庫", 
        "資料維護",
        "異動紀錄",
        "保固管理"
    ]
    
    page = st.sidebar.radio("", menu_options, label_visibility="collapsed")

    if page == "總覽": page_search()
    elif page == "入庫": page_operation("入庫")
    elif page == "出庫": page_operation("出庫")
    elif page == "資料維護": page_maintenance()
    elif page == "異動紀錄": page_reports()
    elif page == "保固管理": page_warranty_management()

def render_item_card(row):
    """渲染項目卡片 - 日式簡約風格"""
    raw_img_url = row.get('ImageFile', '')
    img_url = get_displayable_image_url(raw_img_url)
    has_img = img_url is not None
    item_type = row.get('ItemType', '儀器')
    
    if has_img:
        img_html = f'<img src="{img_url}" class="item-thumb">'
    else:
        type_label = "器" if item_type == "儀器" else "線"
        img_html = f'<div class="item-thumb-empty">{type_label}</div>'
    
    try: stock = int(row['Stock'])
    except: stock = 0
    
    # 標籤
    tags = [f'<span class="tag tag-type">{item_type}</span>']
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
    acc_html = f'<div class="acc-list">{acc_display}</div>' if acc_display else ""

    html = f"""<div class="item-card">
{img_html}
<div class="item-content">
<div class="item-main">
    <div class="item-name">{row['Name']}</div>
    <div class="item-sku">{row['SKU']}</div>
</div>
<div class="item-meta">
    <div>{row['Category']} · {row['Location'] if row['Location'] else '-'}</div>
    {acc_html}
</div>
<div class="item-stock">
    <div class="stock-num">{stock}</div>
    <div>{tags_html}</div>
</div>
</div>
</div>"""
    st.markdown(html, unsafe_allow_html=True)

def page_search():
    st.markdown("### 總覽")
    df = load_data()
    
    # 統計區
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("總計", len(df))
    col2.metric("儀器", len(df[df['ItemType'] == '儀器']))
    col3.metric("線材", len(df[df['ItemType'] == '線材']))
    col4.metric("低庫存", len(df[df['Stock'] <= 5]))
    col5.metric("保固注意", len(get_warranty_alerts(df)))
    
    st.markdown("---")
    
    # 篩選
    with st.expander("篩選條件"):
        fc1, fc2, fc3, fc4 = st.columns(4)
        filter_type = fc1.multiselect("類型", options=ITEM_TYPES)
        filter_category = fc2.multiselect("分類", options=df['Category'].unique().tolist())
        filter_location = fc3.multiselect("地點", options=df['Location'].unique().tolist())
        filter_stock = fc4.selectbox("庫存", ["全部", "正常", "低庫存", "無庫存"])
    
    search_term = st.text_input("搜尋", placeholder="輸入名稱、SKU 或關鍵字")
    
    result = df.copy()
    if filter_type: result = result[result['ItemType'].isin(filter_type)]
    if filter_category: result = result[result['Category'].isin(filter_category)]
    if filter_location: result = result[result['Location'].isin(filter_location)]
    if filter_stock == "低庫存": result = result[result['Stock'] <= 5]
    elif filter_stock == "無庫存": result = result[result['Stock'] == 0]
    
    if search_term:
        mask = result.astype(str).apply(lambda x: x.str.contains(search_term, case=False, na=False)).any(axis=1)
        result = result[mask]
    
    st.caption(f"共 {len(result)} 筆")
    
    for index, row in result.iterrows():
        render_item_card(row)

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
    st.markdown("### 資料維護")
    tabs = st.tabs(["新增", "編輯", "圖片", "匯入", "重置"])
    
    with tabs[0]:
        item_type = st.radio("品項類型", ITEM_TYPES, horizontal=True, key="add_type")
        st.markdown("---")
        
        if item_type == "儀器":
            with st.form("add_instrument"):
                st.markdown("##### 新增儀器")
                
                c1, c2 = st.columns(2)
                name = c1.text_input("儀器名稱 *")
                sn = c2.text_input("S/N 序號")
                
                c3, c4, c5 = st.columns(3)
                code = c3.text_input("設備類型")
                cat = c4.text_input("分類")
                num = c5.text_input("編碼")
                
                st.markdown("##### 地點")
                lc1, lc2 = st.columns([1, 2])
                selected_loc = lc1.selectbox("選擇地點", LOCATION_OPTIONS)
                hosp_input = ""
                if selected_loc == "醫院":
                    hosp_input = lc2.text_input("醫院名稱")
                
                st.markdown("##### 合約保固日")
                w1, w2 = st.columns(2)
                ws = w1.date_input("起始", value=None)
                we = w2.date_input("結束", value=None)
                
                st.markdown("##### 配件")
                acc_data = {}
                
                for cat_name, items in ACCESSORY_CATEGORIES.items():
                    with st.expander(f"{cat_name} ({len(items)})"):
                        cols = st.columns(2)
                        for i, acc_name in enumerate(items):
                            col = cols[i % 2]
                            with col:
                                cc1, cc2 = st.columns([3, 1])
                                checked = cc1.checkbox(acc_name, key=f"a_{cat_name}_{i}")
                                if checked:
                                    qty = cc2.number_input("", min_value=1, value=1, key=f"q_{cat_name}_{i}", label_visibility="collapsed")
                                    acc_data[acc_name] = qty
                
                other_acc = st.text_input("其他配件")
                if other_acc:
                    acc_data["其他"] = other_acc
                
                stock = st.number_input("庫存數量", min_value=0, value=1)
                
                if st.form_submit_button("新增", type="primary", use_container_width=True):
                    if not name.strip():
                        st.error("請輸入儀器名稱")
                    else:
                        final_loc = f"醫院-{hosp_input}" if selected_loc == "醫院" and hosp_input else selected_loc
                        sku = f"{code}-{cat}-{num}" if all([code, cat, num]) else f"INS-{int(time.time())}"
                        acc_json = json.dumps(acc_data, ensure_ascii=False) if acc_data else ""
                        
                        save_data_row({
                            "SKU": sku, "Code": code, "Category": cat, "Number": num,
                            "Name": name, "SN": sn, "Location": final_loc, "Stock": stock,
                            "WarrantyStart": ws, "WarrantyEnd": we,
                            "Accessories": acc_json, "ItemType": "儀器"
                        })
                        st.success(f"已新增: {name}")
                        st.balloons()
        
        else:
            with st.form("add_cable"):
                st.markdown("##### 新增線材")
                
                name = st.text_input("線材名稱 *")
                c1, c2 = st.columns(2)
                code = c1.text_input("代碼")
                cat = c2.text_input("分類")
                
                c3, c4 = st.columns(2)
                stock = c3.number_input("庫存數量", min_value=0, value=1)
                selected_loc = c4.selectbox("地點", LOCATION_OPTIONS)
                
                if st.form_submit_button("新增", type="primary", use_container_width=True):
                    if not name.strip():
                        st.error("請輸入線材名稱")
                    else:
                        sku = f"CBL-{code}-{int(time.time())}" if code else f"CBL-{int(time.time())}"
                        save_data_row({
                            "SKU": sku, "Code": code, "Category": cat,
                            "Name": name, "Location": selected_loc, "Stock": stock,
                            "ItemType": "線材"
                        })
                        st.success(f"已新增: {name}")

    with tabs[1]:
        st.caption("選取列後按 Delete 可標記刪除")
        df = load_data()
        original_skus = set(df["SKU"].astype(str).tolist()) if not df.empty else set()

        col_config = {
            "SKU": st.column_config.TextColumn("SKU", disabled=True),
            "ItemType": st.column_config.SelectboxColumn("類型", options=ITEM_TYPES),
            "Location": st.column_config.SelectboxColumn("地點", options=LOCATION_OPTIONS + ["醫院-其他"]),
            "WarrantyStart": st.column_config.DateColumn("保固起"),
            "WarrantyEnd": st.column_config.DateColumn("保固迄"),
            "ImageFile": st.column_config.ImageColumn("圖片"),
        }
        
        edited = st.data_editor(df, num_rows="dynamic", use_container_width=True, key="editor", column_config=col_config)
        
        if st.button("儲存變更", type="primary"):
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
                        
            st.success(f"完成！更新 {upd_count} 筆，刪除 {del_count} 筆。")
            time.sleep(1)
            st.cache_data.clear()
            st.rerun()

    with tabs[2]:
        df_cur = load_data()
        if not df_cur.empty:
            sel = st.selectbox("選擇項目", df_cur['SKU'].unique())
            f = st.file_uploader("上傳圖片", type=["jpg","png"])
            if f and st.button("更新"):
                url = upload_image_to_firebase(f, sel)
                if url:
                    db.collection(COLLECTION_products).document(sel).update({"imageFile": url})
                    st.success("圖片已更新")

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
        st.caption("檔名需為 SKU")
        imgs = st.file_uploader("選擇圖片", accept_multiple_files=True, key="batch_img")
        if imgs and st.button("上傳圖片"):
            bar = st.progress(0)
            for i, f in enumerate(imgs):
                sku = f.name.rsplit('.', 1)[0]
                upload_image_to_firebase(f, sku)
                bar.progress((i+1)/len(imgs))
            st.success("完成")

    with tabs[4]:
        st.warning("以下操作無法復原")
        confirm = st.checkbox("我確定要清空所有資料")
        if confirm:
            if st.button("清空資料庫", type="primary"):
                count = delete_all_products_logic()
                st.success(f"已刪除 {count} 筆")
                st.rerun()

def page_reports():
    st.markdown("### 異動紀錄")
    st.dataframe(load_log(), use_container_width=True)

if __name__ == "__main__":
    main()