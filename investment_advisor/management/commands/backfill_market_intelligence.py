from django.core.management.base import BaseCommand
from ...models import CongTy, ThiTruongChungKhoang
from ...gemeni_system import FinAgentMarketIntelligence
from ...utils import get_formatted_news, get_formatted_financials, get_price_action
import datetime
import time
import os
from django.conf import settings

api_key = os.environ.get("GEMINI_API_KEY") or getattr(settings, 'GEMINI_API_KEY', None)

class Command(BaseCommand):
    help = 'Chạy backfill dữ liệu lịch sử vào Vector DB (FULL FLOW)'

    def handle(self, *args, **kwargs):
        symbol = "HPG" 
        # Chạy từ quá khứ xa để tích lũy kinh nghiệm
        start_date = datetime.date(2025, 12, 1) 
        end_date = datetime.date(2025, 12, 3)
        
        agent = FinAgentMarketIntelligence(api_key=api_key)

        current_date = start_date
        
        self.stdout.write(f"--- BẮT ĐẦU BACKFILL CHO {symbol} ---")

        while current_date <= end_date:
            # 1. Kiểm tra có dữ liệu giao dịch không (Bỏ qua T7, CN, ngày lễ)
            has_data = ThiTruongChungKhoang.objects.filter(
                congTy__maChungKhoan=symbol, ngay=current_date
            ).exists()
            
            if has_data:
                self.stdout.write(f"Đang xử lý ngày: {current_date}...")
                
                try:
                    # --- BƯỚC CHUẨN BỊ DỮ LIỆU ---
                    news = get_formatted_news(symbol, current_date)
                    fins = get_formatted_financials(symbol, current_date)
                    prices = get_price_action(symbol, current_date)

                    # --- STEP 1: PHÂN TÍCH HIỆN TẠI ---
                    latest_analysis = agent.step_1_analyze_latest(
                        symbol, str(current_date), news, fins, prices
                    )
                    
                    if latest_analysis:
                        # --- STEP 2: TRUY VẤN QUÁ KHỨ (RAG) ---
                        queries = latest_analysis.get('queries', {})
                        historical_context = agent.step_2_retrieve_history(queries)
                        
                        # --- STEP 3: TỔNG HỢP ---
                        final_insight = agent.step_3_synthesize(latest_analysis, historical_context)
                        
                        if final_insight:
                            # --- STEP 4: LƯU VÀO MEMORY ---
                            agent.save_to_memory(
                                symbol, 
                                str(current_date), 
                                latest_analysis['summary'], 
                                final_insight 
                            )
                            self.stdout.write(self.style.SUCCESS(f"-> Đã lưu ký ức ngày {current_date}"))
                        else:
                            self.stdout.write(self.style.WARNING(f"-> Bỏ qua lưu ngày {current_date} do lỗi Step 3"))
                    
                    # --- THAY ĐỔI Ở ĐÂY ---
                    self.stdout.write("Đang nghỉ 60 giây để tránh giới hạn API...")
                    time.sleep(60) # Nghỉ 1 phút giữa các lần chạy

                except Exception as e:
                      self.stdout.write(self.style.ERROR(f"Lỗi ngày {current_date}: {e}"))

            current_date += datetime.timedelta(days=1)
            
        self.stdout.write(self.style.SUCCESS('--- BACKFILL HOÀN TẤT ---'))