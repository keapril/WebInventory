# --- 在 app.py 最上方新增 import ---
import boto3
from botocore.exceptions import NoCredentialsError
from io import BytesIO  # 用於圖片壓縮

# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import io
import json
import time
import requests
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime, timedelta, timezone, date

# Firebase 相關套件
import firebase_admin
from firebase_admin import credentials, firestore, storage

# --- 1. 網頁基礎設定 ---
st.set_page_config(
    page_title="Inventory OS",
    page_icon="▫️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==========================================
# 🔧【設定值】Bucket 名稱
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
    st.error(f"Bucket 連線錯誤: {e}")

COLLECTION_products = "instrument_consumables" 
COLLECTION_logs = "consumables_logs"

# --- 3. UI 設計：現代懸浮毛玻璃風 (Modern Glassmorphism) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Noto+Sans+TC:wght@400;500;700&display=swap');

    :root {
        /* 背景不再是死白，而是帶有極淡的漸層 */
        --bg-gradient: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        --card-bg: rgba(255, 255, 255, 0.95);
        --text-main: #2d3436;
        --text-sub: #636e72;
        --accent-color: #0984e3; /* 科技藍 */
        --shadow-card: 0 10px 20px rgba(0,0,0,0.08), 0 6px 6px rgba(0,0,0,0.1);
        --radius-lg: 16px;
    }

    .stApp {
        background: var(--bg-gradient);
        background-attachment: fixed; /* 背景固定，讓內容滑動時更有層次 */
        color: var(--text-main);
        font-family: 'Inter', 'Noto Sans TC', sans-serif;
    }

    /* 側邊欄半透明化 */
    section[data-testid="stSidebar"] {
        background-color: rgba(255, 255, 255, 0.9);
        backdrop-filter: blur(10px);
        border-right: 1px solid rgba(255,255,255,0.5);
    }

    /* 卡片設計 - 懸浮感核心 */
    .glass-card {
        background: var(--card-bg);
        border-radius: var(--radius-lg);
        padding: 20px;
        margin-bottom: 20px;
        /* 雙層陰影製造懸浮感 */
        box-shadow: var(--shadow-card);
        border: 1px solid rgba(255, 255, 255, 0.8);
        display: flex;
        gap: 20px;
        align-items: center;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    .glass-card:hover {
        transform: translateY(-4px); /* 滑鼠移過去會浮起來 */
        box-shadow: 0 15px 30px rgba(0,0,0,0.12);
    }

    /* 圖片區塊 */
    .img-container {
        width: 85px;
        height: 85px;
        border-radius: 12px;
        overflow: hidden;
        box-shadow: inset 0 0 0 1px rgba(0,0,0,0.05);
        background: #fff;
        flex-shrink: 0;
    }
    .card-img {
        width: 100%;
        height: 100%;
        object-fit: cover;
    }

    /* 內容排版 */
    .content-area {
        flex-grow: 1;
    }
    .card-header {
        display: flex;
        align-items: center;
        gap: 12px;
        margin-bottom: 8px;
    }
    .item-name {
        font-size: 1.1rem;
        font-weight: 700;
        color: #2d3436;
        letter-spacing: 0.5px;
    }
    
    /* 標籤設計 */
    .badge {
        font-size: 0.75rem;
        padding: 4px 10px;
        border-radius: 6px;
        font-weight: 600;
        letter-spacing: 0.5px;
    }
    .badge-sku { background: #dfe6e9; color: #636e72; }
    .badge-cat { background: #e0f7fa; color: #0097a7; }
    
    /* 警示標籤 - 顏色加重 */
    .alert-tag {
        font-size: 0.7rem;
        padding: 3px 8px;
        border-radius: 20px;
        font-weight: 700;
        color: white;
        margin-left: 5px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .bg-danger { background: linear-gradient(135deg, #ff7675, #d63031); }
    .bg-warning { background: linear-gradient(135deg, #ffeaa7, #fdcb6e); color: #8a5a00; }

    /* 次要資訊 */
    .meta-info {
        font-size: 0.85rem;
        color: #636e72;
        margin-top: 6px;
        display: flex;
        align-items: center;
        gap: 15px;
    }
    .meta-item { display: flex; align-items: center; gap: 5px; }

    /* 庫存大數字 */
    .stock-display {
        text-align: right;
        min-width: 90px;
        padding-left: 20px;
        border-left: 2px solid #f1f2f6;
    }
    .stock-val {
        font-family: 'Inter', sans-serif;
        font-size: 2.2rem;
        font-weight: 700;
        color: #2d3436;
        line-height: 1;
        text-shadow: 2px 2px 0px rgba(0,0,0,0.05); /* 數字立體感 */
    }
    .stock-txt {
        font-size: 0.7rem;
        font-weight: 600;
        color: #b2bec3;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-top: 5px;
    }

    /* 輸入框優化 */
    .stTextInput input, .stNumberInput input {
        border-radius: 8px !important;
        border: 1px solid #dfe6e9 !important;
        box-shadow: 0 2px 5px rgba(0,0,0,0.03) !important;
    }
    .stTextInput input:focus {
        border-color: #0984e3 !important;
        box-shadow: 0 0 0 3px rgba(9, 132, 227, 0.1) !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 4. 核心函數庫 ---

def get_taiwan_time():
    tz = timezone(timedelta(hours=8))
    return datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")

@st.cache_data(ttl=300)
def load_data():
    """優化:加入快取機制提升效能"""
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
    """修正版：增加對空日期 (NaT) 的防呆機制"""
    ws = row_data.get("WarrantyStart")
    we = row_data.get("WarrantyEnd")
    
    # --- 🔧 修正開始：嚴格檢查日期格式 ---
    # 如果是 Pandas 的 NaT (Not a Time) 或空值，直接設為空字串
    if pd.isna(ws): 
        ws = ""
    elif isinstance(ws, (datetime, pd.Timestamp, date)): 
        ws = ws.strftime('%Y-%m-%d')
    else:
        ws = str(ws) if ws else ""

    if pd.isna(we): 
        we = ""
    elif isinstance(we, (datetime, pd.Timestamp, date)): 
        we = we.strftime('%Y-%m-%d')
    else:
        we = str(we) if we else ""
    # --- 修正結束 ---

    try: stock_val = int(row_data.get("Stock", 0))
    except: stock_val = 0
    
    data_dict = {
        "code": str(row_data.get("Code", "")),
        "categoryName": str(row_data.get("Category", "")),
        "number": str(row_data.get("Number", "")),
        "name": str(row_data.get("Name", "")),
        "imageFile": str(row_data.get("ImageFile", "")),
        "stock": stock_val,
        "location": str(row_data.get("Location", "")),
        "sn": str(row_data.get("SN", "")),
        "warrantyStart": str(ws),
        "warrantyEnd": str(we),
        "updatedAt": firestore.SERVER_TIMESTAMP
    }
    db.collection(COLLECTION_products).document(str(row_data["SKU"])).set(data_dict, merge=True)
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

# --- 替換原本的 upload_image_to_firebase 函式 ---
def upload_image_to_firebase(uploaded_file, sku, bucket_override=None):
    """
    雖然函式名稱沒改(為了相容舊程式碼)，但現在實際是上傳到 Cloudflare R2
    """
    if uploaded_file is None: return None
    
    # 讀取 Secrets
    try:
        r2_conf = st.secrets["cloudflare"]
        endpoint = r2_conf["endpoint"]
        access_key = r2_conf["access_key"]
        secret_key = r2_conf["secret_key"]
        bucket_name = r2_conf["bucket_name"]
        public_domain = r2_conf["public_domain"]
    except KeyError:
        st.error("❌ 找不到 Cloudflare 設定，請檢查 secrets.toml")
        return None

    try:
        # 1. 圖片壓縮處理 (強烈建議保留，節省頻寬與優化速度)
        image = Image.open(uploaded_file)
        if image.mode in ("RGBA", "P"): image = image.convert("RGB")
        
        # 限制最大寬度 800px
        max_width = 800
        if image.width > max_width:
            ratio = max_width / float(image.width)
            new_height = int(float(image.height) * ratio)
            image = image.resize((max_width, new_height), Image.Resampling.LANCZOS)
            
        img_byte_arr = BytesIO()
        image.save(img_byte_arr, format='JPEG', quality=80)
        img_byte_arr.seek(0)

        # 2. 建立 R2 (S3) 連線
        s3_client = boto3.client(
            's3',
            endpoint_url=endpoint,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key
        )

        # 3. 定義檔名 (SKU + 時間戳 + .jpg)
        safe_sku = "".join([c for c in sku if c.isalnum() or c in ('-','_')])
        file_name = f"images/{safe_sku}-{int(time.time())}.jpg"

        # 4. 執行上傳
        s3_client.upload_fileobj(
            img_byte_arr,
            bucket_name,
            file_name,
            ExtraArgs={'ContentType': 'image/jpeg'}
        )

        # 5. 回傳公開連結
        # 格式: https://pub-xxx.r2.dev/images/sku-123.jpg
        # 注意: R2 網址結尾若有斜線要處理一下，這裡假設 public_domain 沒有結尾斜線
        return f"{public_domain}/{file_name}"

    except Exception as e:
        st.error(f"R2 上傳失敗: {e}")
        return None

def check_warranty_status(warranty_end):
    """檢查保固狀態"""
    if pd.isna(warranty_end): return None, None
    try:
        end_date = pd.to_datetime(warranty_end)
        today = pd.Timestamp.now()
        days_left = (end_date - today).days
        
        if days_left < 0: 
            return "已過期", days_left
        elif days_left <= 30: 
            return "即將到期", days_left
        else: 
            return "正常", days_left
    except:
        return None, None

def get_stock_alert_level(stock):
    """庫存警示等級"""
    if stock == 0: return "無庫存"
    elif stock <= 3: return "極低"
    elif stock <= 5: return "偏低"
    else: return "正常"

def get_warranty_alerts(df):
    """取得保固到期警示清單"""
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
    st.sidebar.markdown("<div class='sidebar-brand'>儀器耗材中控</div>", unsafe_allow_html=True)
    
    # 🆕 保固到期提醒 (側邊欄)
    df = load_data()
    warranty_alerts = get_warranty_alerts(df)
    
    if warranty_alerts:
        with st.sidebar.expander(f"⚠️ 保固提醒 ({len(warranty_alerts)})", expanded=True):
            for alert in warranty_alerts[:5]:  # 只顯示前5筆
                days = alert['DaysLeft']
                status_color = "#DC2626" if days < 0 else "#F59E0B"
                
                if days < 0:
                    day_text = f"已過期 {abs(days)} 天"
                else:
                    day_text = f"剩 {days} 天"
                
                st.markdown(f"""
                <div style='padding:8px 0; border-bottom:1px solid #F0F0F0;'>
                    <div style='font-size:0.85rem; font-weight:600; color:{status_color};'>{alert['Name']}</div>
                    <div style='font-size:0.75rem; color:#999;'>{alert['SKU']} · {day_text}</div>
                </div>
                """, unsafe_allow_html=True)
            
            if len(warranty_alerts) > 5:
                st.caption(f"+ 還有 {len(warranty_alerts) - 5} 項...")
    
    # 連線診斷工具
    with st.sidebar.expander("🔧 連線診斷"):
        st.caption("如果圖片上傳失敗,請在此測試。")
        user_bucket_name = st.text_input("Bucket 名稱", value=CUSTOM_BUCKET_NAME)
        
        if st.button("測試連線"):
            try:
                test_bucket = storage.bucket(name=user_bucket_name)
                if test_bucket.exists():
                    st.success("✅ 連線成功!")
                    st.session_state['valid_bucket'] = test_bucket
                    st.session_state['valid_bucket_name'] = user_bucket_name
                else:
                    st.error("❌ 找不到此 Bucket")
            except Exception as e:
                st.error(f"錯誤: {e}")

    global bucket
    if 'valid_bucket' in st.session_state:
        bucket = st.session_state['valid_bucket']

    menu_options = [
        "總覽與查詢", 
        "入庫作業", 
        "出庫作業", 
        "資料維護",
        "異動紀錄",
        "保固管理"  # 🆕 新增頁面
    ]
    
    page = st.sidebar.radio("選單", menu_options, label_visibility="collapsed")

    if page == "總覽與查詢": page_search()
    elif page == "入庫作業": page_operation("入庫")
    elif page == "出庫作業": page_operation("出庫")
    elif page == "資料維護": page_maintenance()
    elif page == "異動紀錄": page_reports()
    elif page == "保固管理": page_warranty_management()  # 🆕

def render_nordic_card(row):
    """渲染現代懸浮風卡片 (Glassmorphism)"""
    # 1. 圖片
    img_url = row.get('ImageFile', '')
    has_img = img_url and str(img_url).startswith("http")
    
    if has_img:
        img_html = f'<img src="{img_url}" class="card-img">'
    else:
        # 無圖時顯示一個漂亮的圖標
        img_html = '<div style="width:100%;height:100%;display:flex;align-items:center;justify-content:center;color:#b2bec3;font-size:1.8rem;">📦</div>'
    
    # 2. 庫存邏輯
    try: stock = int(row['Stock'])
    except: stock = 0
        
    alerts = []
    if stock == 0:
        alerts.append('<span class="alert-tag bg-danger">缺貨</span>')
    elif stock <= 5:
        alerts.append('<span class="alert-tag bg-warning">低量</span>')
        
    warranty_status, _ = check_warranty_status(row.get('WarrantyEnd'))
    if warranty_status == "已過期":
        alerts.append('<span class="alert-tag bg-danger">過保</span>')
    elif warranty_status == "即將到期":
        alerts.append('<span class="alert-tag bg-warning">保固快到</span>')
    
    alert_html = "".join(alerts)
    
    # 3. 欄位
    sku = row['SKU']
    category = row['Category']
    name = row['Name']
    loc = row['Location'] if row['Location'] else "未設定"
    sn = row['SN'] if row['SN'] else "-"

    # 4. HTML 組裝 (保持靠左對齊)
    html = f"""<div class="glass-card">
<div class="img-container">
{img_html}
</div>
<div class="content-area">
<div class="card-header">
<span class="item-name">{name}</span>
{alert_html}
</div>
<div style="margin-bottom:8px;">
<span class="badge badge-sku">{sku}</span>
<span class="badge badge-cat">{category}</span>
</div>
<div class="meta-info">
<span class="meta-item">📍 {loc}</span>
<span class="meta-item">#️⃣ {sn}</span>
</div>
</div>
<div class="stock-display">
<div class="stock-val">{stock}</div>
<div class="stock-txt">In Stock</div>
</div>
</div>"""
    
    st.markdown(html, unsafe_allow_html=True)

def page_search():
    """總覽與查詢頁面"""
    st.title("總覽 Overview")
    df = load_data()
    
    # 🆕 頂部警示區
    warranty_alerts = get_warranty_alerts(df)
    critical_alerts = [a for a in warranty_alerts if a['DaysLeft'] < 0]
    warning_alerts = [a for a in warranty_alerts if 0 <= a['DaysLeft'] <= 30]
    
    if critical_alerts:
        st.markdown(f"""
        <div class="alert-box critical">
            <div class="alert-box-title">🚨 緊急警示</div>
            <div class="alert-box-content">
                有 <strong>{len(critical_alerts)}</strong> 項設備保固已過期,請立即處理!
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    if warning_alerts:
        st.markdown(f"""
        <div class="alert-box">
            <div class="alert-box-title">⚠️ 保固提醒</div>
            <div class="alert-box-content">
                有 <strong>{len(warning_alerts)}</strong> 項設備保固將在 30 天內到期。
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    # 統計資訊
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("總品項", len(df))
    
    low_stock = len(df[df['Stock'] <= 5])
    c2.metric("低庫存", low_stock, delta="Alert" if low_stock > 0 else None, delta_color="inverse")
    
    no_stock = len(df[df['Stock'] == 0])
    c3.metric("無庫存", no_stock, delta="Critical" if no_stock > 0 else None, delta_color="inverse")
    
    c4.metric("保固到期", len(warranty_alerts), delta="Attention" if warranty_alerts else None, delta_color="inverse")
    
    st.markdown("---")
    
    # 進階篩選區
    with st.expander("🔍 進階篩選", expanded=False):
        fc1, fc2, fc3 = st.columns(3)
        
        filter_category = fc1.multiselect(
            "分類", 
            options=df['Category'].unique().tolist(),
            default=[]
        )
        
        filter_location = fc2.multiselect(
            "地點",
            options=df['Location'].unique().tolist(),
            default=[]
        )
        
        filter_stock = fc3.selectbox(
            "庫存狀態",
            ["全部", "正常", "低庫存(≤5)", "無庫存"]
        )
    
    # 關鍵字搜尋
    search_term = st.text_input("搜尋庫存", placeholder="輸入關鍵字 (名稱、SKU、地點)...")
    
    # 套用篩選
    result = df.copy()
    
    if filter_category:
        result = result[result['Category'].isin(filter_category)]
    
    if filter_location:
        result = result[result['Location'].isin(filter_location)]
    
    if filter_stock == "低庫存(≤5)":
        result = result[result['Stock'] <= 5]
    elif filter_stock == "無庫存":
        result = result[result['Stock'] == 0]
    elif filter_stock == "正常":
        result = result[result['Stock'] > 5]
    
    if search_term:
        mask = result.astype(str).apply(lambda x: x.str.contains(search_term, case=False, na=False)).any(axis=1)
        result = result[mask]
    
    st.caption(f"找到 {len(result)} 筆資料")
    st.write("") 
    
    if result.empty:
        st.info("無符合資料")
    else:
        for index, row in result.iterrows():
            render_nordic_card(row)

def page_warranty_management():
    """🆕 保固管理頁面"""
    st.title("保固管理 Warranty")
    
    df = load_data()
    warranty_alerts = get_warranty_alerts(df)
    
    if not warranty_alerts:
        st.success("✅ 目前沒有保固到期的設備!")
        return
    
    # 分類統計
    c1, c2, c3 = st.columns(3)
    expired = [a for a in warranty_alerts if a['DaysLeft'] < 0]
    within_30 = [a for a in warranty_alerts if 0 <= a['DaysLeft'] <= 30]
    within_90 = [a for a in warranty_alerts if 30 < a['DaysLeft'] <= 90]
    
    c1.metric("已過期", len(expired), delta="Critical", delta_color="inverse")
    c2.metric("30天內到期", len(within_30), delta="Warning", delta_color="inverse")
    c3.metric("90天內到期", len(within_90))
    
    st.markdown("---")
    
    # 篩選器
    filter_type = st.selectbox(
        "篩選條件",
        ["全部", "已過期", "30天內到期", "90天內到期"]
    )
    
    # 套用篩選
    if filter_type == "已過期":
        display_alerts = expired
    elif filter_type == "30天內到期":
        display_alerts = within_30
    elif filter_type == "90天內到期":
        display_alerts = within_90
    else:
        display_alerts = warranty_alerts
    
    st.caption(f"共 {len(display_alerts)} 筆")
    st.write("")
    
    # 顯示清單
    for alert in display_alerts:
        days = alert['DaysLeft']
        
        if days < 0:
            day_text = f"已過期 {abs(days)} 天"
            status_class = "alert-low"
        elif days <= 30:
            day_text = f"剩餘 {days} 天"
            status_class = "alert-warning"
        else:
            day_text = f"剩餘 {days} 天"
            status_class = "alert-badge"
        
        warranty_date = alert['WarrantyEnd'].strftime('%Y-%m-%d') if pd.notna(alert['WarrantyEnd']) else "未設定"
        
        st.markdown(f"""
        <div class="warranty-item">
            <div class="warranty-item-left">
                <div class="warranty-item-name">{alert['Name']}</div>
                <div class="warranty-item-meta">
                    SKU: {alert['SKU']} &nbsp;|&nbsp; 
                    分類: {alert['Category']} &nbsp;|&nbsp; 
                    地點: {alert['Location']}
                </div>
                <div class="warranty-item-meta" style="margin-top:4px;">
                    到期日: {warranty_date}
                </div>
            </div>
            <div class="warranty-item-date">
                <span class="warranty-label">狀態</span>
                <div class="warranty-days">{day_text}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # 匯出功能
    if st.button("📥 下載保固到期清單 (CSV)"):
        df_export = pd.DataFrame(display_alerts)
        if not df_export.empty:
            csv = df_export.to_csv(index=False, encoding='utf-8-sig')
            st.download_button(
                "點此下載",
                csv,
                f"warranty_alerts_{datetime.now().strftime('%Y%m%d')}.csv",
                "text/csv"
            )

def page_operation(op_type):
    st.title(f"{op_type}作業")
    st.caption("請掃描條碼或手動輸入 SKU 進行作業。")
    
    c1, c2 = st.columns([1, 3])
    qty = c1.number_input("數量", min_value=1, value=1)
    
    if "scan_input" not in st.session_state: st.session_state.scan_input = ""
    
    def on_scan():
        if st.session_state.scan_box:
            process_stock(st.session_state.scan_box, qty, op_type)
            st.session_state.scan_box = ""
    
    st.text_input("條碼/SKU 輸入框", key="scan_box", on_change=on_scan, placeholder="在此輸入並按 Enter...")

def process_stock(sku, qty, op_type):
    doc_ref = db.collection(COLLECTION_products).document(sku)
    doc = doc_ref.get()
    
    if doc.exists:
        data = doc.to_dict()
        current = data.get('stock', 0)
        new_stock = current + qty if op_type == "入庫" else current - qty
        
        if new_stock < 0:
            st.error(f"❌ 庫存不足!目前庫存: {current}")
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
        st.toast(f"✅ 成功! {sku} 庫存: {new_stock}")
    else:
        st.error(f"❌ 找不到 SKU: {sku}")

def page_maintenance():
    st.title("資料維護")
    tabs = st.tabs(["新增項目", "編輯表格", "更換圖片", "匯入 CSV", "匯入圖片", "系統重置"])
    
    with tabs[0]:
        st.caption("建立一筆新的庫存資料。")
        with st.form("add_form", clear_on_submit=False):
            st.subheader("基本資訊")
            c1, c2 = st.columns(2)
            code = c1.text_input("產品編碼 (Code)")
            cat = c2.text_input("分類 (Category)")
            c3, c4 = st.columns(2)
            num = c3.text_input("號碼 (Number)")
            name = c4.text_input("品名 (Name)")
            
            st.subheader("詳細規格")
            c5, c6 = st.columns(2)
            sn = c5.text_input("序號 (S/N)")
            loc_options = ["北", "中", "南", "高", "醫院"]
            selected_loc = c6.selectbox("存放地點", loc_options)
            
            final_loc = selected_loc
            
            enable_warranty = st.checkbox("啟用合約保固日期")
            if enable_warranty:
                c_w1, c_w2 = st.columns(2)
                w_start = c_w1.date_input("保固開始")
                w_end = c_w2.date_input("保固結束")
            else:
                w_start, w_end = None, None

            stock = st.number_input("初始庫存", 0, value=1)
            submitted = st.form_submit_button("建立資料")

        hospital_name = ""
        if selected_loc == "醫院":
            hospital_name = st.text_input("請輸入醫院名稱", key="hosp_input")
            if hospital_name: final_loc = f"醫院-{hospital_name}"
        
        if submitted:
            if code and name:
                if selected_loc == "醫院" and not hospital_name:
                    st.error("請輸入醫院名稱")
                else:
                    sku = f"{code}-{cat}-{num}"
                    save_data_row({
                        "SKU":sku, "Code":code, "Category":cat, "Number":num, 
                        "Name":name, "SN":sn, "Location":final_loc, "Stock":stock,
                        "WarrantyStart": w_start, "WarrantyEnd": w_end
                    })
                    st.success(f"✅ 新增成功: {sku}")
            else:
                st.error("Code 與 Name 為必填。")

    with tabs[1]:
        st.caption("直接修改表格內容。")
        df = load_data()
        col_config = {
            "SKU": st.column_config.TextColumn("SKU", disabled=True),
            "WarrantyStart": st.column_config.DateColumn("保固開始"),
            "WarrantyEnd": st.column_config.DateColumn("保固結束"),
            "ImageFile": st.column_config.ImageColumn("圖片"),
        }
        edited = st.data_editor(df, num_rows="dynamic", use_container_width=True, key="data_editor_main", column_config=col_config)
        if st.button("儲存變更", type="primary"):
            with st.spinner("同步中..."):
                for i, row in edited.iterrows():
                    if row['SKU']: save_data_row(row)
            st.success("✅ 已更新。")
            time.sleep(1)
            st.rerun()

    with tabs[2]:
        st.caption("更新單一圖片。")
        df_cur = load_data()
        if not df_cur.empty:
            sel = st.selectbox("選擇商品", df_cur['SKU'].unique())
            if sel:
                row = df_cur[df_cur['SKU'] == sel].iloc[0]
                st.write(f"已選: **{row['Name']}**")
                
                curr_img = row.get('ImageFile')
                if curr_img and str(curr_img).startswith('http'):
                    st.image(curr_img, width=150)
                
                f = st.file_uploader("上傳新圖片", type=["jpg","png"], key="single_uploader")
                if f and st.button("更新圖片"):
                    url = upload_image_to_firebase(f, sel)
                    if url:
                        db.collection(COLLECTION_products).document(sel).update({"imageFile": url})
                        st.success("✅ 圖片已更新。")
        else:
            st.info("無資料。")

    with tabs[3]:
        st.caption("批次匯入 CSV。")
        up_csv = st.file_uploader("選擇 CSV 檔案", type=["csv"], key="csv_batch_uploader")
        if up_csv:
            try:
                df_im = None
                for enc in ['utf-8-sig', 'utf-8', 'big5', 'cp950']:
                    try:
                        up_csv.seek(0)
                        df_im = pd.read_csv(up_csv, encoding=enc)
                        break
                    except: continue
                
                if df_im is not None:
                    df_im.columns = [str(c).strip() for c in df_im.columns]
                    st.dataframe(df_im.head(3))
                    
                    if st.button("執行匯入"):
                        progress_bar = st.progress(0)
                        col_map = {c.lower(): c for c in df_im.columns}
                        def get_val(r, k): return r.get(col_map.get(k.lower()), '')

                        for i, row in df_im.iterrows():
                            sku = str(get_val(row, 'sku')).strip()
                            if sku and sku.lower() != 'nan':
                                save_data_row({
                                    "SKU": sku, 
                                    "Code": get_val(row,'code'), "Category": get_val(row,'category'),
                                    "Number": get_val(row,'number'), "Name": get_val(row,'name'), 
                                    "ImageFile": get_val(row,'imagefile'), "Stock": get_val(row,'stock'), 
                                    "Location": get_val(row,'location'), "SN": get_val(row,'sn'),
                                    "WarrantyStart": get_val(row,'warrantystart'), "WarrantyEnd": get_val(row,'warrantyend')
                                })
                            progress_bar.progress((i+1)/len(df_im))
                        
                        st.success("✅ 匯入完成。")
                        time.sleep(1)
                        st.rerun()
                else:
                    st.error("無法讀取 CSV。")
            except Exception as e:
                st.error(f"錯誤: {e}")

    with tabs[4]:
        st.caption("批次上傳 (檔名 = SKU)。")
        all_skus = [d.id for d in db.collection(COLLECTION_products).stream()]
        
        if not all_skus:
            st.warning("資料庫為空,請先匯入 CSV。")
        else:
            imgs = st.file_uploader("選擇多張圖片", type=["jpg", "png", "jpeg"], accept_multiple_files=True, key="multi_img_uploader")
            if imgs and st.button("開始上傳"):
                bar = st.progress(0)
                succ = 0
                fail = 0
                
                for i, f in enumerate(imgs):
                    sku = f.name.rsplit('.', 1)[0].strip()
                    if sku in all_skus:
                        u = upload_image_to_firebase(f, sku)
                        if u:
                            db.collection(COLLECTION_products).document(sku).update({"imageFile": u})
                            succ += 1
                    else:
                        fail += 1
                    bar.progress((i+1)/len(imgs))
                
                st.success(f"✅ 完成。成功: {succ}, 跳過: {fail}")
                time.sleep(2)
                st.rerun()

    with tabs[5]:
        st.error("危險區域:永久刪除所有資料。")
        confirm = st.text_input("輸入 'DELETE' 確認刪除", key="delete_confirm")
        if st.button("清空資料庫"):
            if confirm == "DELETE":
                with st.spinner("刪除中..."): c = delete_all_products_logic()
                st.success(f"✅ 已刪除 {c} 筆資料。")
                time.sleep(1)
                st.rerun()
            else: st.error("確認碼錯誤。")

def page_reports():
    st.title("異動紀錄")
    df = load_log()
    st.dataframe(df, use_container_width=True)
    st.download_button("📥 下載 CSV", df.to_csv(index=False).encode('utf-8-sig'), "log.csv", "text/csv")

if __name__ == "__main__":
    main()