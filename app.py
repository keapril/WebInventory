# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import io
import json
import time
from PIL import Image
from datetime import datetime

# Firebase 相關套件
import firebase_admin
from firebase_admin import credentials, firestore, storage

# --- 1. 系統設定 ---
st.set_page_config(
    page_title="庫存管理系統 (雲端版)",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. Firebase 初始化 (單例模式) ---
# 確保只初始化一次，避免 Streamlit Rerun 時報錯
if not firebase_admin._apps:
    # 從 Streamlit Secrets 讀取金鑰字串並轉回 JSON 物件
    key_dict = json.loads(st.secrets["firebase"]["text_key"])
    cred = credentials.Certificate(key_dict)
    
    # 初始化 App (需指定 Storage Bucket)
    # 請將 '您的專案ID.appspot.com' 替換為您 Firebase Storage 的 Bucket 名稱
    # 通常是 key_dict['project_id'] + '.appspot.com'
    bucket_name = f"{key_dict['project_id']}.appspot.com"
    
    firebase_admin.initialize_app(cred, {
        'storageBucket': bucket_name
    })

db = firestore.client()
bucket = storage.bucket()

# --- 3. 資料庫操作函式 (Firestore) ---

COLLECTION_NAME = "products"  # 與您的 HTML 系統共用同一個集合

def load_data():
    """從 Firestore 讀取所有資料並轉為 DataFrame"""
    docs = db.collection(COLLECTION_NAME).stream()
    data = []
    for doc in docs:
        d = doc.to_dict()
        # 確保欄位對應 (CSV headers -> Firestore fields)
        data.append({
            "SKU": doc.id, # 使用文件 ID 作為 SKU (唯一值)
            "Code": d.get("code", ""),
            "Category": d.get("categoryName", ""), # HTML版是用 categoryName
            "Number": d.get("number", ""), # 假設您有這個欄位
            "Name": d.get("name", ""),
            "ImageFile": d.get("imageFile", ""), # 存圖片網址或檔名
            "Stock": d.get("stock", 0),
            "Location": d.get("location", ""),
            "SN": d.get("sn", ""),
            "Spec": d.get("spec", ""),
            "UDI": d.get("udi", "")
        })
    
    if not data:
        return pd.DataFrame(columns=["SKU", "Code", "Category", "Number", "Name", "ImageFile", "Stock", "Location", "SN", "Spec", "UDI"])
    
    return pd.DataFrame(data)

def save_data_row(row):
    """更新單筆資料到 Firestore"""
    # 將 DataFrame 的 Row 轉為 Dictionary
    data_dict = {
        "code": row.get("Code", ""),
        "categoryName": row.get("Category", ""),
        "number": row.get("Number", ""),
        "name": row.get("Name", ""),
        "imageFile": row.get("ImageFile", ""),
        "stock": row.get("Stock", 0),
        "location": row.get("Location", ""),
        "sn": row.get("SN", ""),
        "spec": row.get("Spec", ""),
        "udi": row.get("UDI", ""),
        "updatedAt": firestore.SERVER_TIMESTAMP
    }
    # SKU 當作 Document ID
    db.collection(COLLECTION_NAME).document(str(row["SKU"])).set(data_dict, merge=True)

def upload_image_to_firebase(uploaded_file, sku):
    """上傳圖片到 Firebase Storage 並回傳公開連結"""
    if uploaded_file is None:
        return None
    
    # 建立檔案路徑 (例如 images/SKU-timestamp.jpg)
    file_ext = uploaded_file.name.split('.')[-1]
    blob_name = f"images/{sku}-{int(time.time())}.{file_ext}"
    blob = bucket.blob(blob_name)
    
    # 上傳
    blob.upload_from_file(uploaded_file, content_type=uploaded_file.type)
    
    # 設定為公開讀取 (這需要您在 Firebase Storage Rules 開放讀取權限)
    blob.make_public()
    
    return blob.public_url

# --- 4. 介面邏輯 ---

st.title("☁️ 雲端庫存管理系統 (Firebase)")

# 側邊欄
st.sidebar.header("功能選單")
menu = st.sidebar.radio("前往", ["庫存總覽", "新增商品", "圖片管理"])

if menu == "庫存總覽":
    st.subheader("📦 目前庫存")
    df = load_data()
    
    # 搜尋
    search_term = st.text_input("🔍 搜尋 (名稱/代碼/規格)", "")
    if search_term:
        df = df[
            df["Name"].str.contains(search_term, case=False, na=False) |
            df["Code"].str.contains(search_term, case=False, na=False) |
            df["Spec"].str.contains(search_term, case=False, na=False)
        ]

    # 顯示表格 (可編輯)
    edited_df = st.data_editor(
        df,
        key="inventory_editor",
        num_rows="dynamic",
        column_config={
            "ImageFile": st.column_config.ImageColumn("圖片預覽"),
            "Stock": st.column_config.NumberColumn("數量", min_value=0, step=1),
        },
        use_container_width=True
    )

    if st.button("💾 儲存變更"):
        # 比對差異並上傳 (為了效能，這裡簡單示範全部檢查，實際可只存變更)
        # 這裡簡化邏輯：逐筆儲存
        progress_bar = st.progress(0)
        for i, row in edited_df.iterrows():
            if not pd.isna(row["SKU"]) and str(row["SKU"]).strip() != "":
                save_data_row(row)
            progress_bar.progress((i + 1) / len(edited_df))
        
        st.success("✅ 資料已同步至雲端！")
        time.sleep(1)
        st.rerun()

elif menu == "新增商品":
    st.subheader("➕ 新增商品")
    with st.form("add_form"):
        c1, c2 = st.columns(2)
        sku = c1.text_input("SKU (唯一編號)*")
        code = c2.text_input("產品代碼")
        name = st.text_input("品名*")
        category = c1.text_input("分類")
        spec = c2.text_input("規格")
        stock = st.number_input("初始數量", min_value=0, value=1)
        
        uploaded_img = st.file_uploader("商品圖片", type=["png", "jpg", "jpeg"])
        
        if st.form_submit_button("新增"):
            if not sku or not name:
                st.error("SKU 和 品名 為必填！")
            else:
                image_url = ""
                if uploaded_img:
                    with st.spinner("圖片上傳中..."):
                        image_url = upload_image_to_firebase(uploaded_img, sku)
                
                new_data = {
                    "SKU": sku, "Code": code, "Name": name, 
                    "Category": category, "Spec": spec, 
                    "Stock": stock, "ImageFile": image_url,
                    "Number": "", "Location": "", "SN": "", "UDI": ""
                }
                save_data_row(new_data)
                st.success(f"已新增：{name}")

elif menu == "圖片管理":
    st.subheader("🖼️ 圖片更換")
    df = load_data()
    
    sku_to_edit = st.selectbox("選擇商品", df["SKU"].unique())
    
    if sku_to_edit:
        item = df[df["SKU"] == sku_to_edit].iloc[0]
        st.write(f"目前商品：**{item['Name']}**")
        
        if item["ImageFile"]:
            st.image(item["ImageFile"], width=200, caption="目前圖片")
        else:
            st.info("尚無圖片")
            
        new_img = st.file_uploader("上傳新圖片", type=["png", "jpg"])
        if new_img and st.button("確認更換"):
            url = upload_image_to_firebase(new_img, sku_to_edit)
            # 更新資料庫欄位
            db.collection(COLLECTION_NAME).document(str(sku_to_edit)).update({"imageFile": url})
            st.success("圖片更新完成！")
            time.sleep(1)
            st.rerun()

# 頁尾
st.markdown("---")
st.caption("🔒 雲端同步版 | 資料儲存於 Google Cloud Firestore")