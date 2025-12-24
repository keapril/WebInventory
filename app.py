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

# --- 2. Firebase 初始化 (超級容錯版) ---
if not firebase_admin._apps:
    try:
        if "firebase" not in st.secrets:
            st.error("❌ 錯誤：Streamlit Secrets 中找不到 [firebase] 區塊。")
            st.stop()
        
        token_content = st.secrets["firebase"]["text_key"]
        try:
            key_dict = json.loads(token_content, strict=False)
        except json.JSONDecodeError:
            try:
                key_dict = json.loads(token_content.replace('\n', '\\n'), strict=False)
            except:
                st.error("❌ JSON 解析嚴重失敗，請檢查 Secrets 格式是否缺損。")
                st.stop()

        if "private_key" in key_dict:
            key_dict["private_key"] = key_dict["private_key"].replace("\\n", "\n")

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

# --- 資料庫設定 ---
COLLECTION_products = "instrument_consumables" 
COLLECTION_logs = "consumables_logs"

# --- 3. 自定義 CSS ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700&display=swap');
    .stApp { background-color: #F4F6F8; color: #333333; font-family: 'Roboto', sans-serif; }
    section[data-testid="stSidebar"] { background-color: #1A233A; color: #FFFFFF; }
    section[data-testid="stSidebar"] p, section[data-testid="stSidebar"] label { color: #AAB0C6 !important; }
    h1, h2, h3 { color: #1A233A; font-weight: 700; }
    .metric-card { background: #FFFFFF; border-radius: 8px; padding: 24px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); border: 1px solid #E1E4E8; }
    .metric-label { color: #718096; font-size: 0.85rem; font-weight: 600; }
    .metric-value { color: #1A233A; font-size: 2.25rem; font-weight: 700; }
    .badge { display: inline-flex; align-items: center; padding: 4px 10px; border-radius: 4px; font-size: 0.75rem; font-weight: 600; margin-right: 8px; margin-bottom: 4px; }
    .badge-gray { background-color: #EDF2F7; color: #4A5568; }
    .badge-green { background-color: #C6F6D5; color: #22543D; }
    .badge-red { background-color: #FED7D7; color: #822727; }
    .badge-blue { background-color: #EBF8FF; color: #2C5282; }
    .badge-gold { background-color: #FEFCBF; color: #744210; }
    .stTextInput input, .stSelectbox div[data-baseweb="select"], .stNumberInput input { border-radius: 6px; border: 1px solid #CBD5E0; }
    div.stButton > button { background-color: #2B6CB0; color: white; border-radius: 6px; border: none; padding: 0.6rem 1.2rem; font-weight: 500; }
    div.stButton > button:hover { background-color: #2C5282; }
    
    /* 移除可能會蓋住元件的 form-section 設定，改用簡單樣式 */
    .simple-card { background-color: #FFFFFF; padding: 20px; border-radius: 8px; border: 1px solid #E1E4E8; margin-bottom: 20px; }
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
        df["WarrantyStart"] = pd.to_datetime(df["WarrantyStart"], errors='coerce')
        df["WarrantyEnd"] = pd.to_datetime(df["WarrantyEnd"], errors='coerce')
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
        file_ext = uploaded_file.name.split('.')[-1]
        blob_name = f"images/{sku}-{int(time.time())}.{file_ext}"
        blob = bucket.blob(blob_name)
        blob.upload_from_file(uploaded_file, content_type=uploaded_file.type)
        blob.make_public()
        return blob.public_url
    except Exception as e:
        st.error(f"圖片上傳失敗: {e}")
        return None

def generate_inventory_image(df_result):
    card_width, card_height, padding, header_height = 800, 220, 24, 100
    total_height = header_height + (len(df_result) * (card_height + padding)) + padding
    img = Image.new('RGB', (card_width + padding*2, total_height), color='#F4F6F8')
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, card_width + padding*2, header_height], fill='#1A233A')
    draw.text((padding, 35), f"INVENTORY REPORT - {datetime.now().strftime('%Y-%m-%d')}", fill='white')
    y_offset = header_height + padding
    for _, row in df_result.iterrows():
        draw.rectangle([padding, y_offset, padding + card_width, y_offset + card_height], fill='#FFFFFF', outline='#E1E4E8', width=1)
        prod_img = None
        img_url = row.get('ImageFile', '')
        if img_url and isinstance(img_url, str) and img_url.startswith("http"):
            try:
                response = requests.get(img_url, timeout=5)
                if response.status_code == 200: prod_img = Image.open(io.BytesIO(response.content)).convert('RGB')
            except: pass
        if prod_img:
            try:
                prod_img.thumbnail((160, 160))
                img.paste(prod_img, (padding + 30, y_offset + 30))
            except: pass
        else:
            draw.rectangle([padding + 30, y_offset + 30, padding + 190, y_offset + 190], fill='#EDF2F7')
            draw.text((padding + 80, y_offset + 100), "NO IMG", fill='#A0AEC0')
        text_x, text_y = padding + 220, y_offset + 35
        draw.text((text_x, text_y), f"{row['Name']}", fill='#1A233A')
        text_y += 35
        draw.text((text_x, text_y), f"SKU: {row['SKU']} | CAT: {row['Category']}", fill='#718096')
        text_y += 30
        stock_val = row['Stock']
        text_color = '#E53E3E' if stock_val <= 5 else '#38A169'
        draw.text((text_x, text_y), f"STOCK: {stock_val}", fill=text_color)
        text_y += 30
        if row['Location']:
            draw.text((text_x, text_y), f"LOC: {row['Location']}", fill='#3182CE')
            text_y += 30
        war_end_str = row['WarrantyEnd'].strftime('%Y-%m-%d') if pd.notna(row['WarrantyEnd']) and hasattr(row['WarrantyEnd'], 'strftime') else ""
        if row['SN'] or war_end_str:
            draw.text((text_x, text_y), f"S/N: {row['SN']}  War: {war_end_str}", fill='#D69E2E')
        y_offset += card_height + padding
    return img

# --- 5. 主程式介面 ---

def main():
    with st.sidebar:
        st.markdown("""<div style="margin-bottom:24px;"><h2 style="color:white;margin:0;font-size:1.5rem;">庫存管理系統</h2><p style="color:#AAB0C6;font-size:0.85rem;margin-top:4px;">Cloud Enterprise Inventory</p></div>""", unsafe_allow_html=True)
        page = st.radio("Navigation", ["總覽與查詢", "入庫作業", "出庫作業", "資料維護", "異動紀錄"], label_visibility="collapsed")
        st.markdown("---")
        st.markdown("<div style='text-align:center;color:#4A5568;font-size:0.8rem;'>Cloud v8.8 (UI Fix)</div>", unsafe_allow_html=True)

    if page == "總覽與查詢": page_search()
    elif page == "入庫作業": page_operation("入庫")
    elif page == "出庫作業": page_operation("出庫")
    elif page == "資料維護": page_maintenance()
    elif page == "異動紀錄": page_reports()

def page_search():
    st.markdown("### 📊 庫存總覽")
    df = load_data()
    c1, c2, c3 = st.columns(3)
    c1.markdown(f"""<div class="metric-card"><div class="metric-label">總品項數</div><div class="metric-value">{len(df)}</div></div>""", unsafe_allow_html=True)
    low_stock = len(df[df['Stock'] <= 5])
    c2.markdown(f"""<div class="metric-card"><div class="metric-label">低庫存警示</div><div class="metric-value" style="color:{'#E53E3E' if low_stock>0 else '#1A233A'};">{low_stock}</div></div>""", unsafe_allow_html=True)
    c3.markdown(f"""<div class="metric-card"><div class="metric-label">庫存總數量</div><div class="metric-value">{df['Stock'].sum()}</div></div>""", unsafe_allow_html=True)
    
    st.write(""); st.markdown("### 🔍 搜尋庫存")
    col_search, col_action = st.columns([3, 1])
    search_term = col_search.text_input("輸入關鍵字", placeholder="搜尋 SKU / 品名 / 地點...")
    result = df[df.astype(str).apply(lambda x: x.str.contains(search_term, case=False, na=False)).any(axis=1)] if search_term else df
    
    if col_action.button("匯出查詢結果圖", use_container_width=True):
        if result.empty: st.warning("無資料")
        else:
            with st.spinner("生成中..."):
                img = generate_inventory_image(result)
                buf = io.BytesIO()
                img.save(buf, format="PNG")
                st.download_button("下載 PNG", buf.getvalue(), "report.png", "image/png", use_container_width=True)

    st.write("")
    if not result.empty:
        st.caption(f"共找到 {len(result)} 筆資料")
        for _, row in result.iterrows():
            badges = []
            badges.append(f"<span class='badge badge-{'red' if row['Stock']<=5 else 'green'}'>庫存: {row['Stock']}</span>")
            if row['Location']: badges.append(f"<span class='badge badge-blue'>地點: {row['Location']}</span>")
            if pd.notna(row['WarrantyEnd']): badges.append(f"<span class='badge badge-gold'>保固中</span>")
            
            img_shown = False
            img_url = row.get('ImageFile', '')
            img_html = f'<img src="{img_url}" style="width:100%;border-radius:6px;">' if img_url and str(img_url).startswith("http") else '<div style="width:100%;height:100px;background:#EDF2F7;border-radius:6px;display:flex;align-items:center;justify-content:center;color:#A0AEC0;">NO IMAGE</div>'
            st.markdown(f"""
            <div style="background:white;border:1px solid #E1E4E8;border-radius:8px;padding:20px;margin-bottom:12px;box-shadow:0 1px 3px rgba(0,0,0,0.02);">
                <div style="display:flex;gap:24px;align-items:start;">
                    <div style="flex:1;">{img_html}</div>
                    <div style="flex:4;">
                        <div style="font-size:1.15rem;font-weight:600;color:#1A233A;margin-bottom:8px;">{row['Name']}</div>
                        <div style="margin-bottom:12px;">{"".join(badges)}</div>
                        <div style="font-size:0.9rem;color:#718096;"><span style="background:#F7FAFC;padding:2px 6px;border:1px solid #E2E8F0;">{row['SKU']}</span> &nbsp;•&nbsp; {row['Category']}</div>
                    </div>
                </div>
            </div>""", unsafe_allow_html=True)
    else: st.info("沒有找到相關資料。")

def page_operation(op_type):
    st.markdown(f"### {op_type}")
    if "scan_input" not in st.session_state: st.session_state.scan_input = ""
    with st.container():
        st.markdown("<div class='simple-card'><div class='form-title'>執行操作</div>", unsafe_allow_html=True)
        c1, c2 = st.columns([1, 2])
        qty = c1.number_input("數量", min_value=1, value=1)
        
        def on_scan():
            if st.session_state.scan_box:
                process_stock(st.session_state.scan_box, qty, op_type)
                st.session_state.scan_box = ""
        st.text_input("請掃描條碼或輸入 SKU", key="scan_box", on_change=on_scan, placeholder="在此處掃描...")
        st.markdown("</div>", unsafe_allow_html=True)

def process_stock(sku, qty, op_type):
    doc_ref = db.collection(COLLECTION_products).document(sku)
    doc = doc_ref.get()
    if doc.exists:
        data = doc.to_dict()
        new_stock = data.get('stock', 0) + qty if op_type == "入庫" else data.get('stock', 0) - qty
        doc_ref.update({'stock': new_stock, 'updatedAt': firestore.SERVER_TIMESTAMP})
        save_log({"Time":get_taiwan_time(), "User":"Admin", "Type":op_type, "SKU":sku, "Name":data.get('name',''), "Quantity":qty, "Note":"App"})
        st.toast(f"成功！{op_type} {qty} 個", icon="✅")
        st.success(f"已更新 **{data.get('name')}** 庫存為: {new_stock}")
    else: st.error(f"找不到 SKU: {sku}")

def page_maintenance():
    st.markdown("### 資料維護")
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["新增項目", "編輯表格", "更換圖片", "批次匯入(CSV)", "批次匯入(圖片)", "資料庫重置"])
    
    with tab1: # 新增
        st.markdown("<div class='simple-card'><div class='form-title'>新增項目</div>", unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        code = c1.text_input("編碼 (Code)")
        cat = c2.text_input("分類 (Category)")
        c3, c4 = st.columns(2)
        num = c3.text_input("號碼 (Number)")
        name = c4.text_input("品名 (Name)")
        sn = st.text_input("S/N")
        loc = st.text_input("地點")
        stock = st.number_input("初始庫存", 0, value=1)
        if st.button("確認新增", use_container_width=True):
            if code and name:
                sku = f"{code}-{cat}-{num}"
                save_data_row({"SKU":sku, "Code":code, "Category":cat, "Number":num, "Name":name, "SN":sn, "Location":loc, "Stock":stock})
                st.success(f"新增成功: {sku}")
            else: st.error("編碼與品名必填")
        st.markdown("</div>", unsafe_allow_html=True)

    with tab2: # 編輯
        df = load_data()
        edited = st.data_editor(df, num_rows="dynamic", use_container_width=True, key="editor")
        if st.button("儲存變更"):
            with st.spinner("同步中..."):
                for i, row in edited.iterrows():
                    if row['SKU']: save_data_row(row)
            st.success("更新完成")
            time.sleep(1); st.rerun()

    with tab3: # 換圖
        df_cur = load_data()
        sel = st.selectbox("選擇商品", df_cur['SKU'].unique()) if not df_cur.empty else None
        if sel:
            f = st.file_uploader("新圖片", type=["jpg","png"], key="single_up")
            if f and st.button("上傳"):
                url = upload_image_to_firebase(f, sel)
                if url:
                    db.collection(COLLECTION_products).document(sel).update({"imageFile": url})
                    st.success("圖片更新成功")

    with tab4: # CSV (修正版：移除包覆 HTML)
        st.markdown("### 批次匯入庫存資料 (CSV)")
        st.info("📢 請在此上傳您的 `inventory_data.csv`")
        
        up_csv = st.file_uploader("選擇 CSV 檔案", type=["csv"], key="csv_uploader")
        
        if up_csv:
            try:
                df_im = None
                for enc in ['utf-8-sig', 'utf-8', 'big5', 'cp950', 'utf-16']:
                    try:
                        up_csv.seek(0)
                        df_im = pd.read_csv(up_csv, encoding=enc, sep=None, engine='python')
                        break
                    except: continue
                
                if df_im is not None:
                    df_im.columns = [str(c).strip() for c in df_im.columns]
                    st.write(f"預覽 ({len(df_im)} 筆):"); st.dataframe(df_im.head())
                    if st.button("🚀 開始匯入", type="primary"):
                        progress = st.progress(0)
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
                            progress.progress((i+1)/len(df_im))
                        st.success("匯入完成！"); time.sleep(2); st.rerun()
                else: st.error("無法讀取檔案，請檢查格式。")
            except Exception as e: st.error(f"錯誤: {e}")

    with tab5: # 批次圖片 (修正版：移除包覆 HTML)
        st.markdown("### 批次圖片匯入")
        st.info("💡 說明：上傳多張圖片，系統會自動根據「檔名」對應 SKU。")
        
        all_skus = [d.id for d in db.collection(COLLECTION_products).stream()]
        if not all_skus:
            st.warning("⚠️ 資料庫目前是空的，無法進行圖片對應。請先在左側【批次匯入(CSV)】上傳商品資料。")
        else:
            st.success(f"目前有 {len(all_skus)} 筆商品資料，準備就緒。")
            imgs = st.file_uploader("選取多張圖片 (檔名需包含SKU)", accept_multiple_files=True, key="multi_img_up")
            if imgs and st.button("開始上傳圖片"):
                bar = st.progress(0); succ=0; fail=0
                for i, f in enumerate(imgs):
                    sku = f.name.rsplit('.', 1)[0].strip()
                    if sku in all_skus:
                        u = upload_image_to_firebase(f, sku)
                        if u:
                            db.collection(COLLECTION_products).document(sku).update({"imageFile": u})
                            succ += 1
                    else: fail += 1
                    bar.progress((i+1)/len(imgs))
                st.success(f"成功: {succ}, 失敗/跳過: {fail}"); time.sleep(2); st.rerun()

    with tab6: # Reset
        st.markdown("<div class='simple-card'><div class='form-title' style='color:red;'>⚠️ 清空資料庫</div>", unsafe_allow_html=True)
        st.warning("請輸入 'DELETE' 確認刪除")
        confirm = st.text_input("確認碼", key="del_confirm")
        if confirm == "DELETE" and st.button("執行刪除", type="primary"):
            with st.spinner("刪除中..."):
                c = delete_all_products_logic()
            st.success(f"已刪除 {c} 筆資料"); time.sleep(2); st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

def page_reports():
    st.markdown("### 📋 異動紀錄")
    df = load_log()
    st.dataframe(df, use_container_width=True)
    st.download_button("下載 CSV", df.to_csv(index=False).encode('utf-8-sig'), "log.csv", "text/csv")

if __name__ == "__main__":
    main()
