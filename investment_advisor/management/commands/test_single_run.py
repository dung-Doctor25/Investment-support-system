from django.core.management.base import BaseCommand
from ...models import ThiTruongChungKhoang
from ...gemeni_system import FinAgentSystem # Đã đổi tên class
from ...utils import get_formatted_news, get_formatted_financials, get_price_action
import datetime
import json
import os
from django.conf import settings

# Lấy API Key
api_key = os.environ.get("GEMINI_API_KEY") or getattr(settings, 'GEMINI_API_KEY', None)

class Command(BaseCommand):
    help = 'Chạy thử nghiệm FULL FLOW (Bao gồm cả Low-Level Reflection)'

    def handle(self, *args, **kwargs):
        # 1. CẤU HÌNH
        symbol = "HPG" 
        # Chọn ngày có dữ liệu để test
        test_date = datetime.date(2024, 1, 15) 
        
        self.stdout.write(self.style.SUCCESS(f"--- BẮT ĐẦU TEST TOÀN DIỆN CHO {symbol} NGÀY {test_date} ---"))

        # ---------------------------------------------------------
        # BƯỚC 1: CHUẨN BỊ DỮ LIỆU
        # ---------------------------------------------------------
        self.stdout.write("\n[1] Đang lấy dữ liệu từ Database...")
        
        # 1.1 Kiểm tra dữ liệu tồn tại
        if not ThiTruongChungKhoang.objects.filter(congTy__maChungKhoan=symbol, ngay=test_date).exists():
            self.stdout.write(self.style.ERROR(f"Lỗi: Không có dữ liệu giá ngày {test_date}"))
            return

        # 1.2 Lấy dữ liệu Text cho Market Intelligence (Step 1-3)
        try:
            news_text = get_formatted_news(symbol, test_date)
            fin_text = get_formatted_financials(symbol, test_date)
            price_text_str = get_price_action(symbol, test_date) # Dạng String cho Step 1
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Lỗi Data Service: {e}"))
            return

        # 1.3 Tính toán Price Movements (Dạng Dict) cho Low-Level Reflection (Step 4)
        # Vì hàm get_price_action trả về string, ta cần tính lại dạng số để gửi vào JSON
        self.stdout.write("[+] Đang tính toán biến động giá chi tiết...")
        price_movements = self.calculate_price_movements_dict(symbol, test_date)

        # ---------------------------------------------------------
        # BƯỚC 2: KHỞI TẠO AGENT
        # ---------------------------------------------------------
        if not api_key:
             self.stdout.write(self.style.ERROR("Thiếu API KEY!"))
             return
        
        # Dùng class mới FinAgentSystem
        agent = FinAgentSystem(api_key=api_key)

        try:
            # ---------------------------------------------------------
            # BƯỚC 3: CHẠY MARKET INTELLIGENCE (Step 1 -> 3)
            # ---------------------------------------------------------
            self.stdout.write("\n" + "="*50)
            self.stdout.write("MODULE 1: MARKET INTELLIGENCE")
            self.stdout.write("="*50)

            # Step 1: Analyze Latest
            self.stdout.write("-> Step 1: Phân tích tin tức hiện tại...")
            latest = agent.step_1_analyze_latest(symbol, str(test_date), news_text, fin_text, price_text_str)
            if not latest: return

            # Step 2: Retrieve History (Market Memory)
            self.stdout.write("-> Step 2: Truy vấn ký ức thị trường (Market Memory)...")
            # Lưu ý: Nếu DB rỗng thì sẽ không ra gì, không sao cả
            market_history = agent.step_2_retrieve_history(latest.get('queries'))

            # Step 3: Synthesize
            self.stdout.write("-> Step 3: Tổng hợp Insight...")
            final_insight = agent.step_3_synthesize(latest, market_history)
            
            # In kết quả Module 1
            print(json.dumps(final_insight, indent=2, ensure_ascii=False))

            # ---------------------------------------------------------
            # BƯỚC 4: CHẠY LOW-LEVEL REFLECTION (Step 4)
            # ---------------------------------------------------------
            self.stdout.write("\n" + "="*50)
            self.stdout.write("MODULE 2: LOW-LEVEL REFLECTION")
            self.stdout.write("="*50)
            self.stdout.write("(Phân tích mối quan hệ giữa Tin tức ở trên và Giá thực tế)")

            # Step 4: Reflection
            self.stdout.write("-> Step 4: Đang suy luận nguyên nhân biến động giá...")
            
            # Gọi hàm step_4 mới tích hợp
            reflection_result = agent.step_4_low_level_reflection(
                symbol=symbol,
                date_str=str(test_date),
                market_intelligence=final_insight, # Đầu vào là kết quả của Step 3
                price_movements=price_movements,   # Đầu vào là dict giá vừa tính
                kline_image_path=None              # Tạm thời chưa có ảnh
            )

            # In kết quả Module 2
            if reflection_result:
                self.stdout.write(self.style.SUCCESS("\n>>> KẾT QUẢ REFLECTION (LÝ DO GIÁ CHẠY):"))
                print(json.dumps(reflection_result, indent=2, ensure_ascii=False))
                
                # Highlight phần quan trọng
                pattern = reflection_result.get('learned_pattern')
                print(f"\n[PHÁT HIỆN MẪU HÌNH]: {pattern}")
            else:
                self.stdout.write(self.style.ERROR("Step 4 trả về rỗng."))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"CRITICAL ERROR: {e}"))
            import traceback
            traceback.print_exc()

        self.stdout.write(self.style.SUCCESS("\n--- TEST HOÀN TẤT ---"))

    def calculate_price_movements_dict(self, symbol, date):
        """Hàm phụ trợ để tính toán giá dạng Dict cho Step 4"""
        prices = ThiTruongChungKhoang.objects.filter(
            congTy__maChungKhoan=symbol, ngay__lte=date
        ).order_by('-ngay')[:90] # Lấy dữ liệu 3 tháng

        if not prices: return {}
        
        p0 = prices[0].giaDongCua # Giá hiện tại
        p1 = prices[1].giaDongCua if len(prices) > 1 else p0 # Giá hôm qua
        p5 = prices[5].giaDongCua if len(prices) > 5 else p0 # Giá tuần trước
        p20 = prices[20].giaDongCua if len(prices) > 20 else p0 # Giá tháng trước

        def calc_change(now, prev):
            if prev == 0: return "0%"
            return f"{((now - prev) / prev) * 100:.2f}%"

        short_term_desc = "Increase" if p0 > p1 else ("Decrease" if p0 < p1 else "Sideway")

        return {
            "short_term": calc_change(p0, p1),
            "medium_term": calc_change(p0, p5),
            "long_term": calc_change(p0, p20),
            "short_term_desc": short_term_desc
        }