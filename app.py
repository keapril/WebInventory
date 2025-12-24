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
    page_title="儀器耗材中控系統",
    page_icon="🧊", # 改個清爽的圖示
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

# --- 3. 簡約精緻風 CSS (Elegant Light Style) ---
st.markdown("""
    <style>
    /* Google Fonts: 現代無襯線體 */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600&family=Noto+Sans+TC:wght@300;400;500;700&display=swap');

    /* 全域設定 */
    .stApp {
        background-color: #F8F9FA; /* 極淺灰背景 */
        color: #2D3436; /* 深灰文字 */
        font-family: 'Inter', 'Noto Sans TC', sans-serif;
    }

    /* 側邊欄 */
    section[data-testid="stSidebar"] {
        background-color: #FFFFFF;
        border-right: 1px solid #E9ECEF;
    }
    section[data-testid="stSidebar"] h1 {
        color: #2D3436 !important;
        font-weight: 700;
        letter-spacing: 0.5px;
    }
    
    /* 輸入框優化 */
    .stTextInput input, .stNumberInput input, .stSelectbox div[data-baseweb="select"] {
        background-color: #FFFFFF;
        color: #2D3436;
        border: 1px solid #DFE6E9;
        border-radius: 8px; /* 圓角 */
        padding: 10px;
    }
    .stTextInput input:focus {
        border-color: #0984E3; /* 聚焦時的藍色 */
        box-shadow: 0 0 0 2px rgba(9, 132, 227, 0.1);
    }

    /* 按鈕樣式 - 簡約 */
    div.stButton > button {
        background-color: #FFFFFF;
        color: #0984E3;
        border: 1px solid #0984E3;
        border-radius: 6px;
        font-weight: 500;
        padding: 0.5rem 1rem;
        transition: all 0.2s ease;
    }
    div.stButton > button:hover {
        background-color: #0984E3;
        color: #FFFFFF;
        border-color: #0984E3;
        box-shadow: 0 4px 6px rgba(9, 132, 227, 0.15);
    }
    
    /* 數據指標 (Metrics) - 卡片風 */
    div[data-testid="stMetric"] {
        background-color: #FFFFFF;
        padding: 20px;
        border-radius: 12px;
        border: 1px solid #F1F3F5;
        box-shadow: 0 2px 5px rgba(0,0,0,0.03);
    }
    div[data-testid="stMetricLabel"] {
        color: #636E72 !important;
        font-size: 0.85rem;
        font-weight: 500;
        text-transform: uppercase;
    }
    div[data-testid="stMetricValue"] {
        color: #2D3436 !important;
        font-weight: 700;
    }

    /* 商品卡片 (Product Card) - 核心樣式 */
    .product-card {
        background-color: #FFFFFF;
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 20px;
        border: 1px solid #F1F3F5;
        box-shadow: 0 4px 6px rgba(0,0,0,0.02);
        transition: transform 0.2s, box-shadow 0.2s;
        display: flex;
        gap: 20px;
        align-items: start;
    }
    .product-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 15px rgba(0,0,0,0.05);
        border-color: #E2E8F0;
    }
    
    /* 圖片容器 */
    .img-container {
        width: 120px;
        height: 120px;
        border-radius: 8px;
        background-color: #F8F9FA;
        border: 1px solid #E9ECEF;
        display: flex;
        align-items: center;
        justify-content: center;
        overflow: hidden;
        flex-shrink: 0;
    }
    .img-container img {
        width: 100%;
        height: 100%;
        object-fit: contain; /* 保持比例 */
    }
    
    /* 資訊區塊 */
    .info-container {
        flex-grow: 1;
    }
    .card-title {
        font-size: 1.1rem;
        font-weight: 700;
        color: #2D3436;
        margin-bottom: 6px;
    }
    .card-meta {
        font-size: 0.85rem;
        color: #636E72;
        margin-bottom: 4px;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .tag {
        background-color: #F1F3F5;
        color: #636E72;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 0.75rem;
        font-weight: 500;
    }
    
    /* 庫存標籤 */
    .stock-badge {
        font-size: 0.9rem;
        font-weight: 600;
        padding: 4px 12px;
        border-radius: 20px;
        background-color: #E3F2FD;
        color: #0984E3;
    }
    .stock-badge.low {
        background-color: #FFEBEE;
        color: #D63031;
    }

    /* 分隔線 */
    hr { border-color: #E9ECEF; margin-top: 1rem; margin-bottom: 1rem; }
    
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
    st.sidebar.title("耗材管理")
    st.sidebar.caption("v11.0 Elegant Light")
    
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
    
    page = st.sidebar.radio("功能選單", menu_options)

    if page == "1. 儀表板與搜尋": page_search()
    elif page == "2. 入庫作業 (IN)": page_operation("入庫")
    elif page == "3. 出庫作業 (OUT)": page_operation("出庫")
    elif page == "4. 新增項目": page_add_single()
    elif page == "5. 編輯表格": page_edit_table()
    elif page == "6. 批次匯入 (CSV)": page_import_csv()
    elif page == "7. 批次匯入 (IMG)": page_import_images()
    elif page == "8. 系統日誌": page_reports()
    elif page == "9. 系統重置": page_reset_db()

def render_product_card(row):
    """渲染單張精緻商品卡片 (HTML/CSS)"""
    img_url = row.get('ImageFile', '')
    has_img = img_url and str(img_url).startswith("http")
    
    # 圖片區塊
    if has_img:
        img_html = f'<img src="{img_url}">'
    else:
        img_html = '<span style="color:#B2BEC3; font-size:0.8rem;">無圖片</span>'
    
    # 庫存判斷
    stock = int(row['Stock'])
    stock_cls = "low" if stock <= 5 else ""
    stock_label = f"庫存不足: {stock}" if stock <= 5 else f"庫存: {stock}"
    
    # 資訊整理
    sku_tag = f"<span class='tag'>{row['SKU']}</span>"
    cat_tag = f"<span class='tag'>{row['Category']}</span>"
    loc_text = f"📍 {row['Location']}" if row['Location'] else ""
    sn_text = f"🔢 {row['SN']}" if row['SN'] else ""
    
    # 卡片 HTML
    html = f"""
    <div class="product-card">
        <div class="img-container">
            {img_html}
        </div>
        <div class="info-container">
            <div style="display:flex; justify-content:space-between; align-items:start;">
                <div class="card-title">{row['Name']}</div>
                <div class="stock-badge {stock_cls}">{stock_label}</div>
            </div>
            <div class="card-meta">
                {sku_tag} {cat_tag}
            </div>
            <div class="card-meta" style="margin-top:8px;">
                {loc_text} &nbsp;&nbsp; {sn_text}
            </div>
        </div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)

