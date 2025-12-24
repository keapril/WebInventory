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

# --- 3. 自定義 CSS (全部移除，使用原生樣式確保功能) ---
# st.markdown(...) # 移除樣式以修復顯示問題

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
    # 簡單的圖片生成邏輯
    card_width, card_height, padding, header_height = 800, 220, 24, 100
    total_height = header_height + (len(df_result) * (card_height + padding)) + padding
    img = Image.new('RGB', (card_width + padding*2, total_height), color='#F4F6F8')
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, card_width + padding*2, header_height], fill='#1A233A')
    draw.text((padding, 35), f"INVENTORY REPORT - {datetime.now().strftime('%Y-%m-%d')}", fill='white')
    y_offset = header_height + padding
    
    for _, row in df_result.iterrows():
        draw.rectangle([padding, y_offset, padding + card_width, y_offset + card_height], fill='#FFFFFF', outline='#E1E4E8', width=1)
        
        # 嘗試下載圖片
        prod_img = None
        img_url = row.get('ImageFile', '')
        if img_url and isinstance(img_url, str) and img_url.startswith("http"):
            try:
                response = requests.get(img_url, timeout=3)
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
        
        y_offset += card_height + padding
    return img

# --- 5. 主程式介面 ---

def main():
    st.sidebar.title("儀器耗材管理")
    st.sidebar.caption("Cloud v9.0 (Native Stable)")
    
    page = st.sidebar.radio("導航選單", ["總覽與查詢", "入庫作業", "出庫作業", "資料維護", "異動紀錄"])

    if page == "總覽與查詢": page_search()
    elif page == "入庫作業": page_operation("入庫")
    elif page == "出庫作業": page_operation("出庫")
    elif page == "資料維護": page_maintenance()
    elif page == "異動紀錄": page_reports()

def page_search():
    st.header("📊 庫存總覽")
    df = load_data()
    
    c1, c2, c3 = st.columns(3)
    c1.metric("總品項數", len(df))
    low_stock = len(df[df['Stock'] <= 5])
    c2.metric("低庫存警示", low_stock, delta_color="inverse")
    c3.metric("庫存總數量", int(df['Stock'].sum()))
    
    st.divider()
    st.subheader("🔍 搜尋庫存")
    
    col_search, col_action = st.columns([3, 1])
    search_term = col_search.text_input("輸入關鍵字", placeholder="搜尋 SKU / 品名 / 地點...")
    
    result = df
    if search_term:
        result = df[df.astype(str).apply(lambda x: x.str.contains(search_term, case=False, na=False)).any(axis=1)]
    
    if col_action.button("匯出查詢結果圖", use_container_width=True):
        if result.empty: st.warning("無資料可生成")
        else:
            with st.spinner("生成圖片中..."):
                img = generate_inventory_image(result)
                buf = io.BytesIO()
                img.save(buf, format="PNG")
                st.download_button("下載 PNG", buf.getvalue(), "inventory_report.png", "image/png", use_container_width=True)

    st.write(f"共找到 {len(result)} 筆資料")
    
    # 使用原生 dataframe 顯示，確保一定看得到資料
    st.dataframe(
        result,
        column_config={
            "ImageFile": st.column_config.ImageColumn("圖片"),
            "Stock": st.column_config.NumberColumn("庫存"),
        },
        use_container_width=True
    )

def page_operation(op_type):
    st.header(f"📦 {op_type}作業")
    
    # 使用原生容器
    with st.container(border=True):
        st.subheader("執行操作")
        
        c1, c2 = st.columns([1, 2])
        qty = c1.number_input("數量", min_value=1, value=1)
        
        # 掃描框處理
        if "scan_input" not in st.session_state: st.session_state.scan_input = ""
        
        def on_scan():
            if st.session_state.scan_box:
                process_stock(st.session_state.scan_box, qty, op_type)
                st.session_state.scan_box = "" # 清空
        
        st.text_input("請掃描條碼或輸入 SKU (按 Enter 執行)", key="scan_box", on_change=on_scan)

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
            "Note": "App Operation"
        })
        st.toast(f"✅ {op_type}成功！ {sku} 目前庫存: {new_stock}")
        st.success(f"已更新 **{data.get('name')}** 庫存為: {new_stock}")
    else:
        st.error(f"❌ 找不到 SKU: {sku}")

