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
    page_title="儀器耗材中控系統", # 改個更有科技感的名字
    page_icon="🧬",
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
            st.error("❌ 系統錯誤：找不到 Firebase 金鑰配置。")
            st.stop()
        
        token_content = st.secrets["firebase"]["text_key"]
        try:
            key_dict = json.loads(token_content, strict=False)
        except json.JSONDecodeError:
            try:
                key_dict = json.loads(token_content.replace('\n', '\\n'), strict=False)
            except:
                st.error("❌ 系統錯誤：金鑰解析失敗。")
                st.stop()

        if "private_key" in key_dict:
            key_dict["private_key"] = key_dict["private_key"].replace("\\n", "\n")

        cred = credentials.Certificate(key_dict)
        
        if CUSTOM_BUCKET_NAME:
            bucket_name = CUSTOM_BUCKET_NAME
        else:
            project_id = key_dict.get('project_id')
            bucket_name = f"{project_id}.appspot.com"
        
        firebase_admin.initialize_app(cred, {
            'storageBucket': bucket_name
        })
    except Exception as e:
        st.error(f"連線失敗: {e}")
        st.stop()

db = firestore.client()
bucket = storage.bucket()

COLLECTION_products = "instrument_consumables" 
COLLECTION_logs = "consumables_logs"

