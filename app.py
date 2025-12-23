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
    page_title="儀器耗材管理系統",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. Firebase 初始化 (超級容錯版) ---
if not firebase_admin._apps:
    try:
        # A. 檢查 Secrets 是否存在
        if "firebase" not in st.secrets:
            st.error("❌ 錯誤：Streamlit Secrets 中找不到 [firebase] 區塊。")
            st.stop()

        if "text_key" not in st.secrets["firebase"]:
            st.error("❌ 錯誤：在 [firebase] 區塊中找不到 'text_key'。")
            st.stop()

        # B. 嘗試解析 JSON (加入 strict=False 以容許換行符號)
        token_content = st.secrets["firebase"]["text_key"]
        
        try:
            # 關鍵修正：strict=False 允許字串內包含控制字元(如換行)
            key_dict = json.loads(token_content, strict=False)
        except json.JSONDecodeError as e:
            # 如果還是失敗，顯示更具體的引導
            st.error("❌ JSON 解析嚴重失敗。")
            st.warning(f"詳細錯誤：{e}")
            st.info("💡 診斷：您的 'private_key' 欄位可能被斷行了。請嘗試重新複製 JSON，並確保貼上時沒有被編輯器自動格式化。")
            st.code(token_content[:500], language="json") # 顯示前段內容供檢查
            st.stop()

        # C. 檢查並修復 private_key 格式 (重要)
        # 有時候 strict=False 讀進來後，private_key 裡面的 \n 會變成真的換行，
        # 但 Firebase Admin 有時候需要它是 \n 字串，或是乾淨的 PEM 格式。
        if "private_key" in key_dict:
            # 確保 private_key 正確處理換行
            key_dict["private_key"] = key_dict["private_key"].replace("\\n", "\n")

        # D. 初始化
        cred = credentials.Certificate(key_dict)
        
        # 自動抓取 project_id
        project_id = key_dict.get('project_id')
        bucket_name = f"{project_id}.appspot.com"
        
        firebase_admin.initialize_app(cred, {
            'storageBucket': bucket_name
        })
        
        st.sidebar.success("✅ Firebase 連線成功")

    except Exception as e:
        st.error(f"❌ Firebase 初始化發生未預期的錯誤：{e}")
        st.caption(f"錯誤類型：{type(e).__name__}")
        st.stop()

db = firestore.client()
bucket = storage.bucket()

COLLECTION_NAME = "products"

# --- 3. 資料庫操作函式 ---

def load_data_snapshot():
    """讀取資料與原始 ID"""
    try:
        docs = db.collection(COLLECTION_NAME).stream()
        data = []
        original_ids = set()

        for doc in docs:
            d = doc.to_dict()
            sku = doc.id
            original_ids.add(sku)
            
            data.append({
                "SKU": sku, 
                "Code": d.get("code", ""),
                "Category": d.get("categoryName", ""),
                "Number": d.get("number", ""),
                "Name": d.get("name", ""),
                "ImageFile": d.get("imageFile", ""),
                "Stock": d.get("stock", 0),
                "Location": d.get("location", ""),
                "SN": d.get("sn", ""),
                "Spec": d.get("spec", ""),
                "UDI": d.get("udi", "")
            })
        
        if not data:
            return pd.DataFrame(columns=["SKU", "Code", "Category", "Number", "Name", "ImageFile", "Stock", "Location", "SN", "Spec", "UDI"]), original_ids
        
        return pd.DataFrame(data), original_ids
    except Exception as e:
        st.error(f"讀取資料庫時發生錯誤: {e}")
        return pd.DataFrame(), set()

def save_data_row(row):
    """更新單筆資料"""
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
    db.collection(COLLECTION_NAME).document(str(row["SKU"])).set(data_dict, merge=True)

def delete_data_row(sku):
    """刪除資料"""
    db.collection(COLLECTION_NAME).document(str(sku)).delete()

def upload_image_to_firebase(uploaded_file, sku):
    """上傳圖片"""
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

