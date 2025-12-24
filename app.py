# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import io
import json
import time
import requests
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime, timedelta, timezone

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
# 🔧【設定區】Bucket 名稱
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

# --- 3. SaaS / 雜誌風 CSS ---
st.markdown("""
    <style>
    /* 引入現代字體 Inter & Noto Sans TC */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&family=Noto+Sans+TC:wght@300;400;500;700&display=swap');

    /* 全域變數定義 */
    :root {
        --bg-color: #FFFFFF;
        --sidebar-bg: #FAFAFA;
        --text-primary: #111827;
        --text-secondary: #6B7280;
        --accent-color: #111827; /* 近乎黑色的深藍 */
        --border-color: #E5E7EB;
    }

    /* 基礎重置 */
    .stApp {
        background-color: var(--bg-color);
        color: var(--text-primary);
        font-family: 'Inter', 'Noto Sans TC', sans-serif;
    }

    /* 側邊欄優化 */
    section[data-testid="stSidebar"] {
        background-color: var(--sidebar-bg);
        border-right: 1px solid var(--border-color);
    }
    section[data-testid="stSidebar"] .stRadio label {
        color: var(--text-secondary);
        font-size: 0.85rem;
        padding: 8px 0;
    }
    section[data-testid="stSidebar"] h1 {
        font-size: 1rem !important;
        color: var(--text-primary) !important;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 1px;
    }

    /* 標題與文字排版 */
    h1, h2, h3 {
        color: var(--text-primary);
        font-family: 'Inter', sans-serif;
        letter-spacing: -0.02em;
    }
    h1 { font-size: 1.75rem !important; font-weight: 600; }
    h2 { font-size: 1.4rem !important; font-weight: 500; }
    h3 { font-size: 1.1rem !important; font-weight: 500; }
    
    p, label, .stMarkdown {
        color: var(--text-secondary);
        font-size: 0.9rem;
        line-height: 1.5;
    }

    /* 指標卡片 (Metric) - 極簡風 */
    div[data-testid="stMetric"] {
        background-color: #fff;
        padding: 0;
    }
    div[data-testid="stMetricLabel"] {
        color: var(--text-secondary) !important;
        font-size: 0.8rem !important;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    div[data-testid="stMetricValue"] {
        color: var(--text-primary) !important;
        font-size: 1.8rem !important;
        font-weight: 500;
    }

    /* 按鈕 - 雜誌風細線框 */
    div.stButton > button {
        background-color: transparent;
        color: var(--text-primary);
        border: 1px solid #D1D5DB;
        border-radius: 4px;
        font-size: 0.85rem;
        font-weight: 500;
        padding: 0.4rem 1rem;
        box-shadow: none;
        transition: all 0.2s ease;
    }
    div.stButton > button:hover {
        border-color: var(--text-primary);
        background-color: var(--text-primary);
        color: #fff;
    }
    div.stButton > button:active {
        transform: translateY(1px);
    }
    
    /* 輸入框 - 乾淨 */
    .stTextInput input, .stNumberInput input, .stSelectbox div[data-baseweb="select"] {
        border-radius: 4px;
        border: 1px solid #E5E7EB;
        background-color: #fff;
        color: var(--text-primary);
        font-size: 0.9rem;
    }
    .stTextInput input:focus {
        border-color: var(--text-primary);
        box-shadow: none;
    }

    /* 雜誌風格列表卡片 */
    .magazine-card {
        border-bottom: 1px solid #F3F4F6;
        padding: 24px 0;
        display: flex;
        gap: 24px;
        align-items: center;
    }
    .magazine-img {
        width: 100px;
        height: 100px;
        background-color: #F9FAFB;
        border-radius: 2px;
        object-fit: cover;
        flex-shrink: 0;
    }
    .magazine-content {
        flex-grow: 1;
    }
    .magazine-title {
        font-size: 1rem;
        font-weight: 600;
        color: var(--text-primary);
        margin-bottom: 4px;
    }
    .magazine-meta {
        font-size: 0.8rem;
        color: #9CA3AF;
        display: flex;
        gap: 12px;
        margin-bottom: 8px;
        font-family: 'Inter', monospace;
    }
    .magazine-tag {
        background: #F3F4F6;
        padding: 2px 6px;
        border-radius: 2px;
        color: #4B5563;
    }
    .magazine-stock {
        font-family: 'Inter', monospace;
        font-size: 0.9rem;
        color: var(--text-primary);
        text-align: right;
        min-width: 80px;
    }
    .stock-label {
        font-size: 0.7rem;
        color: #9CA3AF;
        text-transform: uppercase;
        display: block;
    }

    /* Tab 樣式調整 */
    button[data-baseweb="tab"] {
        font-size: 0.9rem;
        font-weight: 500;
        color: var(--text-secondary);
        border-radius: 0;
    }
    button[data-baseweb="tab"][aria-selected="true"] {
        color: var(--text-primary);
        background-color: transparent;
        border-bottom: 2px solid var(--text-primary);
    }
    
    /* 移除不必要的 Padding */
    .block-container {
        padding-top: 2rem;
        padding-bottom: 3rem;
    }
    
    hr {
        margin: 2rem 0;
        border: none;
        border-top: 1px solid #F3F4F6;
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
    if hasattr(ws, "strftime"): ws = ws.strftime('%Y-%m-%d')
    if hasattr(we, "strftime"): we = we.strftime('%Y-%m-%d')
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
        "warrantyStart": ws,
        "warrantyEnd": we,
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

def upload_image_to_firebase(uploaded_file, sku):
    if uploaded_file is None: return None
    try:
        safe_sku = "".join([c for c in sku if c.isalnum() or c in ('-','_')])
        file_ext = uploaded_file.name.split('.')[-1]
        blob_name = f"images/{safe_sku}-{int(time.time())}.{file_ext}"
        blob = bucket.blob(blob_name)
        blob.upload_from_file(uploaded_file, content_type=uploaded_file.type)
        blob.make_public()
        return blob.public_url
    except Exception as e:
        st.error(f"Upload failed: {e}")
        return None

# --- 5. 主程式介面 ---

def main():
    st.sidebar.title("Inventory OS")
    st.sidebar.caption("v12.0 SaaS Edition")
    
    # 簡化選單，將功能收納
    menu_options = [
        "Overview 總覽", 
        "Inbound 入庫", 
        "Outbound 出庫", 
        "Maintenance 資料維護",
        "Logs 紀錄"
    ]
    
    page = st.sidebar.radio("MENU", menu_options, label_visibility="collapsed")

    if "Overview" in page: page_search()
    elif "Inbound" in page: page_operation("入庫")
    elif "Outbound" in page: page_operation("出庫")
    elif "Maintenance" in page: page_maintenance()
    elif "Logs" in page: page_reports()

def render_magazine_card(row):
    """渲染雜誌風格列表項目 (HTML/CSS)"""
    img_url = row.get('ImageFile', '')
    has_img = img_url and str(img_url).startswith("http")
    
    # 圖片區塊
    img_tag = f'<img src="{img_url}" class="magazine-img">' if has_img else '<div class="magazine-img" style="display:flex;align-items:center;justify-content:center;color:#ccc;font-size:0.8rem;">No Img</div>'
    
    stock = int(row['Stock'])
    stock_color = "#111" if stock > 5 else "#EF4444" # 紅色警示
    
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
            <div class="magazine-meta" style="font-size:0.75rem;">
                Loc: {loc} &nbsp;|&nbsp; SN: {sn}
            </div>
        </div>
        <div>
            <span class="stock-label">Stock</span>
            <div class="magazine-stock" style="color:{stock_color}">{stock}</div>
        </div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)

def page_search():
    st.title("Overview")
    df = load_data()
    
    # 極簡數據列
    c1, c2, c3 = st.columns(3)
    c1.metric("Items", len(df))
    low_stock = len(df[df['Stock'] <= 5])
    c2.metric("Low Stock", low_stock, delta="Alert" if low_stock > 0 else None, delta_color="inverse")
    c3.metric("Total Qty", int(df['Stock'].sum()))
    
    st.markdown("---")
    
    # 搜尋
    c_search, c_space = st.columns([2, 1])
    search_term = c_search.text_input("Search", placeholder="Type keywords...")
    
    result = df
    if search_term:
        mask = df.astype(str).apply(lambda x: x.str.contains(search_term, case=False, na=False)).any(axis=1)
        result = df[mask]
    
    st.caption(f"{len(result)} items found")
    st.write("") 
    
    if result.empty:
        st.info("No data found.")
    else:
        for index, row in result.iterrows():
            render_magazine_card(row)

def page_operation(op_type):
    st.title(f"{op_type} Operation")
    st.caption("Scan barcode or type SKU to process.")
    
    c1, c2 = st.columns([1, 3])
    qty = c1.number_input("Quantity", min_value=1, value=1)
    
    if "scan_input" not in st.session_state: st.session_state.scan_input = ""
    def on_scan():
        if st.session_state.scan_box:
            process_stock(st.session_state.scan_box, qty, op_type)
            st.session_state.scan_box = ""
    
    st.text_input("SKU Input", key="scan_box", on_change=on_scan, placeholder="Focus here and scan...")

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
        st.toast(f"Success. {sku} New Stock: {new_stock}")
    else:
        st.error(f"SKU Not Found: {sku}")

# === 資料維護 (含所有功能分頁) ===

def page_maintenance():
    st.title("Data Maintenance")
    
    # 使用 Tabs 收納功能，這是最乾淨的 SAAS 作法
    tabs = st.tabs(["Add Item", "Edit Table", "Change Image", "Import CSV", "Import Images", "Reset"])
    
    # 1. 新增
    with tabs[0]:
        st.caption("Create a new inventory item.")
        with st.form("add_form", clear_on_submit=False):
            c1, c2 = st.columns(2)
            code = c1.text_input("Code")
            cat = c2.text_input("Category")
            c3, c4 = st.columns(2)
            num = c3.text_input("Number")
            name = c4.text_input("Name")
            c5, c6 = st.columns(2)
            sn = c5.text_input("Serial No.")
            loc = c6.text_input("Location")
            stock = st.number_input("Initial Stock", 0, value=1)
            
            if st.form_submit_button("Create Item"):
                if code and name:
                    sku = f"{code}-{cat}-{num}"
                    save_data_row({"SKU":sku, "Code":code, "Category":cat, "Number":num, "Name":name, "SN":sn, "Location":loc, "Stock":stock})
                    st.success(f"Item Created: {sku}")
                else:
                    st.error("Code & Name required.")

    # 2. 編輯
    with tabs[1]:
        st.caption("Double-click cells to edit directly.")
        df = load_data()
        edited = st.data_editor(df, num_rows="dynamic", use_container_width=True, key="data_editor_main")
        if st.button("Save Changes", type="primary"):
            with st.spinner("Saving..."):
                for i, row in edited.iterrows():
                    if row['SKU']: save_data_row(row)
            st.success("Database Updated.")
            time.sleep(1); st.rerun()

    # 3. 換圖
    with tabs[2]:
        st.caption("Update single image.")
        df_cur = load_data()
        if not df_cur.empty:
            sel = st.selectbox("Select Item", df_cur['SKU'].unique())
            if sel:
                row = df_cur[df_cur['SKU'] == sel].iloc[0]
                st.write(f"Selected: **{row['Name']}**")
                
                curr_img = row.get('ImageFile')
                if curr_img and str(curr_img).startswith('http'):
                    st.image(curr_img, width=150)
                
                f = st.file_uploader("Upload New Image", type=["jpg","png"], key="single_uploader")
                if f and st.button("Update Image"):
                    url = upload_image_to_firebase(f, sel)
                    if url:
                        db.collection(COLLECTION_products).document(sel).update({"imageFile": url})
                        st.success("Image Updated.")
        else:
            st.info("No items available.")

    # 4. CSV 匯入
    with tabs[3]:
        st.caption("Bulk import from CSV.")
        up_csv = st.file_uploader("Drop CSV file here", type=["csv"], key="csv_batch_uploader")
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
                    
                    if st.button("Run Import"):
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
                        
                        st.success("Import Finished.")
                        time.sleep(1)
                        st.rerun()
                else:
                    st.error("Cannot read CSV.")
            except Exception as e:
                st.error(f"Error: {e}")

    # 5. 圖片批次
    with tabs[4]:
        st.caption("Bulk upload images (Filename = SKU).")
        all_skus = [d.id for d in db.collection(COLLECTION_products).stream()]
        
        if not all_skus:
            st.warning("Database empty. Import CSV first.")
        else:
            imgs = st.file_uploader("Select images", type=["jpg", "png", "jpeg"], accept_multiple_files=True, key="multi_img_uploader")
            if imgs and st.button("Start Upload"):
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
                
                st.success(f"Done. Success: {succ}, Skipped: {fail}")
                time.sleep(2)
                st.rerun()

    # 6. 重置
    with tabs[5]:
        st.error("Danger Zone: This will delete ALL data.")
        confirm = st.text_input("Type 'DELETE' to confirm", key="delete_confirm")
        if st.button("Clear Database"):
            if confirm == "DELETE":
                with st.spinner("Deleting..."):
                    c = delete_all_products_logic()
                st.success(f"Deleted {c} items.")
                time.sleep(1)
                st.rerun()
            else:
                st.error("Invalid confirmation.")

def page_reports():
    st.title("System Logs")
    df = load_log()
    st.dataframe(df, use_container_width=True)
    st.download_button("Download CSV", df.to_csv(index=False).encode('utf-8-sig'), "log.csv", "text/csv")

if __name__ == "__main__":
    main()