# --- 3. 科技感 CSS (Tech / Cyberpunk Style) ---
st.markdown("""
    <style>
    /* Google Fonts: 科技感字體 */
    @import url('https://fonts.googleapis.com/css2?family=Rajdhani:wght@400;600;700&family=Roboto+Mono:wght@400;500&display=swap');

    /* 全域背景 - 深空灰/黑 */
    .stApp {
        background-color: #0b0c10;
        color: #c5c6c7;
        font-family: 'Rajdhani', 'Microsoft JhengHei', sans-serif;
    }

    /* 側邊欄 */
    section[data-testid="stSidebar"] {
        background-color: #1f2833;
        border-right: 1px solid #45a29e;
    }
    section[data-testid="stSidebar"] h1 {
        color: #66fcf1 !important; /* 螢光青 */
        text-shadow: 0 0 5px #45a29e;
        letter-spacing: 2px;
    }
    
    /* 輸入框與按鈕優化 */
    .stTextInput input, .stNumberInput input, .stSelectbox div[data-baseweb="select"] {
        background-color: #1f2833;
        color: #66fcf1;
        border: 1px solid #45a29e;
        border-radius: 4px;
    }
    .stTextInput input:focus {
        border-color: #66fcf1;
        box-shadow: 0 0 8px #66fcf1;
    }

    /* 按鈕樣式 - 霓虹風格 */
    div.stButton > button {
        background-color: transparent;
        color: #66fcf1;
        border: 1px solid #66fcf1;
        border-radius: 4px;
        transition: all 0.3s ease;
        font-family: 'Roboto Mono', monospace;
        font-weight: bold;
    }
    div.stButton > button:hover {
        background-color: #66fcf1;
        color: #0b0c10;
        box-shadow: 0 0 10px #66fcf1;
    }
    
    /* 數據指標 (Metrics) - HUD 風格 */
    div[data-testid="stMetric"] {
        background-color: #1f2833;
        padding: 15px;
        border-radius: 6px;
        border-left: 4px solid #66fcf1;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }
    div[data-testid="stMetricLabel"] {
        color: #45a29e !important;
        font-family: 'Roboto Mono', monospace;
        font-size: 0.9rem;
    }
    div[data-testid="stMetricValue"] {
        color: #ffffff !important;
        text-shadow: 0 0 5px #ffffff;
        font-family: 'Rajdhani', sans-serif;
    }

    /* 資訊卡片 (Tech Card) */
    .tech-card {
        background-color: #1f2833;
        border: 1px solid #2c3e50;
        border-radius: 8px;
        padding: 0;
        margin-bottom: 20px;
        overflow: hidden;
        transition: transform 0.2s;
        box-shadow: 0 4px 10px rgba(0,0,0,0.5);
    }
    .tech-card:hover {
        border-color: #66fcf1;
        transform: translateY(-2px);
    }
    .tech-card-header {
        background: linear-gradient(90deg, #45a29e 0%, #1f2833 100%);
        padding: 8px 12px;
        color: #0b0c10;
        font-weight: bold;
        font-family: 'Roboto Mono', monospace;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .tech-card-body {
        padding: 15px;
        display: flex;
        gap: 15px;
    }
    .tech-img-box {
        width: 100px;
        height: 100px;
        background-color: #0b0c10;
        border: 1px solid #45a29e;
        display: flex;
        align-items: center;
        justify-content: center;
        border-radius: 4px;
        overflow: hidden;
        flex-shrink: 0;
    }
    .tech-img-box img {
        width: 100%;
        height: 100%;
        object-fit: cover;
    }
    .tech-info {
        flex-grow: 1;
        color: #c5c6c7;
    }
    .tech-title {
        font-size: 1.1rem;
        font-weight: 700;
        color: #ffffff;
        margin-bottom: 5px;
    }
    .tech-detail {
        font-size: 0.85rem;
        color: #45a29e;
        font-family: 'Roboto Mono', monospace;
        margin-bottom: 3px;
    }
    .tech-stock {
        font-size: 1.2rem;
        font-weight: bold;
        color: #66fcf1;
        text-align: right;
    }
    .stock-label {
        font-size: 0.7rem;
        color: #888;
        text-transform: uppercase;
    }
    
    /* 分隔線 */
    hr { border-color: #45a29e; opacity: 0.3; }
    
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
        # 確保數值型別
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
        st.error(f"上傳失敗: {e}")
        return None

# --- 5. 主程式介面 ---

def main():
    st.sidebar.title("INVENTORY SYS")
    st.sidebar.caption("v10.0 Tech Edition")
    
    menu_options = [
        "1. 儀表板與搜尋", 
        "2. 入庫作業 (IN)", 
        "3. 出庫作業 (OUT)", 
        "4. 新增項目",
        "5. 編輯表格",
        "6. 批次匯入 (CSV)",
        "7. 批次匯入 (IMG)",
        "8. 系統日誌",
        "9. 系統重置"
    ]
    
    page = st.sidebar.radio("SYSTEM MENU", menu_options)

    if page == "1. 儀表板與搜尋": page_search()
    elif page == "2. 入庫作業 (IN)": page_operation("入庫")
    elif page == "3. 出庫作業 (OUT)": page_operation("出庫")
    elif page == "4. 新增項目": page_add_single()
    elif page == "5. 編輯表格": page_edit_table()
    elif page == "6. 批次匯入 (CSV)": page_import_csv()
    elif page == "7. 批次匯入 (IMG)": page_import_images()
    elif page == "8. 系統日誌": page_reports()
    elif page == "9. 系統重置": page_reset_db()

def render_tech_card(row):
    """渲染單張科技感卡片 (HTML/CSS)"""
    img_url = row.get('ImageFile', '')
    has_img = img_url and str(img_url).startswith("http")
    
    # 圖片區塊
    if has_img:
        img_html = f'<img src="{img_url}">'
    else:
        img_html = '<span style="color:#45a29e; font-size:0.8rem;">NO SIGNAL</span>'
    
    # 庫存顏色
    stock = int(row['Stock'])
    stock_color = "#66fcf1" if stock > 5 else "#e74c3c" # 紅色警告
    
    # 卡片 HTML
    html = f"""
    <div class="tech-card">
        <div class="tech-card-header">
            <span>{row['SKU']}</span>
            <span style="font-size:0.8rem; opacity:0.8;">{row['Category']}</span>
        </div>
        <div class="tech-card-body">
            <div class="tech-img-box">
                {img_html}
            </div>
            <div class="tech-info">
                <div class="tech-title">{row['Name']}</div>
                <div class="tech-detail">LOC: {row['Location']}</div>
                <div class="tech-detail">S/N: {row['SN']}</div>
            </div>
            <div style="display:flex; flex-direction:column; justify-content:center; align-items:end;">
                <span class="stock-label">QTY</span>
                <span class="tech-stock" style="color:{stock_color}">{stock}</span>
            </div>
        </div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)

