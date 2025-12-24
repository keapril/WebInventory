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
    page_title="儀器耗材管理系統",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. Firebase 初始化 (超級容錯版 - 核心代碼) ---
# 這裡就是您提到的「超級容錯」部分，能處理各種金鑰格式問題
if not firebase_admin._apps:
    try:
        # 1. 檢查 Secrets 是否存在
        if "firebase" not in st.secrets:
            st.error("❌ 錯誤：Streamlit Secrets 中找不到 [firebase] 區塊。")
            st.stop()
        
        # 2. 取得金鑰文字
        token_content = st.secrets["firebase"]["text_key"]
        
        # 3. 嘗試解析 JSON (第一道防線：strict=False)
        try:
            key_dict = json.loads(token_content, strict=False)
        except json.JSONDecodeError:
             # 4. 如果失敗，嘗試修復換行符號 (第二道防線)
            try:
                # 常見錯誤：複製時換行變成了真正的 Enter，導致 JSON 格式錯誤
                # 這裡嘗試將其修復回 \n
                key_dict = json.loads(token_content.replace('\n', '\\n'), strict=False)
            except:
                st.error("❌ JSON 解析嚴重失敗，請檢查 Secrets 格式是否缺損。")
                st.stop()

        # 5. 修復 private_key 欄位 (第三道防線)
        # Firebase Admin 需要真正的換行符號，而不是字串的 "\\n"
        if "private_key" in key_dict:
            key_dict["private_key"] = key_dict["private_key"].replace("\\n", "\n")

        # 6. 正式連線
        cred = credentials.Certificate(key_dict)
        project_id = key_dict.get('project_id')
        bucket_name = f"{project_id}.appspot.com"
        
        firebase_admin.initialize_app(cred, {
            'storageBucket': bucket_name
        })
    except Exception as e:
        st.error(f"Firebase 初始化失敗: {e}")
        st.stop()

db = firestore.client()
bucket = storage.bucket()

# --- 資料庫設定 (已隔離) ---
# 這是全新的資料表名稱，確保不影響您的 APP
COLLECTION_products = "instrument_consumables" 
COLLECTION_logs = "consumables_logs"