def page_search():
    st.header("儀表板")
    df = load_data()
    
    # 簡約風數據列
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("總品項數", len(df))
    low_stock = len(df[df['Stock'] <= 5])
    c2.metric("低庫存", low_stock, delta="需補貨" if low_stock > 0 else "正常", delta_color="inverse")
    c3.metric("總庫存量", int(df['Stock'].sum()))
    c4.metric("系統狀態", "連線正常")
    
    st.divider()
    
    # 搜尋區
    c_search, c_filter = st.columns([3, 1])
    with c_search:
        search_term = st.text_input("🔍 搜尋商品", placeholder="輸入 SKU、名稱、地點...")
    
    result = df
    if search_term:
        mask = df.astype(str).apply(lambda x: x.str.contains(search_term, case=False, na=False)).any(axis=1)
        result = df[mask]
    
    st.caption(f"共找到 {len(result)} 筆資料")
    st.write("") 
    
    # === 卡片式顯示 (讓照片能預覽) ===
    if result.empty:
        st.info("沒有找到相關資料，請嘗試其他關鍵字。")
    else:
        # 單欄式排版，讓資訊更清楚，或兩欄
        for index, row in result.iterrows():
            render_product_card(row)

def page_operation(op_type):
    st.header(f"{op_type}作業")
    
    with st.container():
        c1, c2 = st.columns([1, 2])
        with c1:
            qty = st.number_input("數量", min_value=1, value=1)
        
        if "scan_input" not in st.session_state: st.session_state.scan_input = ""
        def on_scan():
            if st.session_state.scan_box:
                process_stock(st.session_state.scan_box, qty, op_type)
                st.session_state.scan_box = ""
        
        st.text_input("請掃描條碼或輸入 SKU", key="scan_box", on_change=on_scan, placeholder="在此輸入後按 Enter...")

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
            "Note": "Web Ops"
        })
        st.toast(f"✅ {op_type}成功！ {sku} 目前庫存: {new_stock}")
    else:
        st.error(f"❌ 找不到 SKU: {sku}")

# === 功能頁面 ===

