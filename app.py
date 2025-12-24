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
# 🔧【設定區】Bucket 名稱 (已更新為您提供的名稱)
# ==========================================
CUSTOM_BUCKET_NAME = "product-system-900c4.firebasestorage.app"

# --- 2. Firebase 初始化 ---
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
        
        # 初始化
        firebase_admin.initialize_app(cred, {
            'storageBucket': CUSTOM_BUCKET_NAME
        })
    except Exception as e:
        st.error(f"連線失敗: {e}")
        st.stop()

db = firestore.client()

# 強制獲取指定名稱的 Bucket
try:
    bucket = storage.bucket(name=CUSTOM_BUCKET_NAME)
except Exception as e:
    st.error(f"Bucket 連線錯誤: {e}")

COLLECTION_products = "instrument_consumables" 
COLLECTION_logs = "consumables_logs"

# --- 3. SaaS / 雜誌文青風 CSS ---
st.markdown("""
    <style>
    /* 引入字體：標題用襯線體(Playfair Display)，內文用無襯線體(Inter) */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&family=Playfair+Display:wght@400;600;700&family=Noto+Sans+TC:wght@300;400;500&display=swap');

    /* 全域變數定義 */
    :root {
        --bg-color: #FFFFFF;
        --sidebar-bg: #F8F9FA;
        --text-primary: #2C2C2C; /* 深灰，不全黑 */
        --text-secondary: #666666;
        --accent-color: #111111; 
        --border-color: #EEEEEE;
        --font-serif: 'Playfair Display', 'Noto Sans TC', serif; /* 中文標題也用黑體或明體 */
        --font-sans: 'Inter', 'Noto Sans TC', sans-serif;
    }

    /* 基礎重置 */
    .stApp {
        background-color: var(--bg-color);
        color: var(--text-primary);
        font-family: var(--font-sans);
    }

    /* 側邊欄優化 */
    section[data-testid="stSidebar"] {
        background-color: var(--sidebar-bg);
        border-right: 1px solid var(--border-color);
        padding-top: 20px;
    }
    section[data-testid="stSidebar"] .stRadio label {
        color: var(--text-secondary);
        font-size: 0.95rem; /* 稍微放大中文 */
        padding: 8px 0;
        font-family: var(--font-sans);
        font-weight: 500;
    }
    /* 側邊欄標題 */
    .sidebar-brand {
        font-family: var(--font-serif);
        font-size: 1.3rem;
        font-weight: 700;
        color: var(--text-primary);
        margin-bottom: 30px;
        letter-spacing: 1px;
    }

    /* 標題排版 (Typography) */
    h1 {
        font-family: var(--font-serif) !important;
        font-weight: 700 !important;
        color: var(--text-primary) !important;
        font-size: 2rem !important;
        letter-spacing: 0.5px;
        margin-bottom: 1.5rem !important;
    }
    h2, h3 {
        font-family: var(--font-sans) !important;
        font-weight: 500 !important;
        color: var(--text-primary) !important;
        letter-spacing: 0.5px;
    }
    h2 { font-size: 1.3rem !important; margin-top: 1.5rem !important; }
    h3 { font-size: 1.1rem !important; color: var(--text-secondary) !important; }
    
    p, label, .stMarkdown {
        color: var(--text-secondary);
        font-size: 0.9rem !important;
        line-height: 1.6;
        font-weight: 400;
    }

    /* 指標卡片 (Metric) - 極簡文字風 */
    div[data-testid="stMetric"] {
        background-color: #fff;
        padding: 10px 0;
        border-bottom: 1px solid var(--border-color);
    }
    div[data-testid="stMetricLabel"] {
        color: #999 !important;
        font-size: 0.8rem !important;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    div[data-testid="stMetricValue"] {
        color: var(--text-primary) !important;
        font-family: var(--font-serif) !important;
        font-size: 1.8rem !important;
        font-weight: 500;
    }

    /* 按鈕 - 極簡細線框 */
    div.stButton > button {
        background-color: transparent;
        color: var(--text-primary);
        border: 1px solid #DDDDDD;
        border-radius: 2px; /* 較直角 */
        font-size: 0.9rem;
        font-weight: 400;
        padding: 0.5rem 1.2rem;
        box-shadow: none;
        transition: all 0.3s ease;
        font-family: var(--font-sans);
    }
    div.stButton > button:hover {
        border-color: var(--text-primary);
        background-color: var(--text-primary);
        color: #fff;
    }
    
    /* 輸入框 - 乾淨無框感 */
    .stTextInput input, .stNumberInput input, .stSelectbox div[data-baseweb="select"] {
        border-radius: 2px;
        border: 1px solid #EEEEEE;
        background-color: #FAFAFA;
        color: var(--text-primary);
        font-size: 0.9rem;
        padding: 8px 12px;
    }
    .stTextInput input:focus {
        border-color: #999;
        background-color: #fff;
        box-shadow: none;
    }

    /* 雜誌風格列表卡片 */
    .magazine-card {
        border-bottom: 1px solid #F0F0F0;
        padding: 20px 0;
        display: flex;
        gap: 20px;
        align-items: center;
        transition: opacity 0.2s;
    }
    .magazine-card:hover {
        opacity: 0.8;
    }
    .magazine-img {
        width: 80px;
        height: 80px;
        background-color: #F5F5F5;
        object-fit: cover;
        flex-shrink: 0;
    }
    .magazine-content {
        flex-grow: 1;
        display: flex;
        flex-direction: column;
        justify-content: center;
    }
    .magazine-title {
        font-family: var(--font-sans);
        font-size: 1rem;
        font-weight: 600;
        color: var(--text-primary);
        margin-bottom: 4px;
    }
    .magazine-meta {
        font-family: var(--font-sans);
        font-size: 0.8rem;
        color: #888;
        display: flex;
        gap: 12px;
        margin-bottom: 2px;
        font-weight: 400;
    }
    .magazine-tag {
        border: 1px solid #EEE;
        padding: 1px 6px;
        border-radius: 2px;
        font-size: 0.75rem;
        color: #666;
    }
    .magazine-stock {
        font-family: var(--font-serif);
        font-size: 1.2rem;
        color: var(--text-primary);
        text-align: right;
        min-width: 60px;
        font-weight: 400;
    }
    .stock-label {
        font-size: 0.7rem;
        color: #AAA;
        text-transform: uppercase;
        display: block;
        text-align: right;
        letter-spacing: 1px;
    }

    /* Tab 樣式調整 */
    button[data-baseweb="tab"] {
        font-family: var(--font-sans);
        font-size: 0.9rem;
        font-weight: 400;
        color: #888;
        border-radius: 0;
        padding: 0 16px 8px 16px;
        border: none;
        background: transparent;
    }
    button[data-baseweb="tab"][aria-selected="true"] {
        color: var(--text-primary);
        border-bottom: 1px solid var(--text-primary);
        font-weight: 600;
    }
    div[data-baseweb="tab-list"] {
        gap: 16px;
        border-bottom: 1px solid #F0F0F0;
        margin-bottom: 24px;
    }
    
    /* 隱藏預設 Header 與 Footer */
    header {visibility: hidden;}
    footer {visibility: hidden;}
    
    .block-container {
        padding-top: 1rem;
        padding-bottom: 2rem;
    }
    
    hr {
        margin: 2rem 0;
        border: none;
        border-top: 1px solid #F0F0F0;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 4. 核心函數區 ---

def get_taiwan_time():
    tz = timezone(timedelta(hours=8))
    return datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")

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
        
        # [修復] 強制轉換日期格式，避免 data_editor 崩潰
        df["WarrantyStart"] = pd.to_datetime(df["WarrantyStart"], errors='coerce')
        df["WarrantyEnd"] = pd.to_datetime(df["WarrantyEnd"], errors='coerce')
        
        df["Stock"] = pd.to_numeric(df["Stock"], errors='coerce').fillna(0).astype(int)
        return df
    except Exception as e:
        st.error(f"資料讀取錯誤: {e}")
        return pd.DataFrame(columns=["SKU", "Code", "Category", "Number", "Name", "ImageFile", "Stock", "Location", "SN", "WarrantyStart", "WarrantyEnd"])

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
    
    # 日期處理
    if isinstance(ws, (datetime, pd.Timestamp, date)): ws = ws.strftime('%Y-%m-%d')
    elif hasattr(ws, "strftime"): ws = ws.strftime('%Y-%m-%d')
    if isinstance(we, (datetime, pd.Timestamp, date)): we = we.strftime('%Y-%m-%d')
    elif hasattr(we, "strftime"): we = we.strftime('%Y-%m-%d')

    if pd.isna(ws): ws = ""
    if pd.isna(we): we = ""

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
    return count

def upload_image_to_firebase(uploaded_file, sku, bucket_override=None):
    if uploaded_file is None: return None
    try:
        # 使用傳入的 bucket 或預設 bucket
        target_bucket = bucket_override if bucket_override else bucket
        
        safe_sku = "".join([c for c in sku if c.isalnum() or c in ('-','_')])
        file_ext = uploaded_file.name.split('.')[-1]
        blob_name = f"images/{safe_sku}-{int(time.time())}.{file_ext}"
        blob = target_bucket.blob(blob_name)
        blob.upload_from_file(uploaded_file, content_type=uploaded_file.type)
        blob.make_public()
        return blob.public_url
    except Exception as e:
        st.error(f"上傳失敗: {e}")
        st.caption("請檢查左側『連線診斷』確認 Bucket 名稱是否正確，或是否已啟用 Storage。")
        return None

# --- 5. 主程式介面 ---

def main():
    st.sidebar.markdown("<div class='sidebar-brand'>儀器耗材中控</div>", unsafe_allow_html=True)
    
    # === 🔧 連線診斷工具 (新增) ===
    with st.sidebar.expander("🔧 連線診斷"):
        st.caption("如果圖片上傳失敗，請在此測試。")
        
        # 讓使用者輸入從畫面上看到的名稱
        user_bucket_name = st.text_input("Bucket 名稱", value=CUSTOM_BUCKET_NAME, help="請輸入 gs:// 後面的文字")
        
        if st.button("測試連線"):
            try:
                test_bucket = storage.bucket(name=user_bucket_name)
                if test_bucket.exists():
                    st.success("✅ 連線成功！")
                    # 將測試成功的 bucket 暫存起來供本次使用
                    st.session_state['valid_bucket'] = test_bucket
                    st.session_state['valid_bucket_name'] = user_bucket_name
                else:
                    st.error("❌ 找不到此 Bucket")
                    st.info("請確認 Firebase Console > Storage 是否已點擊 'Get Started'。")
            except Exception as e:
                st.error(f"錯誤: {e}")
    # ===============================

    # 優先使用測試成功的 Bucket
    global bucket
    if 'valid_bucket' in st.session_state:
        bucket = st.session_state['valid_bucket']

    menu_options = [
        "總覽與查詢", 
        "入庫作業", 
        "出庫作業", 
        "資料維護",
        "異動紀錄"
    ]
    
    page = st.sidebar.radio("選單", menu_options, label_visibility="collapsed")

    if page == "總覽與查詢": page_search()
    elif page == "入庫作業": page_operation("入庫")
    elif page == "出庫作業": page_operation("出庫")
    elif page == "資料維護": page_maintenance()
    elif page == "異動紀錄": page_reports()

def render_magazine_card(row):
    """渲染雜誌風格列表項目 (HTML/CSS)"""
    img_url = row.get('ImageFile', '')
    has_img = img_url and str(img_url).startswith("http")
    
    img_tag = f'<img src="{img_url}" class="magazine-img">' if has_img else '<div class="magazine-img" style="display:flex;align-items:center;justify-content:center;color:#ccc;font-size:0.7rem;">無圖片</div>'
    
    stock = int(row['Stock'])
    # 文青風配色：正常為深黑，警示為暗紅
    stock_color = "#111" if stock > 5 else "#B91C1C" 
    
    loc = row['Location'] if row['Location'] else "-"
    sn = row['SN'] if row['SN'] else "-"
    
    html = f"""
    <div class="magazine-card">
        {img_tag}
        <div class="magazine-content">
            <div class="magazine-title">{row['Name']}</div>
            <div class="magazine-meta">
                <span class="magazine-tag">{row['SKU']}</span>
                <span>{row['Category']}</span>
            </div>
            <div class="magazine-meta">
                位置: {loc} &nbsp;|&nbsp; 序號: {sn}
            </div>
        </div>
        <div>
            <span class="stock-label">庫存</span>
            <div class="magazine-stock" style="color:{stock_color}">{stock}</div>
        </div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)

