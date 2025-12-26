from django.core.management.base import BaseCommand
from investment_advisor.models import ThiTruongChungKhoang
# Import class Agent
from ...gemeni_system import FinAgentSystem 
from ...utils import get_formatted_news, get_formatted_financials, get_price_action
import datetime
import json
import os
from django.conf import settings

api_key = os.environ.get("GEMINI_API_KEY") or getattr(settings, 'GEMINI_API_KEY', None)

class Command(BaseCommand):
    help = 'Chạy thử nghiệm FinAgent với cấu trúc mới (LMI -> PMI)'

    def handle(self, *args, **kwargs):
        # 1. CẤU HÌNH
        symbol = "HPG" 
        test_date = datetime.date(2024, 1, 15) # Chọn ngày có dữ liệu
        
        self.stdout.write(self.style.SUCCESS(f"--- START TESTING FINAGENT FLOW: {symbol} on {test_date} ---"))

        # 2. LẤY DỮ LIỆU ĐẦU VÀO
        self.stdout.write("\n[1] Fetching Data...")
        if not ThiTruongChungKhoang.objects.filter(congTy__maChungKhoan=symbol, ngay=test_date).exists():
            self.stdout.write(self.style.ERROR(f"Lỗi: Không có dữ liệu giá ngày {test_date}"))
            return

        try:
            news_text = get_formatted_news(symbol, test_date)
            fin_text = get_formatted_financials(symbol, test_date)
            price_text = get_price_action(symbol, test_date)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Data Error: {e}"))
            return

        # 3. KHỞI TẠO AGENT
        if not api_key:
             self.stdout.write(self.style.ERROR("Missing API KEY"))
             return
        agent = FinAgentSystem(api_key=api_key)

        try:
            # =================================================================
            # MODULE 1.1: LATEST MARKET INTELLIGENCE (LMI)
            # =================================================================
            self.stdout.write("\n" + "="*50)
            self.stdout.write("STEP 1: RUNNING LATEST MARKET INTELLIGENCE (LMI)")
            self.stdout.write("="*50)

            lmi_result = agent.run_latest_market_intelligence(
                symbol, str(test_date), news_text, fin_text, price_text
            )
            
            if not lmi_result:
                self.stdout.write(self.style.ERROR("LMI Failed."))
                return

            # --- IN KẾT QUẢ LMI ---
            print(lmi_result)
            print(f"\n[LMI ANALYSIS]:\n{lmi_result.get('analysis')}")
            print(f"\n[LMI SUMMARY]:\n{lmi_result.get('summary')}")
            
            
            # =================================================================
            # RETRIEVAL: DIVERSIFIED RETRIEVAL OPERATION (Đã sửa)
            # =================================================================
            self.stdout.write("\n" + "-"*50)
            self.stdout.write(f"STEP 1.5: RETRIEVING HISTORY (Diversified M x K)")
            self.stdout.write("-"*50)
            
            # Mapping giữa key trong query và metadata trong DB
            # Đảm bảo bạn đã lưu metadata 'duration' là SHORT-TERM, MEDIUM-TERM... trong hàm _save_to_market_memory
            query_map = {
                "short_term_query": "SHORT-TERM",
                "medium_term_query": "MEDIUM-TERM",
                "long_term_query": "LONG-TERM"
            }
            
            queries_dict = lmi_result.get('queries', {})
            context_list = []

            # DUYỆT QUA TỪNG LOẠI QUERY ĐỂ TÌM KIẾM RIÊNG BIỆT (SEPARATELY)
            for q_key, duration_label in query_map.items():
                q_text = queries_dict.get(q_key)
                
                if q_text:
                    self.stdout.write(f"  -> Searching for {duration_label} patterns...")
                    try:
                        # Thực hiện query CÓ LỌC (Specific retrieval types assigned)
                        results = agent.market_memory.query(
                            query_texts=[q_text],
                            n_results=1, # Top K = 1
                            where={"duration": duration_label} # <--- ĐÂY LÀ CHÌA KHÓA: Chỉ tìm trong ký ức cùng loại
                        )
                        
                        if results['documents']:
                            found_doc = results['documents'][0][0]
                            found_date = results['metadatas'][0][0]['date']
                            # Ghi rõ nguồn gốc ký ức để PMI Module hiểu
                            context_list.append(f"- Past ({duration_label} pattern from {found_date}): {found_doc}")
                            
                    except Exception as e:
                        print(f"    Error retrieving {duration_label}: {e}")

            # Tổng hợp lại thành historical_context
            if context_list:
                historical_context = "\n".join(context_list)
                print(f"\nFound Diversified History:\n{historical_context}")
            else:
                historical_context = "No relevant history found (Cold start)."
                print(historical_context)

            # =================================================================
            # MODULE 1.2: PAST MARKET INTELLIGENCE (PMI)
            # =================================================================
            self.stdout.write("\n" + "="*50)
            self.stdout.write("STEP 2: RUNNING PAST MARKET INTELLIGENCE (PMI)")
            self.stdout.write("="*50)

            pmi_result = agent.run_past_market_intelligence(lmi_result, historical_context)

            if pmi_result:
                # --- IN KẾT QUẢ PMI THEO FORMAT MỚI ---
                self.stdout.write(self.style.SUCCESS("\n>>> PMI RESULT (SYNTHESIS):"))
                print(json.dumps(pmi_result, indent=2, ensure_ascii=False))
            else:
                self.stdout.write(self.style.ERROR("PMI Failed."))

            # =================================================================
            # MODULE 2: LOW-LEVEL REFLECTION (Optional Check)
            # =================================================================
            # Kiểm tra xem bạn đã implement hàm này chưa
            if hasattr(agent, 'run_low_level_reflection'):
                self.stdout.write("\n" + "="*50)
                self.stdout.write("STEP 3: CHECKING LOW-LEVEL REFLECTION")
                self.stdout.write("="*50)
                kline_description = """
                Kline chart with Moving Average (MA) and Bollinger Bands (BB).
                - MA5 is flat indicating trend pause.
                - Bollinger Bands are narrowing indicating reduced volatility.
                - Today's candle is RED (Closing price < Opening price), showing selling pressure.
                """
                # Tính toán giá (Demo)
                # ... (Logic tính giá short_term...)
                price_movements = {"short_term_desc": "Decrease", "short_term": "-1.5%"} 

                # Gọi LLR (Lưu ý: PMI mới không có 'final_signal', nên LLR cần đọc 'summary')
                # Nếu code LLR của bạn vẫn đang dùng .get('final_signal'), nó có thể bị None.
                try:
                    llr_res = agent.run_low_level_reflection(
                        symbol, str(test_date), pmi_result, price_movements, kline_description
                    )
                    if llr_res:
                        print(json.dumps(llr_res, indent=2))
                except Exception as e:
                    print(f"LLR Skipped (Code mismatch): {e}")

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"CRITICAL ERROR: {e}"))
            import traceback
            traceback.print_exc()

        # =================================================================
        # MODULE 2: LOW-LEVEL REFLECTION (LLR)
        # =================================================================
        self.stdout.write("\n" + "="*50)
        self.stdout.write("STEP 3: RUNNING LOW-LEVEL REFLECTION (LLR)")
        self.stdout.write("="*50)
        
        # Giả lập dữ liệu Kline Chart (Mô tả text vì không có ảnh thật lúc này)
        # Nội dung lấy từ image_4626c5.jpg
        kline_description = """
        Kline chart with Moving Average (MA) and Bollinger Bands (BB).
        - MA5 is flat indicating trend pause.
        - Bollinger Bands are narrowing indicating reduced volatility.
        - Today's candle is RED (Closing price < Opening price), showing selling pressure.
        """
        
        # Tính toán Price Movement (Text description)
        price_text = "Short-term: Decreased -1.5%. Medium-term: Increased +2.0%."

        # Lấy Summary từ PMI (nếu có) hoặc LMI để làm input
        market_summary_input = pmi_result.get('summary') if pmi_result else lmi_result.get('summary')

        llr_result = agent.run_low_level_reflection(
            symbol, str(test_date), 
            market_summary=market_summary_input,
            price_text=price_text,
            kline_text=kline_description,
            kline_image_path=None # Nếu có file ảnh: "path/to/chart.png"
        )

        if llr_result:
            print(f"\n[LLR REASONING]:")
            r = llr_result.get('reasoning', {})
            print(f"  Short: {r.get('short_term_reasoning')[:100]}...")
            print(f"  Medium: {r.get('medium_term_reasoning')[:100]}...")
            print(f"  Long: {r.get('long_term_reasoning')[:100]}...")
            print(f"\n[LLR QUERY]: {llr_result.get('query')}")
        else:
            self.stdout.write(self.style.ERROR("LLR Failed."))
            return

        # =================================================================
        # MODULE 2.1: RETRIEVE PAST LOW-LEVEL REFLECTION (PLLR)
        # =================================================================
        self.stdout.write("\n" + "-"*50)
        self.stdout.write("STEP 3.5: RETRIEVING PAST REFLECTIONS (PLLR)")
        self.stdout.write("-" * 50)
        
        pllr_context = agent.retrieve_past_low_level_reflection(llr_result)
        print(f"Found Past Reflections:\n{pllr_context}")




        # =================================================================
        # MODULE 3: HIGH-LEVEL REFLECTION (HLR)
        # =================================================================
        self.stdout.write("\n" + "="*50)
        self.stdout.write("STEP 4: RUNNING HIGH-LEVEL REFLECTION (HLR)")
        self.stdout.write("="*50)

        # 1. Chuẩn bị Inputs
        
        # a. LLR Reasoning: Chuyển dict thành string để đưa vào prompt
        llr_reasoning_str = json.dumps(llr_result.get('reasoning', {}), indent=2)

        # b. Past Decisions (Giả lập): Trong thực tế, bạn query từ DB Lịch sử giao dịch
        past_decisions_mock = f"""
        {test_date - datetime.timedelta(days=5)}: HOLD - Market uncertainty, waiting for news.
        {test_date - datetime.timedelta(days=3)}: BUY - Price crossed above MA20, volume increased.
        {test_date - datetime.timedelta(days=1)}: HOLD - Maintaining position, trend is still up.
        """

        # c. Trading Chart Path (Kiểm tra file tồn tại)
        # Bạn nên để một file ảnh 'test_chart.png' ở thư mục gốc để test tính năng nhìn ảnh
        trading_chart_path = "test_chart.png"
        if not os.path.exists(trading_chart_path):
            self.stdout.write(self.style.WARNING(f"Warning: File '{trading_chart_path}' not found."))
            self.stdout.write(self.style.WARNING("HLR will run in TEXT-ONLY mode (Not recommended for production)."))
            trading_chart_path = None # Set None để module tự xử lý
        else:
            self.stdout.write(self.style.SUCCESS(f"Found chart image: {trading_chart_path}"))

        # 2. Gọi hàm HLR (Lưu ý: Không truyền asset_info như yêu cầu)
        hlr_result = agent.run_high_level_reflection(
            symbol=symbol,
            date_str=str(test_date),
            market_summary=market_summary_input, # Tái sử dụng từ LMI/PMI
            llr_reasoning=llr_reasoning_str,     # Output từ Step 3
            past_decisions=past_decisions_mock,  # Lịch sử giả lập
            trading_chart_path=None # Đường dẫn ảnh (hoặc None)
        )

        if hlr_result:
            self.stdout.write(self.style.SUCCESS("\n[HLR RESULT]:"))
            print(f"  Reasoning: {hlr_result.get('reasoning')[:150]}...")
            print(f"  Improvement: {hlr_result.get('improvement')}")
            print(f"  Summary (Lessons): {hlr_result.get('summary')}")
            print(f"  Query: {hlr_result.get('query')}")
        else:
            self.stdout.write(self.style.ERROR("HLR Failed."))

        # =================================================================
        # MODULE 3.5: RETRIEVE PAST HIGH-LEVEL REFLECTION (PHLR)
        # =================================================================
        self.stdout.write("\n" + "-"*50)
        self.stdout.write("STEP 4.5: RETRIEVING TRADING LESSONS (PHLR)")
        self.stdout.write("-" * 50)

        # Test 1: Retrieve bằng Query sinh ra từ HLR
        query_from_hlr = hlr_result.get('query') if hlr_result else None
        
        # Test 2: Hoặc Retrieve bằng context thị trường hiện tại (Giả lập)
        current_market_context = "Market is showing signs of fake breakout similar to last month."

        phlr_context = agent.retrieve_past_high_level_reflection(
            hlr_query_text=query_from_hlr,
            current_market_context=current_market_context
        )
        
        print(f"Found Past Lessons:\n{phlr_context}")



        # =================================================================
        # MODULE 5: DECISION MAKING (FINAL STEP)
        # =================================================================
        self.stdout.write("\n" + "="*50)
        self.stdout.write("STEP 5: RUNNING FINAL DECISION MAKING")
        self.stdout.write("="*50)

        # 1. Chuẩn bị Inputs tổng hợp
        
        # Market Intelligence (Gộp LMI và PMI)
        # Trong thực tế, bạn lấy string 'summary' từ kết quả module 1 & 1.2
        mi_summary = lmi_result.get('summary', '')
        pmi_summary = pmi_result.get('summary', '') if pmi_result else "N/A"
        mi_input = f"Latest Summary: {mi_summary}\nPast Context: {pmi_summary}"

        # LLR Reflection (Gộp các reasoning)
        # Chuyển đổi JSON object thành String để đưa vào prompt
        llr_input = json.dumps(llr_result.get('reasoning', {}), indent=2)

        # HLR Reflection (Lấy bài học từ HLR hiện tại và quá khứ)
        hlr_current = hlr_result.get('summary', '') if hlr_result else "N/A"
        hlr_input = f"Current Reflection: {hlr_current}\nPast Lessons: {phlr_context}"

        # Technical Signals (Giả lập dữ liệu từ các chỉ báo kỹ thuật)
        # Đây là input quan trọng để Agent áp dụng Strategy 1, 2, 3
        tech_signals = """
        - MACD: MACD Line (1.5) is above Signal Line (1.2) -> Bullish Crossover.
        - RSI: 62 (Neutral-Bullish, trending up).
        - KDJ: J line is turning upwards.
        - Bollinger Bands: Price touched lower band and is bouncing back.
        - Current Price: 28,000 VND.
        """

        # Account Status (Giả lập trạng thái tài khoản để test Rule #9)
        account_status = {
            "cash": 100000000, # 100 triệu VND (Đủ tiền mua)
            "position": 0      # 0 cổ phiếu (Không thể Bán)
        }
        self.stdout.write(f"Account Status: {account_status}")

        # 2. Gọi hàm Decision (Đã bỏ asset_info)
        decision_result = agent.run_decision_making(
            symbol=symbol,
            date_str=str(test_date),
            market_intelligence=mi_input,
            llr_reflection=llr_input,
            hlr_reflection=hlr_input,
            technical_signals=tech_signals,
            account_status=account_status
        )

        if decision_result:
            self.stdout.write(self.style.SUCCESS("\n>>> FINAL TRADING DECISION <<<"))
            self.stdout.write(self.style.WARNING(f"ACTION: {decision_result.get('action')}"))
            print(f"ANALYSIS: {decision_result.get('analysis')}")
            print(f"REASONING: {decision_result.get('reasoning')}")
        else:
            self.stdout.write(self.style.ERROR("Decision Making Failed."))

        self.stdout.write(self.style.SUCCESS("\n--- FULL FINAGENT PIPELINE COMPLETE ---"))




        # =================================================================
        # KẾT THÚC TEST
        # =================================================================


        self.stdout.write(self.style.SUCCESS("\n--- TEST COMPLETE ---"))