def page_maintenance():
    st.header("🛠️ 資料維護")
    
    # 這裡使用原生的 tabs，完全不依賴 CSS
    tabs = st.tabs(["1. 新增項目", "2. 編輯表格", "3. 更換圖片", "4. 批次匯入(CSV)", "5. 批次匯入(圖片)", "6. 資料庫重置"])
    
    with tabs[0]: # 新增
        st.subheader("新增單筆資料")
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
                    st.success(f"新增成功: {sku}")
                else:
                    st.error("編碼與品名為必填欄位")

    with tabs[1]: # 編輯
        st.subheader("線上編輯表格")
        df = load_data()
        edited = st.data_editor(df, num_rows="dynamic", use_container_width=True, key="data_editor_main")
        if st.button("💾 儲存表格變更"):
            with st.spinner("正在同步至雲端..."):
                for i, row in edited.iterrows():
                    if row['SKU']: save_data_row(row)
            st.success("更新完成！")
            time.sleep(1)
            st.rerun()

    with tabs[2]: # 換圖
        st.subheader("單筆更換圖片")
        df_cur = load_data()
        if not df_cur.empty:
            sel = st.selectbox("選擇商品", df_cur['SKU'].unique())
            if sel:
                row = df_cur[df_cur['SKU'] == sel].iloc[0]
                st.write(f"目前商品：**{row['Name']}**")
                
                # 顯示舊圖
                curr_img = row.get('ImageFile')
                if curr_img and str(curr_img).startswith('http'):
                    st.image(curr_img, width=200, caption="目前圖片")
                
                f = st.file_uploader("上傳新圖片", type=["jpg","png"], key="single_uploader")
                if f and st.button("確認上傳"):
                    url = upload_image_to_firebase(f, sel)
                    if url:
                        db.collection(COLLECTION_products).document(sel).update({"imageFile": url})
                        st.success("圖片更新成功！")
        else:
            st.info("目前沒有商品資料")

    with tabs[3]: # CSV
        st.subheader("批次匯入庫存資料 (CSV)")
        st.info("請上傳 `inventory_data.csv`。系統會自動對應欄位。")
        
        up_csv = st.file_uploader("選擇 CSV 檔案", type=["csv"], key="csv_batch_uploader")
        
        if up_csv:
            try:
                # 嘗試多種編碼
                df_im = None
                for enc in ['utf-8-sig', 'utf-8', 'big5', 'cp950']:
                    try:
                        up_csv.seek(0)
                        df_im = pd.read_csv(up_csv, encoding=enc)
                        break
                    except: continue
                
                if df_im is not None:
                    # 去除欄位名稱的空白
                    df_im.columns = [str(c).strip() for c in df_im.columns]
                    st.write("預覽資料：")
                    st.dataframe(df_im.head())
                    
                    if st.button("🚀 開始匯入", type="primary"):
                        progress_bar = st.progress(0)
                        
                        # 建立不分大小寫的欄位對應表
                        col_map = {c.lower(): c for c in df_im.columns}
                        def get_val(r, k): return r.get(col_map.get(k.lower()), '')

                        for i, row in df_im.iterrows():
                            sku = str(get_val(row, 'sku')).strip()
                            # 簡單防呆
                            if sku and sku.lower() != 'nan':
                                save_data_row({
                                    "SKU": sku, 
                                    "Code": get_val(row,'code'), 
                                    "Category": get_val(row,'category'),
                                    "Number": get_val(row,'number'), 
                                    "Name": get_val(row,'name'), 
                                    "ImageFile": get_val(row,'imagefile'),
                                    "Stock": get_val(row,'stock'), 
                                    "Location": get_val(row,'location'), 
                                    "SN": get_val(row,'sn'),
                                    "WarrantyStart": get_val(row,'warrantystart'), 
                                    "WarrantyEnd": get_val(row,'warrantyend')
                                })
                            progress_bar.progress((i+1)/len(df_im))
                        
                        st.success("匯入完成！")
                        time.sleep(2)
                        st.rerun()
                else:
                    st.error("無法讀取 CSV，請檢查編碼或格式。")
            except Exception as e:
                st.error(f"發生錯誤: {e}")

    with tabs[4]: # 批次圖片
        st.subheader("批次圖片匯入")
        st.info("上傳多張圖片，系統會自動根據「檔名」對應 SKU (例如 A001.jpg -> SKU: A001)。")
        
        # 檢查是否有資料
        all_skus = [d.id for d in db.collection(COLLECTION_products).stream()]
        
        if not all_skus:
            st.warning("⚠️ 資料庫目前是空的，無法進行圖片對應。請先到左邊的分頁匯入 CSV。")
        else:
            st.success(f"目前資料庫有 {len(all_skus)} 筆商品，準備就緒。")
            
            imgs = st.file_uploader("選取多張圖片", type=["jpg", "png", "jpeg"], accept_multiple_files=True, key="multi_img_uploader")
            
            if imgs and st.button("開始批次上傳"):
                bar = st.progress(0)
                succ = 0
                fail = 0
                
                for i, f in enumerate(imgs):
                    # 檔名處理：去除副檔名
                    sku = f.name.rsplit('.', 1)[0].strip()
                    
                    if sku in all_skus:
                        u = upload_image_to_firebase(f, sku)
                        if u:
                            db.collection(COLLECTION_products).document(sku).update({"imageFile": u})
                            succ += 1
                    else:
                        fail += 1
                    
                    bar.progress((i+1)/len(imgs))
                
                st.success(f"處理完成！成功: {succ}, 跳過(找不到SKU): {fail}")
                time.sleep(3)
                st.rerun()

    with tabs[5]: # Reset
        st.subheader("⚠️ 危險區域：資料庫重置")
        st.error("此操作將永久刪除所有資料！")
        
        confirm = st.text_input("請輸入 'DELETE' 以確認刪除", key="delete_confirm")
        
        if st.button("🗑️ 確認清空資料庫", type="primary"):
            if confirm == "DELETE":
                with st.spinner("正在刪除所有資料..."):
                    c = delete_all_products_logic()
                st.success(f"已刪除 {c} 筆資料。")
                time.sleep(2)
                st.rerun()
            else:
                st.error("確認碼錯誤")

def page_reports():
    st.header("📋 異動紀錄")
    df = load_log()
    st.dataframe(df, use_container_width=True)
    st.download_button("下載 CSV 紀錄", df.to_csv(index=False).encode('utf-8-sig'), "log.csv", "text/csv")

if __name__ == "__main__":
    main()