def page_search():
    st.title("總覽 Overview")
    df = load_data()
    
    c1, c2, c3 = st.columns(3)
    c1.metric("總品項", len(df))
    low_stock = len(df[df['Stock'] <= 5])
    c2.metric("低庫存", low_stock, delta="Alert" if low_stock > 0 else None, delta_color="inverse")
    c3.metric("總數量", int(df['Stock'].sum()))
    
    st.markdown("---")
    
    c_search, c_space = st.columns([2, 1])
    search_term = c_search.text_input("搜尋庫存", placeholder="輸入關鍵字 (名稱、SKU、地點)...")
    
    result = df
    if search_term:
        mask = df.astype(str).apply(lambda x: x.str.contains(search_term, case=False, na=False)).any(axis=1)
        result = df[mask]
    
    st.caption(f"找到 {len(result)} 筆資料")
    st.write("") 
    
    if result.empty:
        st.info("無符合資料")
    else:
        for index, row in result.iterrows():
            render_magazine_card(row)

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
        st.toast(f"成功！ {sku} 庫存: {new_stock}")
    else:
        st.error(f"找不到 SKU: {sku}")

def page_maintenance():
    st.title("資料維護")
    tabs = st.tabs(["新增項目", "編輯表格", "更換圖片", "匯入 CSV", "匯入圖片", "系統重置"])
    
    with tabs[0]: # 新增
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
                    st.success(f"新增成功: {sku}")
            else:
                st.error("Code 與 Name 為必填。")

    with tabs[1]: # 編輯
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
            st.success("已更新。"); time.sleep(1); st.rerun()

    with tabs[2]: # 換圖
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
                        st.success("圖片已更新。")
        else:
            st.info("無資料。")

    with tabs[3]: # CSV
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
                        
                        st.success("匯入完成。"); time.sleep(1); st.rerun()
                else:
                    st.error("無法讀取 CSV。")
            except Exception as e:
                st.error(f"錯誤: {e}")

    with tabs[4]: # 圖片批次
        st.caption("批次上傳 (檔名 = SKU)。")
        all_skus = [d.id for d in db.collection(COLLECTION_products).stream()]
        
        if not all_skus:
            st.warning("資料庫為空，請先匯入 CSV。")
        else:
            imgs = st.file_uploader("選擇多張圖片", type=["jpg", "png", "jpeg"], accept_multiple_files=True, key="multi_img_uploader")
            if imgs and st.button("開始上傳"):
                bar = st.progress(0); succ = 0; fail = 0
                
                for i, f in enumerate(imgs):
                    sku = f.name.rsplit('.', 1)[0].strip()
                    if sku in all_skus:
                        # 傳遞 bucket 物件
                        u = upload_image_to_firebase(f, sku)
                        if u:
                            db.collection(COLLECTION_products).document(sku).update({"imageFile": u})
                            succ += 1
                    else:
                        fail += 1
                    bar.progress((i+1)/len(imgs))
                
                st.success(f"完成。成功: {succ}, 跳過: {fail}")
                time.sleep(2)
                st.rerun()

    with tabs[5]: # 重置
        st.error("危險區域：永久刪除所有資料。")
        confirm = st.text_input("輸入 'DELETE' 確認刪除", key="delete_confirm")
        if st.button("清空資料庫"):
            if confirm == "DELETE":
                with st.spinner("刪除中..."): c = delete_all_products_logic()
                st.success(f"已刪除 {c} 筆資料。"); time.sleep(1); st.rerun()
            else: st.error("確認碼錯誤。")

def page_reports():
    st.title("異動紀錄")
    df = load_log()
    st.dataframe(df, use_container_width=True)
    st.download_button("下載 CSV", df.to_csv(index=False).encode('utf-8-sig'), "log.csv", "text/csv")

def generate_inventory_image(df_result):
    card_width, card_height, padding, header_height = 800, 220, 24, 100
    total_height = header_height + (len(df_result) * (card_height + padding)) + padding
    img = Image.new('RGB', (card_width + padding*2, total_height), color='#F4F6F8')
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, card_width + padding*2, header_height], fill='#2D3436')
    draw.text((padding, 35), f"INVENTORY REPORT - {datetime.now().strftime('%Y-%m-%d')}", fill='white')
    y_offset = header_height + padding
    for _, row in df_result.iterrows():
        draw.rectangle([padding, y_offset, padding + card_width, y_offset + card_height], fill='#FFFFFF', outline='#DFE6E9', width=2)
        text_x, text_y = padding + 220, y_offset + 35
        draw.text((text_x, text_y), f"{row['Name']}", fill='#2D3436')
        text_y += 35
        draw.text((text_x, text_y), f"SKU: {row['SKU']}", fill='#636E72')
        y_offset += card_height + padding
    return img

if __name__ == "__main__":
    main()
