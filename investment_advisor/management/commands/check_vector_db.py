from django.core.management.base import BaseCommand
import chromadb
import os
import json

class Command(BaseCommand):
    help = 'Kiểm tra dữ liệu đang lưu trong Vector DB (ChromaDB)'

    def handle(self, *args, **kwargs):
        # 1. Đường dẫn đến kho dữ liệu (Phải khớp với file gemini_agent.py)
        DB_PATH = "./chroma_db_storage"
        COLLECTION_NAME = "market_memory"

        # Kiểm tra xem thư mục có tồn tại không
        if not os.path.exists(DB_PATH):
            self.stdout.write(self.style.ERROR(f"Lỗi: Không tìm thấy thư mục '{DB_PATH}'. Bạn đã chạy Backfill chưa?"))
            return

        self.stdout.write(f"--- ĐANG KẾT NỐI VỚI CHROMA DB TẠI '{DB_PATH}' ---")

        try:
            # 2. Kết nối client
            client = chromadb.PersistentClient(path=DB_PATH)
            
            # 3. Lấy Collection (Bảng dữ liệu)
            try:
                collection = client.get_collection(name=COLLECTION_NAME)
            except Exception:
                self.stdout.write(self.style.ERROR(f"Lỗi: Không tìm thấy Collection tên '{COLLECTION_NAME}'. Database có thể đang rỗng."))
                return

            # 4. Đếm số lượng bản ghi
            count = collection.count()
            self.stdout.write(self.style.SUCCESS(f"TỔNG SỐ BẢN GHI (MEMORY): {count}"))

            if count == 0:
                self.stdout.write(self.style.WARNING("Database đang rỗng!"))
                return

            # 5. Lấy thử 5 bản ghi mới nhất để xem (Peek)
            self.stdout.write("\n--- HIỂN THỊ 5 BẢN GHI MẪU ---")
            
            # peek() lấy n bản ghi đầu tiên trong kho
            results = collection.peek(limit=5)
            
            # Chroma lưu dữ liệu theo cột (ids, embeddings, documents, metadatas)
            # Chúng ta cần ghép lại để dễ đọc
            ids = results['ids']
            documents = results['documents']
            metadatas = results['metadatas']

            for i in range(0, len(ids)):
                print("-" * 50)
                print(f"ID       : {ids[i]}")
                print(f"METADATA : {metadatas[i]}")
                print(f"CONTENT  : {documents[i][:200]}...") # Chỉ in 200 ký tự đầu cho gọn
                print("-" * 50)

            # 6. (Nâng cao) Thử tìm kiếm 1 mã cụ thể
            self.stdout.write("\n--- (TEST QUERY) TÌM KIẾM DỮ LIỆU CỦA 'HPG' ---")
            # Lấy tất cả dữ liệu có metadata chứa symbol='HPG'
            hpg_data = collection.get(where={"symbol": "HPG"}, limit=3)
            
            if hpg_data['ids']:
                print(f"Tìm thấy {len(hpg_data['ids'])} bản ghi mẫu của HPG:")
                for i in range(len(hpg_data['ids'])):
                    print(f"> Ngày: {hpg_data['metadatas'][i].get('date')} | Signal: {hpg_data['metadatas'][i].get('signal')}")
            else:
                print("Không tìm thấy dữ liệu nào của HPG.")

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Lỗi không xác định: {e}"))