# --- 4. 介面邏輯 ---

st.title("☁️ 儀器耗材管理系統")

if 'original_ids' not in st.session_state:
    st.session_state.original_ids = set()

menu = st.sidebar.radio("前往", ["庫存總覽", "新增商品", "圖片管理"])

if menu == "庫存總覽":
    st.subheader("📦 目前庫存")
    
    df, original_ids = load_data_snapshot()
    st.session_state.original_ids = original_ids

    if not df.empty:
        search_term = st.text_input("🔍 搜尋 (名稱/代碼/規格)", "")
        if search_term:
            df = df[
                df["Name"].str.contains(search_term, case=False, na=False) |
                df["Code"].str.contains(search_term, case=False, na=False) |
                df["Spec"].str.contains(search_term, case=False, na=False)
            ]

        edited_df = st.data_editor(
            df,
            key="inventory_editor",
            num_rows="dynamic",
            column_config={
                "SKU": st.column_config.TextColumn("SKU (不可改)", disabled=True),
                "ImageFile": st.column_config.ImageColumn("圖片預覽"),
                "Stock": st.column_config.NumberColumn("數量", min_value=0, step=1),
            },
            use_container_width=True
        )

        if st.button("💾 儲存變更"):
            try:
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                total_rows = len(edited_df)
                current_skus = set()
                
                for i, row in edited_df.iterrows():
                    if not pd.isna(row["SKU"]) and str(row["SKU"]).strip() != "":
                        sku_str = str(row["SKU"])
                        current_skus.add(sku_str)
                        save_data_row(row)
                    
                    if total_rows > 0:
                        progress_bar.progress((i + 1) / total_rows)
                
                deleted_skus = st.session_state.original_ids - current_skus
                
                if deleted_skus:
                    status_text.text(f"正在刪除 {len(deleted_skus)} 筆資料...")
                    for sku in deleted_skus:
                        delete_data_row(sku)
                
                st.success(f"✅ 同步完成！更新/新增 {len(edited_df)} 筆，刪除 {len(deleted_skus)} 筆。")
                time.sleep(1.5)
                st.rerun()
                
            except Exception as e:
                st.error(f"儲存過程發生錯誤: {e}")
    else:
        st.info("目前沒有資料，請至「新增商品」頁面新增。")

elif menu == "新增商品":
    st.subheader("➕ 新增商品")
    with st.form("add_form"):
        c1, c2 = st.columns(2)
        sku = c1.text_input("SKU (唯一編號)*", help="請輸入唯一識別碼，建立後不可修改")
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
                # 檢查是否存在
                doc_ref = db.collection(COLLECTION_NAME).document(sku)
                if doc_ref.get().exists:
                    st.error(f"錯誤：SKU '{sku}' 已存在。")
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
                    time.sleep(1)
                    st.rerun()

elif menu == "圖片管理":
    st.subheader("🖼️ 圖片更換")
    df, _ = load_data_snapshot()
    
    if not df.empty:
        sku_to_edit = st.selectbox("選擇商品", df["SKU"].unique())
        
        if sku_to_edit:
            item = df[df["SKU"] == sku_to_edit].iloc[0]
            st.write(f"目前商品：**{item['Name']}** ({item['SKU']})")
            
            if item["ImageFile"]:
                st.image(item["ImageFile"], width=200, caption="目前圖片")
            else:
                st.info("尚無圖片")
                
            new_img = st.file_uploader("上傳新圖片", type=["png", "jpg"])
            if new_img and st.button("確認更換"):
                with st.spinner("上傳中..."):
                    url = upload_image_to_firebase(new_img, sku_to_edit)
                    if url:
                        db.collection(COLLECTION_NAME).document(str(sku_to_edit)).update({"imageFile": url})
                        st.success("圖片更新完成！")
                        time.sleep(1)
                        st.rerun()
    else:
        st.info("無資料可編輯。")

# 頁尾
st.markdown("---")
st.caption("🔒 雲端同步版 | 資料儲存於 Google Cloud Firestore")