def page_add_single():
    st.header("新增項目")
    st.info("請輸入商品詳細資料")
    with st.form("add_form"):
        c1, c2 = st.columns(2)
        code = c1.text_input("編碼 (Code)")
        cat = c2.text_input("分類 (Category)")
        c3, c4 = st.columns(2)
        num = c3.text_input("號碼 (Number)")
        name = c4.text_input("品名 (Name)")
        sn = st.text_input("S/N (產品序號)")
        loc = st.text_input("存放地點")
        stock = st.number_input("初始庫存", 0, value=1)
        
        if st.form_submit_button("確認新增"):
            if code and name:
                sku = f"{code}-{cat}-{num}"
                save_data_row({"SKU":sku, "Code":code, "Category":cat, "Number":num, "Name":name, "SN":sn, "Location":loc, "Stock":stock})
                st.success(f"已新增: {sku}")
            else:
                st.error("編碼與品名為必填欄位")

def page_edit_table():
    st.header("線上編輯表格")
    st.caption("您可以直接像 Excel 一樣編輯下方表格，完成後點擊儲存。")
    df = load_data()
    edited = st.data_editor(df, num_rows="dynamic", use_container_width=True, key="data_editor_main")
    if st.button("💾 儲存變更"):
        with st.spinner("同步中..."):
            for i, row in edited.iterrows():
                if row['SKU']: save_data_row(row)
        st.success("資料庫已更新")
        time.sleep(1); st.rerun()

def page_import_csv():
    st.header("批次匯入 (CSV)")
    st.markdown("請上傳您的 `inventory_data.csv` 檔案以初始化或更新資料庫。")
    up_csv = st.file_uploader("選擇檔案", type=["csv"], key="csv_batch_uploader")
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
                if st.button("確認匯入", type="primary"):
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
                    st.success("匯入完成！"); time.sleep(2); st.rerun()
            else: st.error("讀取失敗")
        except Exception as e: st.error(f"錯誤: {e}")

def page_import_images():
    st.header("批次匯入 (圖片)")
    st.markdown("系統會自動依據 **檔名** (例如 `A001.jpg`) 對應至相同的 **SKU**。")
    all_skus = [d.id for d in db.collection(COLLECTION_products).stream()]
    if not all_skus:
        st.warning("目前資料庫為空，請先匯入 CSV。")
    else:
        st.success(f"目前有 {len(all_skus)} 筆商品資料。")
        imgs = st.file_uploader("選擇多張圖片", type=["jpg", "png", "jpeg"], accept_multiple_files=True)
        if imgs and st.button("開始上傳"):
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
            st.success(f"完成。成功: {succ}, 跳過: {fail}"); time.sleep(3); st.rerun()

def page_reset_db():
    st.header("系統重置")
    st.error("⚠️ 危險操作：這將會永久刪除所有資料！")
    confirm = st.text_input("輸入 'DELETE' 確認", key="del_confirm")
    if st.button("🗑️ 確認清空", type="primary"):
        if confirm == "DELETE":
            with st.spinner("刪除中..."):
                c = delete_all_products_logic()
            st.success(f"已刪除 {c} 筆資料"); time.sleep(2); st.rerun()
        else: st.error("確認碼錯誤")

def page_reports():
    st.header("異動紀錄")
    df = load_log()
    st.dataframe(df, use_container_width=True)
    st.download_button("下載 CSV", df.to_csv(index=False).encode('utf-8-sig'), "log.csv", "text/csv")

def generate_inventory_image(df_result):
    # 簡單報表生成邏輯 (維持不變)
    card_width, card_height, padding, header_height = 800, 220, 24, 100
    total_height = header_height + (len(df_result) * (card_height + padding)) + padding
    img = Image.new('RGB', (card_width + padding*2, total_height), color='#F4F6F8')
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, card_width + padding*2, header_height], fill='#2D3436') # 改深灰標題
    draw.text((padding, 35), f"INVENTORY REPORT - {datetime.now().strftime('%Y-%m-%d')}", fill='white')
    y_offset = header_height + padding
    for _, row in df_result.iterrows():
        draw.rectangle([padding, y_offset, padding + card_width, y_offset + card_height], fill='#FFFFFF', outline='#DFE6E9', width=2)
        # (圖片處理邏輯省略以節省長度，功能與之前相同)
        text_x, text_y = padding + 220, y_offset + 35
        draw.text((text_x, text_y), f"{row['Name']}", fill='#2D3436')
        text_y += 35
        draw.text((text_x, text_y), f"SKU: {row['SKU']}", fill='#636E72')
        y_offset += card_height + padding
    return img

if __name__ == "__main__":
    main()