# --- 3. 自定義 CSS (保留您的原始設計) ---
st.markdown("""
    <style>
    /* 全站字體與背景 */
    @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700&display=swap');

    .stApp {
        background-color: #F4F6F8;
        color: #333333;
        font-family: 'Roboto', "Helvetica Neue", Helvetica, "PingFang TC", "Microsoft JhengHei", sans-serif;
    }

    /* 側邊欄 - 深藍色 */
    section[data-testid="stSidebar"] {
        background-color: #1A233A;
        color: #FFFFFF;
    }
    section[data-testid="stSidebar"] h1, 
    section[data-testid="stSidebar"] h2, 
    section[data-testid="stSidebar"] h3 {
        color: #FFFFFF !important;
        font-weight: 500;
        letter-spacing: 1px;
    }
    section[data-testid="stSidebar"] label,
    section[data-testid="stSidebar"] .stMarkdown,
    section[data-testid="stSidebar"] p {
        color: #AAB0C6 !important;
    }

    /* 標題樣式 */
    h1, h2, h3 {
        color: #1A233A;
        font-weight: 700;
    }

    /* === 數據卡片 === */
    .metric-card {
        background: #FFFFFF;
        border-radius: 8px;
        padding: 24px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
        border: 1px solid #E1E4E8;
        text-align: left;
    }
    .metric-label {
        color: #718096;
        font-size: 0.85rem;
        font-weight: 600;
        text-transform: uppercase;
        margin-bottom: 8px;
    }
    .metric-value {
        color: #1A233A;
        font-size: 2.25rem;
        font-weight: 700;
    }

    /* === 狀態標籤 === */
    .badge {
        display: inline-flex;
        align-items: center;
        padding: 4px 10px;
        border-radius: 4px;
        font-size: 0.75rem;
        font-weight: 600;
        margin-right: 8px;
        margin-bottom: 4px;
    }
    .badge-gray { background-color: #EDF2F7; color: #4A5568; }
    .badge-green { background-color: #C6F6D5; color: #22543D; }
    .badge-red { background-color: #FED7D7; color: #822727; }
    .badge-blue { background-color: #EBF8FF; color: #2C5282; }
    .badge-gold { background-color: #FEFCBF; color: #744210; }

    /* === 輸入框與按鈕 === */
    .stTextInput input, .stSelectbox div[data-baseweb="select"], .stNumberInput input, .stDateInput input {
        border-radius: 6px;
        border: 1px solid #CBD5E0;
    }
    div.stButton > button {
        background-color: #2B6CB0;
        color: white;
        border-radius: 6px;
        border: none;
        padding: 0.6rem 1.2rem;
        font-weight: 500;
    }
    div.stButton > button:hover {
        background-color: #2C5282;
    }

    /* Radio Button 優化 */
    .stRadio > div { flex-direction: column; gap: 8px; }
    .stRadio label {
        background-color: transparent;
        padding: 10px 12px;
        border-radius: 6px;
        color: #E2E8F0 !important;
        cursor: pointer;
    }
    .stRadio label:hover {
        background-color: #2D3748;
        color: #FFFFFF !important;
    }
    
    /* 表單區塊 */
    .form-section {
        background-color: #FFFFFF;
        padding: 24px;
        border-radius: 8px;
        border: 1px solid #E1E4E8;
        margin-bottom: 24px;
    }
    .form-title {
        font-size: 1.1rem;
        font-weight: 600;
        color: #2D3748;
        margin-bottom: 16px;
        border-bottom: 1px solid #EDF2F7;
        padding-bottom: 8px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 4. 核心函數區 (Firebase 版) ---

def get_taiwan_time():
    tz = timezone(timedelta(hours=8))
    return datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")

def load_data():
    """從 Firestore 讀取所有資料"""
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
        if not data:
            return pd.DataFrame(columns=default_cols)
            
        df = pd.DataFrame(data)
        # 補齊可能缺失的欄位
        for col in default_cols:
            if col not in df.columns:
                df[col] = ""
        
        # 日期轉換
        df["WarrantyStart"] = pd.to_datetime(df["WarrantyStart"], errors='coerce')
        df["WarrantyEnd"] = pd.to_datetime(df["WarrantyEnd"], errors='coerce')
        
        return df
    except Exception as e:
        st.error(f"資料讀取錯誤: {e}")
        return pd.DataFrame(columns=["SKU", "Code", "Category", "Number", "Name", "ImageFile", "Stock", "Location", "SN", "WarrantyStart", "WarrantyEnd"])

def load_log():
    """從 Firestore 讀取 Log"""
    try:
        docs = db.collection(COLLECTION_logs).order_by("timestamp", direction=firestore.Query.DESCENDING).limit(100).stream()
        data = []
        for doc in docs:
            data.append(doc.to_dict())
        if not data:
            return pd.DataFrame(columns=["Time", "User", "Type", "SKU", "Name", "Quantity", "Note"])
        return pd.DataFrame(data)
    except Exception:
        return pd.DataFrame(columns=["Time", "User", "Type", "SKU", "Name", "Quantity", "Note"])

def save_data_row(row_data):
    """更新或新增單筆資料到 Firestore"""
    # 處理日期轉字串
    ws = row_data.get("WarrantyStart")
    we = row_data.get("WarrantyEnd")
    
    if hasattr(ws, "strftime"): ws = ws.strftime('%Y-%m-%d')
    if hasattr(we, "strftime"): we = we.strftime('%Y-%m-%d')
    if pd.isna(ws): ws = ""
    if pd.isna(we): we = ""

    # 確保數值型別正確
    stock_val = row_data.get("Stock", 0)
    try:
        stock_val = int(stock_val)
    except:
        stock_val = 0

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
    """新增 Log 到 Firestore"""
    entry["timestamp"] = firestore.SERVER_TIMESTAMP # 用於排序
    db.collection(COLLECTION_logs).add(entry)

def delete_all_products_logic():
    """刪除所有產品資料 (批次刪除) - 修復 Empty Batch Error"""
    docs = db.collection(COLLECTION_products).stream()
    count = 0
    batch = db.batch()
    
    # 收集需要刪除的文件
    for doc in docs:
        batch.delete(doc.reference)
        count += 1
        # Firestore batch limit is 500
        if count % 400 == 0:
            batch.commit()
            batch = db.batch()
    
    # [修復] 只有當還有剩餘未提交的刪除操作時，才執行 commit
    if count > 0 and count % 400 != 0:
        batch.commit()
        
    return count

def upload_image_to_firebase(uploaded_file, sku):
    """上傳圖片到 Firebase Storage"""
    if uploaded_file is None:
        return None
    try:
        file_ext = uploaded_file.name.split('.')[-1]
        blob_name = f"images/{sku}-{int(time.time())}.{file_ext}"
        blob = bucket.blob(blob_name)
        blob.upload_from_file(uploaded_file, content_type=uploaded_file.type)
        blob.make_public()
        return blob.public_url
    except Exception as e:
        st.error(f"圖片上傳失敗: {e}")
        return None

# --- [圖片生成函數 (修正版：支援網址圖片)] ---
def generate_inventory_image(df_result):
    card_width = 800
    card_height = 220
    padding = 24
    header_height = 100
    
    total_height = header_height + (len(df_result) * (card_height + padding)) + padding
    img_width = card_width + (padding * 2)
    
    img = Image.new('RGB', (img_width, total_height), color='#F4F6F8')
    draw = ImageDraw.Draw(img)
    
    try:
        font_default = ImageFont.load_default()
    except:
        pass 
    
    # Header
    draw.rectangle([0, 0, img_width, header_height], fill='#1A233A')
    draw.text((padding, 35), f"INVENTORY REPORT - {datetime.now().strftime('%Y-%m-%d')}", fill='white')

    y_offset = header_height + padding
    
    for _, row in df_result.iterrows():
        # 卡片框
        draw.rectangle([padding, y_offset, padding + card_width, y_offset + card_height], fill='#FFFFFF')
        draw.rectangle([padding, y_offset, padding + card_width, y_offset + card_height], outline='#E1E4E8', width=1)
        
        # 圖片處理 (支援 Firebase URL)
        prod_img = None
        img_url = row.get('ImageFile', '')
        
        if img_url and isinstance(img_url, str) and img_url.startswith("http"):
            try:
                # 加大 timeout 避免圖片下載超時
                response = requests.get(img_url, timeout=5)
                if response.status_code == 200:
                    prod_img = Image.open(io.BytesIO(response.content)).convert('RGB')
            except:
                pass
        
        if prod_img:
            try:
                prod_img.thumbnail((160, 160))
                img.paste(prod_img, (padding + 30, y_offset + 30))
            except:
                pass
        else:
            draw.rectangle([padding + 30, y_offset + 30, padding + 190, y_offset + 190], fill='#EDF2F7')
            draw.text((padding + 80, y_offset + 100), "NO IMG", fill='#A0AEC0')

        # 文字
        text_x = padding + 220
        text_y = y_offset + 35
        
        draw.text((text_x, text_y), f"{row['Name']}", fill='#1A233A')
        text_y += 35
        
        draw.text((text_x, text_y), f"SKU: {row['SKU']} | CAT: {row['Category']}", fill='#718096')
        text_y += 30
        
        stock_val = row['Stock']
        stock_text = f"STOCK: {stock_val}"
        
        if stock_val <= 5:
            text_color = '#E53E3E' # Red
        else:
            text_color = '#38A169' # Green
            
        draw.text((text_x, text_y), stock_text, fill=text_color)
        text_y += 30
        
        if row['Location']:
            draw.text((text_x, text_y), f"LOC: {row['Location']}", fill='#3182CE')
            text_y += 30
            
        war_end_str = ""
        if pd.notna(row['WarrantyEnd']):
            war_end_str = row['WarrantyEnd'].strftime('%Y-%m-%d') if hasattr(row['WarrantyEnd'], 'strftime') else str(row['WarrantyEnd'])

        if row['SN'] or war_end_str:
            info = f"S/N: {row['SN']}  War: {war_end_str}"
            draw.text((text_x, text_y), info, fill='#D69E2E')

        y_offset += card_height + padding

    return img

# --- 5. 主程式介面 ---

def main():
    with st.sidebar:
        st.markdown("""
        <div style="margin-bottom: 24px;">
            <h2 style="color:white; margin:0; font-size:1.5rem;">庫存管理系統</h2>
            <p style="color:#AAB0C6; font-size: 0.85rem; margin-top:4px;">Cloud Enterprise Inventory</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.write("導航選單")
        page = st.radio("Navigation", [
            "總覽與查詢", 
            "入庫作業", 
            "出庫作業", 
            "資料維護", 
            "異動紀錄"
        ], label_visibility="collapsed")
        
        st.markdown("---")
        st.markdown("<div style='text-align: center; color: #4A5568; font-size: 0.8rem;'>Cloud v8.6 (Super Fault-Tolerant)</div>", unsafe_allow_html=True)

    # 頁面路由
    if page == "總覽與查詢":
        page_search()
    elif page == "入庫作業":
        page_operation("入庫")
    elif page == "出庫作業":
        page_operation("出庫")
    elif page == "資料維護":
        page_maintenance()
    elif page == "異動紀錄":
        page_reports()

# --- 各頁面子程式 ---

def page_search():
    st.markdown("### 📊 庫存總覽")
    df = load_data()
    
    # 數據看板
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">總品項數</div>
            <div class="metric-value">{len(df)}</div>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        low_stock = len(df[df['Stock'] <= 5])
        val_color = "#E53E3E" if low_stock > 0 else "#1A233A"
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">低庫存警示</div>
            <div class="metric-value" style="color:{val_color};">{low_stock}</div>
        </div>
        """, unsafe_allow_html=True)
    with c3:
        total_qty = df['Stock'].sum()
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">庫存總數量</div>
            <div class="metric-value">{total_qty}</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.write("")
    st.markdown("### 🔍 搜尋庫存")
    
    col_search, col_action = st.columns([3, 1])
    with col_search:
        search_term = st.text_input("輸入關鍵字", key="search_input", placeholder="搜尋 SKU / 品名 / 地點 / S/N...")
    
    if search_term:
        mask = df.astype(str).apply(lambda x: x.str.contains(search_term, case=False, na=False)).any(axis=1)
        result = df[mask]
    else:
        result = df
    
    with col_action:
        st.write("") 
        if st.button("匯出查詢結果圖", use_container_width=True):
            if result.empty:
                st.warning("沒有資料可生成圖片")
            else:
                with st.spinner("圖片生成中..."):
                    img = generate_inventory_image(result)
                    buf = io.BytesIO()
                    img.save(buf, format="PNG")
                    byte_im = buf.getvalue()
                    st.download_button(label="下載 PNG", data=byte_im, file_name="inventory_report.png", mime="image/png", use_container_width=True)

    st.write("")
    
    if not result.empty:
        st.caption(f"共找到 {len(result)} 筆資料")
        
        for _, row in result.iterrows():
            # 徽章準備
            badges = []
            if row['Stock'] <= 5: 
                badges.append(f"<span class='badge badge-red'>庫存低: {row['Stock']}</span>")
            else: 
                badges.append(f"<span class='badge badge-green'>庫存: {row['Stock']}</span>")
            
            if row['Location']: 
                badges.append(f"<span class='badge badge-blue'>地點: {row['Location']}</span>")
            
            if row['SN']: 
                badges.append(f"<span class='badge badge-gray'>S/N: {row['SN']}</span>")
            
            if pd.notna(row['WarrantyEnd']):
                try:
                    today = datetime.now()
                    if row['WarrantyEnd'] >= today:
                        days = (row['WarrantyEnd'] - today).days
                        badges.append(f"<span class='badge badge-gold'>保固內 ({days}天)</span>")
                    else:
                        badges.append(f"<span class='badge badge-red'>已過保</span>")
                except: pass
            
            badges_html = "".join(badges)

            # === 卡片顯示 ===
            with st.container():
                st.markdown(f"""
                <div style="background:white; border:1px solid #E1E4E8; border-radius:8px; padding:20px; margin-bottom:12px; box-shadow:0 1px 3px rgba(0,0,0,0.02);">
                    <div style="display:flex; gap:24px; align-items:start;">
                """, unsafe_allow_html=True)
                
                c_img, c_info = st.columns([1, 4])
                
                with c_img:
                    img_shown = False
                    img_url = row.get('ImageFile', '')
                    if img_url and isinstance(img_url, str) and img_url.startswith("http"):
                        st.image(img_url, use_container_width=True)
                        img_shown = True
                    
                    if not img_shown:
                        st.markdown('<div style="width:100%; height:100px; background:#EDF2F7; border-radius:6px; display:flex; align-items:center; justify-content:center; color:#A0AEC0; font-size:0.8rem;">NO IMAGE</div>', unsafe_allow_html=True)
                
                with c_info:
                    st.markdown(f"""
                        <div style="font-size:1.15rem; font-weight:600; color:#1A233A; margin-bottom:8px;">{row['Name']}</div>
                        <div style="margin-bottom:12px;">{badges_html}</div>
                        <div style="font-size:0.9rem; color:#718096; line-height:1.5;">
                            <span style="background:#F7FAFC; padding:2px 6px; border-radius:4px; border:1px solid #E2E8F0; font-family:monospace;">{row['SKU']}</span>
                            &nbsp; • &nbsp; {row['Category']} &nbsp; • &nbsp; {row['Number']}
                        </div>
                    """, unsafe_allow_html=True)
                
                st.markdown("</div></div>", unsafe_allow_html=True)
    else: 
        st.info("沒有找到相關資料。")

def page_operation(op_type):
    st.markdown(f"### {op_type}")
    
    if "scan_input" not in st.session_state: st.session_state.scan_input = ""
    
    with st.container():
        st.markdown("<div class='form-section'>", unsafe_allow_html=True)
        st.markdown(f"<div class='form-title'>執行{op_type}</div>", unsafe_allow_html=True)
        
        c1, c2 = st.columns([1, 2])
        with c1: qty = st.number_input("數量", min_value=1, value=1)
        
        def on_scan():
            if st.session_state.scan_box:
                process_stock(st.session_state.scan_box, qty, op_type)
                st.session_state.scan_box = ""
        
        st.text_input("請掃描條碼或輸入 SKU", key="scan_box", on_change=on_scan, placeholder="在此處掃描...")
        st.markdown("</div>", unsafe_allow_html=True)

def process_stock(sku, qty, op_type):
    # 使用 Transaction 或直接讀取更新 (此處為簡化版直接操作)
    doc_ref = db.collection(COLLECTION_products).document(sku)
    doc = doc_ref.get()
    
    if doc.exists:
        data = doc.to_dict()
        curr_stock = data.get('stock', 0)
        new_stock = curr_stock + qty if op_type == "入庫" else curr_stock - qty
        name = data.get('name', 'Unknown')
        
        # 更新庫存
        doc_ref.update({'stock': new_stock, 'updatedAt': firestore.SERVER_TIMESTAMP})
        
        # 寫入 Log
        save_log({
            "Time": get_taiwan_time(),
            "User": "Admin",
            "Type": op_type,
            "SKU": sku,
            "Name": name,
            "Quantity": qty,
            "Note": "App Operation"
        })
        
        st.toast(f"成功！{op_type} {qty} 個", icon="✅")
        st.success(f"已更新 **{name}** 庫存為: {new_stock}")
    else:
        st.error(f"找不到 SKU: {sku}")

def page_maintenance():
    st.markdown("### 資料維護")
    
    # [新增] Tab 5: 批次匯入(圖片)
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["新增項目", "編輯表格", "更換圖片", "批次匯入(CSV)", "批次匯入(圖片)", "資料庫重置"])
    
    # === Tab 1: 新增 ===
    with tab1:
        st.markdown("<div class='form-section'>", unsafe_allow_html=True)
        st.markdown("<div class='form-title'>1. 基本資料</div>", unsafe_allow_html=True)
        
        c1, c2 = st.columns(2)
        i_code = c1.text_input("編碼 (Code)")
        i_cat = c2.text_input("分類 (Category)")
        c3, c4 = st.columns(2)
        i_num = c3.text_input("號碼 (Number)")
        i_name = c4.text_input("品名 (Name)")
        
        st.markdown("<div class='form-title' style='margin-top:20px;'>2. 規格與保固 (選填)</div>", unsafe_allow_html=True)
        st.caption("若為耗材可略過此區塊")
        
        c_sn, c_war = st.columns(2)
        i_sn = c_sn.text_input("S/N (產品序號)")
        
        with c_war:
            enable_warranty = st.checkbox("設定保固日期?")
            if enable_warranty:
                cw1, cw2 = st.columns(2)
                i_w_start = cw1.date_input("保固開始日", value=datetime.today())
                i_w_end = cw2.date_input("保固結束日", value=datetime.today() + timedelta(days=365))
            else:
                i_w_start = None
                i_w_end = None
        
        st.markdown("<div class='form-title' style='margin-top:20px;'>3. 庫存與地點</div>", unsafe_allow_html=True)
        col_loc_main, col_loc_sub = st.columns([1, 2])
        main_loc = col_loc_main.selectbox("區域選擇", ["北", "中", "南", "高", "醫院"])
        
        hospital_name = ""
        with col_loc_sub:
            if main_loc == "醫院":
                hospital_name = st.text_input("輸入醫院名稱", placeholder="例如：台大")
            else:
                st.text_input("區域鎖定", value=main_loc, disabled=True)
        
        i_stock = st.number_input("初始庫存", 0, value=1)
        i_file = st.file_uploader("商品圖片", type=["jpg", "png"])
        
        st.write("")
        if st.button("確認新增", use_container_width=True):
            final_loc = f"醫院-{hospital_name}" if main_loc == "醫院" and hospital_name.strip() else main_loc
            if main_loc == "醫院" and not hospital_name.strip():
                st.error("請輸入醫院名稱")
                st.stop()

            # 自動生成 SKU
            sku = f"{i_code}-{i_cat}-{i_num}"
            
            if i_code and i_name:
                # 上傳圖片
                fname = ""
                if i_file:
                    with st.spinner("上傳圖片中..."):
                        fname = upload_image_to_firebase(i_file, sku)
                
                new_data = {
                    "SKU": sku, "Code": i_code, "Category": i_cat, "Number": i_num, 
                    "Name": i_name, "ImageFile": fname, "Stock": i_stock, 
                    "Location": final_loc, "SN": i_sn, 
                    "WarrantyStart": i_w_start, "WarrantyEnd": i_w_end
                }
                
                # 存入 Firestore
                save_data_row(new_data)
                st.success(f"新增成功: {sku}")
            else:
                st.error("編碼與品名為必填")
        st.markdown("</div>", unsafe_allow_html=True)

    # === Tab 2: 編輯表格 ===
    with tab2:
        df = load_data()
        
        # 準備地點下拉選單
        exist_locs = sorted([str(x) for x in df['Location'].unique() if pd.notna(x) and str(x).strip() != ""])
        all_locs = sorted(list(set(["北", "中", "南", "高"] + exist_locs)))

        col_cfg = {
            "SKU": st.column_config.TextColumn("SKU (不可改)", disabled=True),
            "Location": st.column_config.SelectboxColumn("地點", width="medium", options=all_locs),
            "WarrantyStart": st.column_config.DateColumn("保固開始", format="YYYY-MM-DD"),
            "WarrantyEnd": st.column_config.DateColumn("保固結束", format="YYYY-MM-DD"),
            "SN": st.column_config.TextColumn("S/N (序號)"),
            "ImageFile": st.column_config.TextColumn("圖片連結", disabled=True),
            "Stock": st.column_config.NumberColumn("庫存", min_value=0)
        }
        
        edited = st.data_editor(df, num_rows="dynamic", key="main_editor", use_container_width=True, column_config=col_cfg)
        
        if st.button("儲存表格變更"):
            # 逐筆更新 (因為 data_editor 回傳完整 dataframe)
            with st.spinner("正在同步至雲端..."):
                progress_bar = st.progress(0)
                total = len(edited)
                for i, row in edited.iterrows():
                    if row['SKU']: # 確保 SKU 存在
                        save_data_row(row)
                    progress_bar.progress((i + 1) / total)
            
            st.success("表格已更新至雲端！")
            time.sleep(1)
            st.rerun()

    # === Tab 3: 換圖 ===
    with tab3:
        df_cur = load_data()
        if not df_cur.empty:
            sel = st.selectbox("選擇商品更換圖片", df_cur['SKU'].unique())
            if sel:
                row = df_cur[df_cur['SKU'] == sel].iloc[0]
                st.write(f"目前商品：**{row['Name']}**")
                
                img_url = row.get('ImageFile', '')
                if img_url and str(img_url).startswith('http'):
                    st.image(img_url, width=200, caption="目前圖片")
                else:
                    st.info("目前無圖片")

                f = st.file_uploader("選擇新圖片", type=["jpg","png"])
                if f and st.button("上傳並更換"):
                    with st.spinner("上傳中..."):
                        fname = upload_image_to_firebase(f, sel)
                        if fname:
                            # 更新資料庫欄位
                            db.collection(COLLECTION_products).document(sel).update({"imageFile": fname})
                            st.success("圖片更新成功")
                            time.sleep(1)
                            st.rerun()
                            
    # === Tab 4: CSV Import ===
    with tab4:
        st.markdown("<div class='form-section'>", unsafe_allow_html=True)
        st.markdown("<div class='form-title'>批次匯入庫存資料</div>", unsafe_allow_html=True)
        st.info("📢 系統升級為雲端版後，不會自動讀取本機檔案。請在此上傳您原本的 `inventory_data.csv` 進行初始化。")
        
        uploaded_csv = st.file_uploader("上傳 CSV 檔", type=["csv"])
        
        if uploaded_csv:
            try:
                # [修復] 增強 CSV 讀取 (處理 BOM 與欄位空白)
                try:
                    df_import = pd.read_csv(uploaded_csv, encoding='utf-8-sig') # 優先嘗試 utf-8-sig 去除 BOM
                except:
                    uploaded_csv.seek(0)
                    df_import = pd.read_csv(uploaded_csv, encoding='big5') # 再試 big5
                
                # [修復] 標準化欄位名稱 (去除前後空白、轉小寫比對)
                df_import.columns = [c.strip() for c in df_import.columns]
                
                st.write(f"預覽資料 (共 {len(df_import)} 筆):")
                st.dataframe(df_import.head(5))
                
                if st.button("🚀 開始匯入資料至雲端", type="primary"):
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    total_rows = len(df_import)
                    
                    # 建立欄位映射 (Case Insensitive)
                    col_map = {c.lower(): c for c in df_import.columns}
                    
                    def get_val(key):
                        # 嘗試找 'SKU', 'sku', 'Sku' 等各種寫法
                        if key.lower() in col_map:
                            return row.get(col_map[key.lower()], '')
                        return ''

                    for i, row in df_import.iterrows():
                        # 確保 SKU 存在
                        sku = str(get_val('sku')).strip()
                        if not sku or sku.lower() == 'nan':
                            continue
                            
                        # 準備資料
                        row_data = {
                            "SKU": sku,
                            "Code": get_val('code'),
                            "Category": get_val('category'),
                            "Number": get_val('number'),
                            "Name": get_val('name'),
                            "ImageFile": get_val('imagefile'),
                            "Stock": get_val('stock'),
                            "Location": get_val('location'),
                            "SN": get_val('sn'),
                            "WarrantyStart": get_val('warrantystart'),
                            "WarrantyEnd": get_val('warrantyend')
                        }
                        
                        save_data_row(row_data)
                        
                        progress = (i + 1) / total_rows
                        progress_bar.progress(progress)
                        status_text.text(f"正在匯入: {row_data['Name']} ({i+1}/{total_rows})")
                    
                    st.success("✅ 匯入完成！所有資料已同步至雲端資料庫。")
                    time.sleep(2)
                    st.rerun()
                    
            except Exception as e:
                st.error(f"讀取 CSV 失敗: {e}")
                st.error("請檢查您的 CSV 檔案格式，建議使用 UTF-8 編碼。")
        st.markdown("</div>", unsafe_allow_html=True)

    # === Tab 5: 批次圖片匯入 ===
    with tab5:
        st.markdown("<div class='form-section'>", unsafe_allow_html=True)
        st.markdown("<div class='form-title'>批次圖片匯入</div>", unsafe_allow_html=True)
        st.info("💡 說明：上傳多張圖片，系統會自動根據「檔名」對應 SKU。例如：檔名為 `A001.jpg` 會自動存入 SKU 為 `A001` 的商品。")
        
        # 1. 先取得目前所有 SKU
        all_skus = set()
        # 這裡不快取，因為可能剛上傳 CSV
        try:
            docs = db.collection(COLLECTION_products).stream()
            for doc in docs:
                all_skus.add(doc.id)
        except:
            pass

        # 2. 檢查資料庫是否為空 (UX 優化)
        if not all_skus:
            st.error("⚠️ 警告：目前資料庫是空的！系統無法進行圖片對應。")
            st.warning("請先切換到【批次匯入(CSV)】分頁，上傳您的商品清單 `inventory_data.csv`。")
        else:
            st.success(f"目前資料庫共有 {len(all_skus)} 筆商品資料，準備就緒。")
            
            uploaded_imgs = st.file_uploader("選取多張圖片", type=["jpg", "png", "jpeg"], accept_multiple_files=True)
            
            if uploaded_imgs and st.button("開始批次上傳圖片"):
                progress_bar = st.progress(0)
                status_text = st.empty()
                total_files = len(uploaded_imgs)
                success_count = 0
                fail_count = 0
                
                for i, img_file in enumerate(uploaded_imgs):
                    # 取得檔名 (不含副檔名) 當作 SKU
                    sku_candidate = img_file.name.rsplit('.', 1)[0]
                    
                    status_text.text(f"正在處理: {img_file.name} -> SKU: {sku_candidate}")
                    
                    if sku_candidate in all_skus:
                        # 執行上傳
                        url = upload_image_to_firebase(img_file, sku_candidate)
                        if url:
                            # 更新資料庫
                            db.collection(COLLECTION_products).document(sku_candidate).update({"imageFile": url})
                            success_count += 1
                    else:
                        # 嘗試容錯 (例如檔名有空格)
                        sku_stripped = sku_candidate.strip()
                        if sku_stripped in all_skus:
                             url = upload_image_to_firebase(img_file, sku_stripped)
                             if url:
                                db.collection(COLLECTION_products).document(sku_stripped).update({"imageFile": url})
                                success_count += 1
                        else:
                            st.warning(f"跳過: 找不到 SKU '{sku_candidate}' 對應的商品資料")
                            fail_count += 1
                    
                    progress_bar.progress((i + 1) / total_files)
                
                st.success(f"處理完成！成功上傳: {success_count} 張，失敗/跳過: {fail_count} 張。")
                if success_count > 0:
                    time.sleep(2)
                    st.rerun()
                
        st.markdown("</div>", unsafe_allow_html=True)
        
    # === Tab 6: Reset ===
    with tab6:
        st.markdown("<div class='form-section'>", unsafe_allow_html=True)
        st.markdown("<div class='form-title' style='color:#E53E3E;'>⚠️ 危險區域：清空資料庫</div>", unsafe_allow_html=True)
        st.warning("此操作將會 **永久刪除** 所有庫存商品資料 (products)，無法復原！(Log 紀錄會保留)")
        
        confirm_text = st.text_input("請輸入 'DELETE' 以確認執行刪除", placeholder="在此輸入...")
        
        if st.button("🗑️ 確認清空所有資料", type="primary"):
            if confirm_text == "DELETE":
                try:
                    with st.spinner("正在刪除所有資料..."):
                        count = delete_all_products_logic()
                    st.success(f"已清空資料庫！共刪除 {count} 筆資料。")
                    time.sleep(2)
                    st.rerun()
                except Exception as e:
                    st.error(f"刪除失敗: {e}")
                    st.caption("建議檢查 Firebase 權限或稍後再試。")
            else:
                st.error("確認碼錯誤，請輸入 'DELETE'。")
        st.markdown("</div>", unsafe_allow_html=True)

def page_reports():
    st.markdown("### 📋 異動紀錄")
    df = load_log()
    if not df.empty:
        # 轉換 Timestamp 物件為字串以利顯示
        if 'timestamp' in df.columns:
            df['timestamp'] = df['timestamp'].apply(lambda x: x.strftime('%Y-%m-%d %H:%M:%S') if hasattr(x, 'strftime') else x)
        
        # 調整欄位順序
        cols = ["Time", "User", "Type", "SKU", "Name", "Quantity", "Note"]
        # 確保欄位存在
        for c in cols:
            if c not in df.columns: df[c] = ""
            
        st.dataframe(df[cols], use_container_width=True)
        st.download_button("下載 CSV", df.to_csv(index=False).encode('utf-8-sig'), "log.csv", "text/csv")
    else: 
        st.info("目前無紀錄")

if __name__ == "__main__":
    main()
