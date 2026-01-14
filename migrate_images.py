# -*- coding: utf-8 -*-
"""
遷移腳本：將 Firebase Storage 的舊圖片遷移到 Cloudflare R2
執行方式：在本地運行 python migrate_images.py
"""

import json
import time
import io
import boto3
from PIL import Image
import firebase_admin
from firebase_admin import credentials, firestore, storage

# ==========================================
# 配置
# ==========================================

# Firebase 設定
FIREBASE_KEY_PATH = "product-system-900c4-firebase-adminsdk-fbsvc-305a38d463.json"
FIREBASE_BUCKET = "product-system-900c4.firebasestorage.app"

# Cloudflare R2 設定 - 從 secrets.toml 讀取
import tomllib
import os

secrets_path = os.path.join(os.path.dirname(__file__), ".streamlit", "secrets.toml")
with open(secrets_path, "rb") as f:
    secrets = tomllib.load(f)

r2_conf = secrets.get("cloudflare", {})
R2_ENDPOINT = r2_conf.get("endpoint", "")
R2_ACCESS_KEY = r2_conf.get("access_key", "")
R2_SECRET_KEY = r2_conf.get("secret_key", "")
R2_BUCKET_NAME = r2_conf.get("bucket_name", "")
R2_PUBLIC_DOMAIN = r2_conf.get("public_domain", "")

# Firestore Collection
COLLECTION_NAME = "instrument_consumables"

# ==========================================
# 初始化
# ==========================================

def init_firebase():
    """初始化 Firebase"""
    if not firebase_admin._apps:
        cred = credentials.Certificate(FIREBASE_KEY_PATH)
        firebase_admin.initialize_app(cred, {
            'storageBucket': FIREBASE_BUCKET
        })
    
    db = firestore.client()
    bucket = storage.bucket()
    return db, bucket

def init_r2():
    """初始化 Cloudflare R2 客戶端"""
    return boto3.client(
        's3',
        endpoint_url=R2_ENDPOINT,
        aws_access_key_id=R2_ACCESS_KEY,
        aws_secret_access_key=R2_SECRET_KEY
    )

# ==========================================
# 遷移邏輯
# ==========================================

def is_firebase_url(url):
    """檢查是否為 Firebase Storage URL"""
    if not url:
        return False
    return "storage.googleapis.com" in url or "firebasestorage.app" in url

def extract_blob_path(url):
    """從 Firebase Storage URL 提取 blob 路徑"""
    import urllib.parse
    parsed = urllib.parse.urlparse(url)
    path_parts = parsed.path.split('/', 2)
    if len(path_parts) >= 3:
        return urllib.parse.unquote(path_parts[2])
    return None

def migrate_single_image(db, firebase_bucket, r2_client, doc_id, image_url):
    """遷移單張圖片"""
    try:
        # 1. 從 Firebase Storage 下載圖片
        blob_path = extract_blob_path(image_url)
        if not blob_path:
            print(f"  ❌ 無法解析 blob 路徑: {image_url}")
            return False
        
        blob = firebase_bucket.blob(blob_path)
        image_bytes = blob.download_as_bytes()
        print(f"  ✅ 下載成功: {blob_path}")
        
        # 2. 處理圖片（壓縮/轉換）
        image = Image.open(io.BytesIO(image_bytes))
        if image.mode in ("RGBA", "P"):
            image = image.convert("RGB")
        
        max_width = 800
        if image.width > max_width:
            ratio = max_width / float(image.width)
            new_height = int(float(image.height) * ratio)
            image = image.resize((max_width, new_height), Image.Resampling.LANCZOS)
        
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format='JPEG', quality=80)
        img_byte_arr.seek(0)
        
        # 3. 上傳到 Cloudflare R2
        safe_doc_id = "".join([c for c in doc_id if c.isalnum() or c in ('-', '_')])
        new_file_name = f"images/{safe_doc_id}-{int(time.time())}.jpg"
        
        r2_client.upload_fileobj(
            img_byte_arr,
            R2_BUCKET_NAME,
            new_file_name,
            ExtraArgs={'ContentType': 'image/jpeg'}
        )
        new_url = f"{R2_PUBLIC_DOMAIN}/{new_file_name}"
        print(f"  ✅ 上傳成功: {new_url}")
        
        # 4. 更新 Firestore
        db.collection(COLLECTION_NAME).document(doc_id).update({
            'imageFile': new_url
        })
        print(f"  ✅ 資料庫已更新")
        
        return True
        
    except Exception as e:
        print(f"  ❌ 遷移失敗: {e}")
        return False

def migrate_all():
    """遷移所有 Firebase Storage 的圖片"""
    print("=" * 50)
    print("開始遷移 Firebase Storage 圖片到 Cloudflare R2")
    print("=" * 50)
    
    # 檢查配置
    if not all([R2_ENDPOINT, R2_ACCESS_KEY, R2_SECRET_KEY, R2_BUCKET_NAME, R2_PUBLIC_DOMAIN]):
        print("❌ 錯誤：請先設定 Cloudflare R2 的配置")
        print("   編輯 migrate_images.py，填入以下資訊：")
        print("   - R2_ENDPOINT")
        print("   - R2_ACCESS_KEY")
        print("   - R2_SECRET_KEY")
        print("   - R2_BUCKET_NAME")
        print("   - R2_PUBLIC_DOMAIN")
        return
    
    # 初始化
    db, firebase_bucket = init_firebase()
    r2_client = init_r2()
    
    # 讀取所有文件
    docs = db.collection(COLLECTION_NAME).stream()
    
    total = 0
    migrated = 0
    skipped = 0
    failed = 0
    
    for doc in docs:
        total += 1
        data = doc.to_dict()
        image_url = data.get('imageFile', '')
        
        print(f"\n[{total}] 處理: {doc.id}")
        
        if not image_url:
            print(f"  ⏭️ 跳過：無圖片")
            skipped += 1
            continue
        
        if not is_firebase_url(image_url):
            print(f"  ⏭️ 跳過：已經是 R2 或其他來源")
            skipped += 1
            continue
        
        success = migrate_single_image(db, firebase_bucket, r2_client, doc.id, image_url)
        if success:
            migrated += 1
        else:
            failed += 1
        
        # 避免請求太快
        time.sleep(0.5)
    
    print("\n" + "=" * 50)
    print("遷移完成！")
    print(f"  總計: {total}")
    print(f"  成功遷移: {migrated}")
    print(f"  跳過: {skipped}")
    print(f"  失敗: {failed}")
    print("=" * 50)

if __name__ == "__main__":
    migrate_all()