def page_search():
    st.title("DASHBOARD // 儀表板")
    df = load_data()
    
    # 頂部數據列
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("TOTAL ITEMS", len(df))
    low_stock = len(df[df['Stock'] <= 5])
    c2.metric("LOW STOCK", low_stock, delta="Alert" if low_stock > 0 else "Normal", delta_color="inverse")
    c3.metric("TOTAL QUANTITY", int(df['Stock'].sum()))
    c4.metric("SYSTEM STATUS", "ONLINE", delta="Stable")
    
    st.markdown("---")
    
    # 搜尋區
    st.subheader("SEARCH MODULE // 資料檢索")
    search_term = st.text_input("INPUT KEYWORD", placeholder="SKU / Name / Location...")
    
    result = df
    if search_term:
        mask = df.astype(str).apply(lambda x: x.str.contains(search_term, case=False, na=False)).any(axis=1)
        result = df[mask]
    
    st.caption(f"FOUND: {len(result)} ITEMS")
    st.write("") # Spacer
    
    # === 卡片式顯示 (解決照片預覽問題) ===
    if result.empty:
        st.info("NO DATA FOUND")
    else:
        # 兩欄式排版
        cols = st.columns(2)
        for i, (index, row) in enumerate(result.iterrows()):
            with cols[i % 2]:
                render_tech_card(row)

def page_operation(op_type):
    st.title(f"OPERATION // {op_type}")
    
    c1, c2 = st.columns([1, 2])
    with c1:
        qty = st.number_input("QUANTITY", min_value=1, value=1)
    
    if "scan_input" not in st.session_state: st.session_state.scan_input = ""
    def on_scan():
        if st.session_state.scan_box:
            process_stock(st.session_state.scan_box, qty, op_type)
            st.session_state.scan_box = ""
    
    st.text_input("SCAN BARCODE / SKU", key="scan_box", on_change=on_scan)
    st.caption("Press Enter to Execute")

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
            "Note": "TechUI Ops"
        })
        st.toast(f"✅ EXECUTION SUCCESS! {sku} QTY: {new_stock}")
    else:
        st.error(f"❌ INVALID SKU: {sku}")

# === 功能頁面 (維持扁平化選單) ===

def page_add_single():
    st.header("DATA ENTRY // 新增項目")
    with st.form("add_form"):
        c1, c2 = st.columns(2)
        code = c1.text_input("CODE")
        cat = c2.text_input("CATEGORY")
        c3, c4 = st.columns(2)
        num = c3.text_input("NUMBER")
        name = c4.text_input("NAME")
        sn = st.text_input("SERIAL NO.")
        loc = st.text_input("LOCATION")
        stock = st.number_input("INITIAL STOCK", 0, value=1)
        
        if st.form_submit_button("SUBMIT DATA"):
            if code and name:
                sku = f"{code}-{cat}-{num}"
                save_data_row({"SKU":sku, "Code":code, "Category":cat, "Number":num, "Name":name, "SN":sn, "Location":loc, "Stock":stock})
                st.success(f"ENTRY ADDED: {sku}")
            else:
                st.error("MISSING REQUIRED FIELDS")

def page_edit_table():
    st.header("DATABASE EDITOR // 線上編輯")
    df = load_data()
    # 使用原生 Editor，但配合 Dark Mode CSS 其實也很搭
    edited = st.data_editor(df, num_rows="dynamic", use_container_width=True, key="data_editor_main")
    if st.button("SAVE CHANGES"):
        with st.spinner("SYNCHRONIZING..."):
            for i, row in edited.iterrows():
                if row['SKU']: save_data_row(row)
        st.success("DATABASE UPDATED")
        time.sleep(1); st.rerun()

def page_import_csv():
    st.header("BATCH IMPORT // CSV")
    st.info("Upload `inventory_data.csv` to initialize database.")
    up_csv = st.file_uploader("SELECT FILE", type=["csv"], key="csv_batch_uploader")
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
                st.dataframe(df_im.head())
                if st.button("EXECUTE IMPORT", type="primary"):
                    progress_bar = st.progress(0)
                    col_map = {c.lower(): c for c in df_im.columns}
                    def get_val(r, k): return r.get(col_map.get(k.lower()), '')
                    for i, row in df_im.iterrows():
                        sku = str(get_val(row, 'sku')).strip()
                        if sku and sku.lower() != 'nan':
                            save_data_row({
                                "SKU": sku, "Code": get_val(row,'code'), "Category": get_val(row,'category'),
                                "Number": get_val(row,'number'), "Name": get_val(row,'name'), "ImageFile": get_val(row,'imagefile'),
                                "Stock": get_val(row,'stock'), "Location": get_val(row,'location'), "SN": get_val(row,'sn'),
                                "WarrantyStart": get_val(row,'warrantystart'), "WarrantyEnd": get_val(row,'warrantyend')
                            })
                        progress_bar.progress((i+1)/len(df_im))
                    st.success("IMPORT COMPLETE"); time.sleep(2); st.rerun()
            else: st.error("READ ERROR")
        except Exception as e: st.error(f"ERROR: {e}")

def page_import_images():
    st.header("BATCH IMPORT // IMAGES")
    st.info("Upload images matching SKU names (e.g., A001.jpg).")
    all_skus = [d.id for d in db.collection(COLLECTION_products).stream()]
    if not all_skus:
        st.warning("DATABASE EMPTY. IMPORT CSV FIRST.")
    else:
        st.success(f"TARGETS IDENTIFIED: {len(all_skus)}")
        imgs = st.file_uploader("SELECT IMAGES", type=["jpg", "png", "jpeg"], accept_multiple_files=True)
        if imgs and st.button("INITIATE UPLOAD"):
            bar = st.progress(0); succ = 0; fail = 0
            for i, f in enumerate(imgs):
                sku = f.name.rsplit('.', 1)[0].strip()
                if sku in all_skus:
                    u = upload_image_to_firebase(f, sku)
                    if u:
                        db.collection(COLLECTION_products).document(sku).update({"imageFile": u})
                        succ += 1
                else: fail += 1
                bar.progress((i+1)/len(imgs))
            st.success(f"UPLOAD COMPLETE. SUCCESS: {succ}, SKIPPED: {fail}"); time.sleep(3); st.rerun()

def page_reset_db():
    st.header("DANGER ZONE // 系統重置")
    st.error("WARNING: DATA WILL BE PERMANENTLY DELETED.")
    confirm = st.text_input("TYPE 'DELETE' TO CONFIRM")
    if st.button("NUKE DATABASE", type="primary"):
        if confirm == "DELETE":
            with st.spinner("DELETING..."):
                c = delete_all_products_logic()
            st.success(f"SYSTEM PURGED. DELETED {c} RECORDS."); time.sleep(2); st.rerun()
        else: st.error("INVALID CONFIRMATION CODE")

def page_reports():
    st.header("SYSTEM LOGS // 異動紀錄")
    df = load_log()
    st.dataframe(df, use_container_width=True)
    st.download_button("EXPORT LOGS (CSV)", df.to_csv(index=False).encode('utf-8-sig'), "log.csv", "text/csv")

if __name__ == "__main__":
    main()
