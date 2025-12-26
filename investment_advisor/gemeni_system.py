import os
import google.genai as genai
import json
import logging
from typing import List, Dict, Any
from Thesis import settings
import chromadb
from django.conf import settings

logger = logging.getLogger(__name__)

class FinAgentSystem:  # ĐÃ ĐỔI TÊN TỪ FinAgentMarketIntelligence
    def __init__(self, api_key=None):
        """
        Khởi tạo hệ thống FinAgent với đa tầng ký ức.
        """
        # 1. Xử lý API Key
        if not api_key:
            api_key = os.environ.get("GEMINI_API_KEY") or getattr(settings, 'GEMINI_API_KEY', None)
        
        if not api_key:
            raise ValueError("Vui lòng đặt GEMINI_API_KEY trong biến môi trường hoặc settings.py.")

        # 2. Khởi tạo Client (New SDK)
        self.client = genai.Client(api_key=api_key)
        self.model_name = "gemini-2.5-flash" 

        # 3. Cấu hình Vector DB (ChromaDB)
        # PersistentClient giúp dữ liệu không bị mất khi restart server
        self.chroma_client = chromadb.PersistentClient(path="./chroma_db_storage")
        
        # --- KHỞI TẠO 3 TẦNG KÝ ỨC ---
        # Tầng 1: Market Intelligence (Tin tức & Sự kiện vĩ mô)
        self.market_memory = self.chroma_client.get_or_create_collection(name="market_memory")
        
        # Tầng 2: Low-Level Reflection (Mối quan hệ Tin tức - Giá)
        self.low_level_memory = self.chroma_client.get_or_create_collection(name="low_level_memory")
        
        # Tầng 3: High-Level Reflection (Kinh nghiệm/Chiến lược giao dịch)
        self.high_level_memory = self.chroma_client.get_or_create_collection(name="high_level_memory")


    # =========================================================================
    # MODULE 1: MARKET INTELLIGENCE (LMI)
    # =========================================================================

    def run_latest_market_intelligence(self, symbol, date_str, news_text, financial_text, price_text):

        prompt = f"""
            You are the 'Latest Market Intelligence' module analyzing {symbol} on {date_str}.
            
            **INPUT DATA:**
            1. Financials: {financial_text}
            2. Price Action: {price_text}
            3. News: {news_text}

            **TASK:**
            Based on the above information, you should analyze the key insights and summarize the market intelligence. 
            Please strictly follow the following constraints and output formats:

            **"analysis"**: 
            This field is used to extract key insights from the above information. You should analyze step-by-step:
            1. Extract the key insights that can represent this market intelligence.
            2. Analyze the market effects duration (SHORT-TERM, MEDIUM-TERM, LONG-TERM).
            3. Analyze the market sentiment (POSITIVE, NEGATIVE, NEUTRAL).
            4. The analysis you provide should be a concise and clear paragraph.

            **"summary"**: 
            This field is used to summarize the above analysis and extract key investment insights.
            1. Because this field is primarily used for decision-making in trading tasks, you should focus primarily on asset-related key investment insights.
            2. You should provide an overall analysis of all the market intelligence, explicitly provide a market sentiment (POSITIVE, NEGATIVE, or NEUTRAL) and provide a reasoning for the analysis.
            3. The summary you provide should be concise and clear.

            **"queries"**: 
            This field will be used to retrieve past market intelligence based on the duration of effects on asset prices.
            1. Because this field is primarily used for retrieving past market intelligence based on the duration of effects on asset prices, you should focus primarily on asset related key insights and duration of effects.
            2. Please combine the analysis of market intelligence on similar duration of effects on asset prices.
            3. You should provide a query text for each duration of effects on asset prices (short_term, medium_term, long_term).
            4. The query text that you provide should be primarily keywords from the original market intelligence contained.

            **OUTPUT FORMAT (JSON):**
            {{
                "analysis": "New AR/VR headset anticipated at WWDC, significant interest shown... (Duration: MEDIUM-TERM, Sentiment: POSITIVE)",
                "summary": "Positive sentiment prevails with expectations around Apple's new AR/VR... The overall market sentiment appears POSITIVE in the medium term...",
                "queries": {{
                    "short_term_query": "Customer withdrawals challenges, Meta Quest 3 competitive pressure...",
                    "medium_term_query": "WWDC Apple AR/VR headset expectations...",
                    "long_term_query": "NSA spy allegations, CEO pay adjustments..."
                }}
            }}
            """

        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config={'response_mime_type': 'application/json'}
            )
            result = json.loads(response.text)
            
            # --- LƯU VÀO MEMORY (Chỉ lưu LMI) ---
            if result:
                self._save_to_market_memory(symbol, date_str, result)
                
            return result
        except Exception as e:
            logger.error(f"Error LMI: {e}")
            return None


    def run_past_market_intelligence(self, lmi_result, historical_context):
        
        # 1. Chuẩn bị Context đầu vào
        # Kết hợp kết quả từ bước LMI và dữ liệu tìm thấy từ RAG
        context_input = f"""
        [LATEST MARKET INTELLIGENCE (FROM LMI MODULE)]:
        {json.dumps(lmi_result, indent=2)}

        [RETRIEVED PAST CONTEXT (FROM RAG)]:
        {historical_context}
        """

        # 2. Prompt chuẩn theo 'image_bd00c4.png'
        prompt = f"""
        You are the 'Past Market Intelligence' module. 
        Based on the above information (Latest Market Intelligence + Historical Context), you should analyze the key insights and summarize the market intelligence.
        
        {context_input}

        **Please strictly follow the following constraints:**

        **1. ANALYSIS SECTION:**
        - Disregard UNRELATED market intelligence.
        - For relevant market intelligence, extract key insights:
          - Extract key insights representing this intelligence. Do NOT contain IDs or asset symbols.
          - Analyze EFFECTS DURATION: Select ONLY one: SHORT-TERM, MEDIUM-TERM, or LONG-TERM.
          - Analyze SENTIMENT: Select ONLY one: POSITIVE, NEGATIVE, or NEUTRAL.
        
        **2. SUMMARY SECTION:**
        - Summarize the above analysis and extract key investment insights.
        - Focus primarily on asset-related key investment insights for decision-making.
        - Combine and summarize intelligence on similar sentiment tendencies and durations.
        - Provide an OVERALL ANALYSIS explicitly providing a market sentiment (POSITIVE, NEGATIVE, or NEUTRAL) and reasoning.
        - Concise and clear, no more than 300 tokens.

        **OUTPUT FORMAT (Strict JSON):**
        {{
            "analysis": "Analysis that you provided for market intelligence...",
            "summary": "The summary that you provided..."
        }}
        """
        
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config={'response_mime_type': 'application/json'}
            )
            return json.loads(response.text)
        except Exception as e:
            logger.error(f"Error PMI: {e}")
            return None

    def _save_to_market_memory(self, symbol, date_str, lmi_result):

        summary = lmi_result.get('summary', '')
        analysis = lmi_result.get('analysis', '')
        queries = lmi_result.get('queries', {})

        # Danh sách các tài liệu cần lưu (Batch Upsert)
        documents = []
        metadatas = []
        ids = []

        # 1. LƯU BẢN GHI TỔNG HỢP (SUMMARY)
        # Để phục vụ việc đọc hiểu tổng quan
        documents.append(f"Summary: {summary}\nFull Analysis: {analysis}")
        metadatas.append({
            "symbol": symbol,
            "date": date_str,
            "type": "LMI_SUMMARY",
            "duration": "ALL"
        })
        ids.append(f"{symbol}_{date_str}_SUMMARY")

        # 2. LƯU TÁCH BIỆT THEO DURATION (Diversified Retrieval)
        # Duyệt qua các loại query: short_term, medium_term, long_term
        term_mapping = {
            "short_term_query": "SHORT-TERM",
            "medium_term_query": "MEDIUM-TERM",
            "long_term_query": "LONG-TERM"
        }

        for query_key, duration_label in term_mapping.items():
            query_text = queries.get(query_key)
            
            # Chỉ lưu nếu có query text hợp lệ
            if query_text:
                # [QUAN TRỌNG] Paper nói: dùng "query text field" để phục vụ retrieval task
                # Nên nội dung của Vector này chính là Query Text (chứa nhiều keywords ngữ nghĩa)
                # Kèm theo Summary để khi retrieve về Agent vẫn hiểu ngữ cảnh.
                content_to_vectorize = f"Retrieval Keywords: {query_text}\nContext: {summary}"
                
                # Metadata chi tiết cho từng Duration
                meta = {
                    "symbol": symbol,
                    "date": date_str,
                    "type": "LMI_PART",
                    "duration": duration_label, # Metadata quan trọng để lọc (Filter)
                    "query_text": query_text    # Lưu query gốc vào meta để tham khảo
                }

                documents.append(content_to_vectorize)
                metadatas.append(meta)
                # ID phải là duy nhất cho từng duration: VD: HPG_2024-01-15_SHORT
                ids.append(f"{symbol}_{date_str}_{duration_label}")

        # 3. Thực hiện Upsert một lần (Batch)
        try:
            if documents:
                self.market_memory.upsert(
                    documents=documents,
                    metadatas=metadatas,
                    ids=ids
                )
                logger.info(f"Saved Diversified Memory for {symbol} on {date_str} ({len(ids)} records)")
        except Exception as e:
            logger.error(f"Error saving Diversified LMI: {e}")



    # =========================================================================
    # MODULE 2: LOW-LEVEL REFLECTION (LLR) & PAST RETRIEVAL (PLLR)
    # =========================================================================

    def run_low_level_reflection(self, symbol, date_str, market_summary, price_text, kline_text, kline_image_path=None):
        """
        [LLR Module] Phân tích mối quan hệ giữa Tin tức và Giá (Price & Chart).
        Prompt chuẩn theo 'image_4629a8.png' và 'image_4629c9.png'.
        Input:
         - market_summary: Tóm tắt từ module PMI/LMI.
         - price_text: Dữ liệu giá (Price movements).
         - kline_text: Mô tả kỹ thuật (MA, Bollinger Bands) theo 'image_4626c5.jpg'.
        """
        
        # 1. Chuẩn bị nội dung (Text + Image)
        contents = []
        
        # Nếu có ảnh biểu đồ nến thì đưa vào (Multimodal)
        if kline_image_path:
            try:
                from PIL import Image
                img = Image.open(kline_image_path)
                contents.append(img)
            except Exception as e:
                logger.warning(f"Could not load image: {e}")

        # 2. Xây dựng Prompt (Copy text từ ảnh image_4629a8.png)
        prompt_text = f"""
        You are the 'Low-level Reflection' module analyzing {symbol} on {date_str}.

        **INPUT INFORMATION:**
        1. Market Intelligence Summary: {market_summary}
        2. Price Movements: {price_text}
        3. Kline Chart Analysis: {kline_text}

        **TASK:**
        Based on the above information, you should analyze the summary of market intelligence and the Kline chart on the reasoning that lead to past to feature price movements. Then output the results as the following constraints:

        **"reasoning"**: This field will be used for trading decisions. You should think step-by-step and provide the detailed reasoning to determine how the summary of market intelligence and Kline chart that lead to the price movements. Please strictly follow the following constraints and output formats:
        1. There should be three fields under this field, corresponding to the three time horizons: "short_term_reasoning", "medium_term_reasoning", and "long_term_reasoning".
        2. For the reasoning of each time horizon, you should analyze step-by-step and follow the rules as follows and do not miss any of them:
           - Price movements should involve a shift in trend from the past to the future.
           - You should analyze the summary of market intelligence that lead to the price movements. And you should pay MORE attention to the effect of latest market intelligence on price movements.
           - You should conduct a thorough analysis of the Kline chart, focusing on price changes. And provide the reasoning driving these price movements.
           - Consider 'Momentum': The tendency of asset prices to keep moving in their current direction. Securities that performed well/poorly in the past are likely to continue doing so.
           - The reasoning you provide for each time horizon should be concise and clear, with no more than 300 tokens.

        **"query"**: This field will be used to retrieve past reasoning for price movements.
        1. Analyzing and summarizing reasoning of each time horizon, condensing it into a concise sentence of no more than 100 tokens to extract key information.

        **OUTPUT FORMAT (Strict JSON - Mapping from XML in image_4629c9.png):**
        {{
            "reasoning": {{
                "short_term_reasoning": "Reasoning about Short-Term price movements...",
                "medium_term_reasoning": "Reasoning about Medium-Term price movements...",
                "long_term_reasoning": "Reasoning about Long-Term price movements..."
            }},
            "query": "The key sentence utilized to retrieve past reasoning for price movements..."
        }}
        """
        contents.append(prompt_text)

        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=contents,
                config={'response_mime_type': 'application/json'}
            )
            result = json.loads(response.text)
            
            # --- LƯU VÀO MEMORY ---
            if result:
                self._save_to_low_level_memory(symbol, date_str, result)

            return result
        except Exception as e:
            logger.error(f"Error LLR: {e}")
            return None

    def retrieve_past_low_level_reflection(self, llr_result):
        """
        [PLLR Retrieval] Sử dụng 'query' sinh ra từ LLR để tìm kiếm quá khứ.
        (Step 06 trong Flow image_097caa.png)
        """
        query_text = llr_result.get('query')
        if not query_text:
            return "No query generated for retrieval."

        try:
            # Query vào low_level_memory
            results = self.low_level_memory.query(
                query_texts=[query_text],
                n_results=2 # Lấy Top 2 kết quả tương tự nhất
            )
            
            context_list = []
            if results['documents']:
                for doc, meta in zip(results['documents'][0], results['metadatas'][0]):
                    context_list.append(f"- Past Reflection ({meta['date']}): {doc}")
            
            return "\n".join(context_list) if context_list else "No similar past reflections found."
            
        except Exception as e:
            logger.error(f"Error Retrieval PLLR: {e}")
            return "Error retrieving history."

    def _save_to_low_level_memory(self, symbol, date_str, llr_result):
        """
        Lưu kết quả LLR vào Vector DB.
        """
        # Lấy dữ liệu
        reasoning = llr_result.get('reasoning', {})
        query_text = llr_result.get('query', '')
        
        # Gộp nội dung reasoning lại để lưu trữ
        # [QUAN TRỌNG] Paper dùng 'query' để vector hóa (embedding) phục vụ tìm kiếm
        # Nhưng nội dung (document) trả về phải chứa Reasoning để đọc hiểu.
        
        full_content = f"""
        Query: {query_text}
        Short-Term: {reasoning.get('short_term_reasoning')}
        Medium-Term: {reasoning.get('medium_term_reasoning')}
        Long-Term: {reasoning.get('long_term_reasoning')}
        """
        
        # Metadata
        meta = {
            "symbol": symbol,
            "date": date_str,
            "type": "LLR",
            "query_text": query_text # Lưu query gốc
        }

        try:
            # Upsert
            self.low_level_memory.upsert(
                documents=[full_content], # Nội dung để đọc
                metadatas=[meta],
                ids=[f"{symbol}_{date_str}_LLR"]
                # Lưu ý: ChromaDB sẽ embed 'documents' mặc định. 
                # Nếu muốn embed bằng 'query', ta cần custom embedding function hoặc trick 'documents' = query.
                # Ở đây ta lưu full_content để search semantic chung, vẫn ổn.
            )
            logger.info(f"Saved LLR to Memory: {symbol} {date_str}")
        except Exception as e:
            logger.error(f"Save LLR Error: {e}")



    # =========================================================================
    # MODULE 3: HIGH-LEVEL REFLECTION (HLR) & PAST RETRIEVAL (PHLR)
    # =========================================================================

    def run_high_level_reflection(self, symbol, date_str, market_summary, llr_reasoning, past_decisions, trading_chart_path=None):
        """
        [HLR Module] Phân tích và phản ánh lại các quyết định giao dịch dựa trên bức tranh toàn cảnh.
        
        INPUTS:
          1. market_summary: Tóm tắt tin tức vĩ mô (từ Module 1).
          2. llr_reasoning: Lý luận phân tích quan hệ tin-giá (từ Module 2).
          3. past_decisions: Lịch sử lệnh và lý do cũ.
          4. trading_chart_path: Ảnh biểu đồ Trading (Buy/Sell points).
        """
        
        # 1. Chuẩn bị nội dung (Multimodal: Text + Image)
        contents = []

        # Xử lý ảnh Trading Chart (Giống logic LLR)
        if trading_chart_path:
            try:
                from PIL import Image
                img = Image.open(trading_chart_path)
                contents.append(img)
            except Exception as e:
                logger.warning(f"Could not load trading chart image: {e}")
        else:
            # Nếu không có ảnh, HLR vẫn chạy nhưng sẽ thiếu dữ liệu thị giác quan trọng
            logger.warning("HLR running without trading chart image.")

        # 2. Xây dựng Prompt (Dạng Text tự nhiên, không dùng HTML)
        prompt_text = f"""
        You are an expert trader providing high-level reflection on past trading decisions for {symbol} on {date_str}.

        **INPUT INFORMATION:**
        1. Market Intelligence Context (Summaries of Latest & Past): {market_summary}
        2. Low-Level Reflection Reasoning (Price-News Relation): {llr_reasoning}
        3. Historical Trading Decisions & Reasoning: {past_decisions}
        4. Trading Chart: (Refer to the attached image containing Adj Close price movements, Buy/Sell markers, and Cumulative Returns).

        **TASK:**
        Based on the provided information (Market Context, LLR Reasoning, Visual Chart, and Past Decisions), you should think step-by-step to provide detailed analysis and summary to highlight key investment insights.

        Please strictly follow the constraints below for your output:

        **"reasoning"**: 
        Reflect on whether the decisions made at each point in time were right or wrong.
        - Did the decision align with the Market Intelligence and LLR reasoning available at that time?
        - Did the decision lead to a profit (Right) or loss/missed opportunity (Wrong) based on the chart?
        - Analyze contributing factors: market intelligence accuracy, technical signals on the chart, and price movements.

        **"improvement"**: 
        If there were bad decisions, how would you revise them to maximize return?
        - Suggest specific corrective actions for each identified mistake (e.g., "2023-01-03: HOLD to BUY").
        - Provide a detailed list of improvements explaining why the revision is better.

        **"summary"**: 
        Provide a summary of the lessons learnt from the successes and mistakes. Draw connections between the signals (Market/LLR) and the actual outcomes to be adapted to future trading decisions.

        **"query"**: 
        Analyze and summarize the "summary", condensing it into a concise sentence (no more than 1000 tokens) to extract key information. This field will be used to retrieve this reflection in the future.

        **OUTPUT FORMAT (Strict JSON):**
        {{
            "reasoning": "Detailed reflection regarding right/wrong decisions...",
            "improvement": "List of improvements or corrective actions...",
            "summary": "Summary of lessons learnt...",
            "query": "Key sentence for retrieval..."
        }}
        """
        contents.append(prompt_text)

        try:
            # Gọi Gemini API
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=contents,
                config={'response_mime_type': 'application/json'}
            )
            result = json.loads(response.text)

            # --- LƯU VÀO MEMORY ---
            if result:
                self._save_to_high_level_memory(symbol, date_str, result)

            return result

        except Exception as e:
            logger.error(f"Error HLR: {e}")
            return None

    def retrieve_past_high_level_reflection(self, hlr_query_text=None, current_market_context=None):
        """
        [PHLR Retrieval] Truy xuất bài học HLR quá khứ.
        """
        # Ưu tiên dùng context hiện tại để tìm bài học cũ
        query = current_market_context if current_market_context else hlr_query_text
        
        if not query:
            return "No query provided for PHLR retrieval."

        try:
            # Query vào high_level_memory
            results = self.high_level_memory.query(
                query_texts=[query],
                n_results=2 
            )

            context_list = []
            if results['documents']:
                for doc, meta in zip(results['documents'][0], results['metadatas'][0]):
                    context_list.append(f"--- LESSON LEARNED ({meta['date']}) ---\n{doc}")

            return "\n".join(context_list) if context_list else "No relevant past trading lessons found."

        except Exception as e:
            logger.error(f"Error Retrieval PHLR: {e}")
            return "Error retrieving HLR history."

    def _save_to_high_level_memory(self, symbol, date_str, hlr_result):
        """
        Lưu kết quả HLR vào Vector DB.
        """
        summary = hlr_result.get('summary', '')
        improvement = hlr_result.get('improvement', '')
        # reasoning = hlr_result.get('reasoning', '') # Tùy chọn lưu
        query_text = hlr_result.get('query', '')

        # Nội dung document tập trung vào Bài học và Cải thiện
        full_content = f"""
        Query/Context: {query_text}
        Mistakes & Improvements: {improvement}
        KEY LESSONS: {summary}
        """

        meta = {
            "symbol": symbol,
            "date": date_str,
            "type": "HLR",
            "query_text": query_text 
        }

        try:
            self.high_level_memory.upsert(
                documents=[full_content],
                metadatas=[meta],
                ids=[f"{symbol}_{date_str}_HLR"]
            )
            logger.info(f"Saved HLR (Lessons) to Memory: {symbol} {date_str}")
        except Exception as e:
            logger.error(f"Save HLR Error: {e}")



    # =========================================================================
    # MODULE 4: DECISION MAKING (FINAL OUTPUT)
    # =========================================================================

    def run_decision_making(self, symbol, date_str, 
                            market_intelligence, llr_reflection, hlr_reflection,
                            technical_signals, account_status):
        """
        [Decision Module] Tổng hợp thông tin để ra quyết định Mua/Bán.
        
        Logic dựa trên các hình ảnh:
         - Strategies & Prompt Rules: image_fa071f.png
         - Output Format: image_fa073e.png
        
        Input:
          - symbol (str): Mã cổ phiếu.
          - market_intelligence (str): Tổng hợp tin tức (LMI + PMI).
          - llr_reflection (str): Phân tích xu hướng giá (LLR).
          - hlr_reflection (str): Bài học kinh nghiệm (HLR).
          - technical_signals (str): Giá trị các chỉ báo (MACD, RSI, KDJ...) để áp dụng Strategy.
          - account_status (dict): {"cash": float, "position": int} (Để check rule Cash/Position).
        """

        # 1. Xây dựng Prompt
        
        system_role = """You are an expert trader who have sufficient financial experience and provides expert guidance. 
        Imagine working in a real market environment where you have access to various types of information relevant to financial markets. 
        You are capable of deeply analyzing, understanding, and summarizing information to make informed and wise trading decisions (i.e., BUY, HOLD and SELL)."""

        prompt_text = f"""
        {system_role}

        **TASK DESCRIPTION:**
        You are currently targeting the trading decisions of **{symbol}** on {date_str}.
        Your objective is to make correct trading decisions considering step-by-step reasoning based on the following comprehensive set of information.

        **1. MARKET INTELLIGENCE (Latest & Past):**
        {market_intelligence}

        **2. LOW-LEVEL REFLECTION (Price Movements & Trends):**
        Analysis of price movements across three time horizons (Short, Medium, Long-Term):
        {llr_reflection}

        **3. HIGH-LEVEL REFLECTION (Past Decisions & Lessons):**
        Reflections on past trading decisions, evaluating correctness, and lessons learned:
        {hlr_reflection}

        **4. TRADING STRATEGIES & TECHNICAL SIGNALS:**
        Current Technical Signals: {technical_signals}
        
        **Apply the following strategies to the current signals:**
        - **Strategy 1 (MACD Crossover)**: Generates BUY when MACD line crosses above signal line (bullish), and SELL when below (bearish). Ideal for trending markets.
        - **Strategy 2 (KDJ with RSI Filter)**: Works best in ranging markets. Uses KDJ for momentum and RSI to pinpoint reversals.
        - **Strategy 3 (Mean Reversion)**: Assumes prices revert to mean. BUY when Z-score indicates oversold, SELL when overbought.

        **5. ACCOUNT STATUS (Current Situation):**
        - Available Cash: {account_status.get('cash', 0)}
        - Current Position (Shares held): {account_status.get('position', 0)}

        **DECISION MAKING INSTRUCTIONS:**
        Based on the above information, step-by-step analyze the summary to provide the reasoning for BUY, SELL, or HOLD. Strictly follow these rules:

        1. **Market Sentiment**: Analyze if market intelligence is Positive, Negative, or Neutral.
        2. **Price Trend**: Determine if future trend is Bullish or Bearish based on LLR.
           - If Bullish -> Consider BUY.
           - If Bearish -> Consider SELL.
        3. **Lessons Learned**: Apply lessons from High-Level Reflection. If you missed a BUY/SELL opportunity before in similar context, act accordingly now.
        4. **Strategies**: Evaluate the signals using the 3 strategies above.
        5. **Weightage**: 
           - If sentiment is Neutral, pay less attention to it.
           - Pay more attention to intelligence causing immediate price impact.
           - If signals are mixed, trust the Professional Guidance/Historical reliability.
        6. **CRITICAL PRE-CHECK (Rule #9 - Mandatory):** - **If Cash is lower than current Price -> DO NOT BUY.** (Insufficient funds).
           - **If Current Position is 0 -> DO NOT SELL.** (No shares to sell).
        7. **Final Decision**: Combine all analysis to determine BUY, SELL, or HOLD.

        **OUTPUT FORMAT (Strict JSON):**
        {{
            "analysis": "Step-by-step analysis of Market, Trend, Strategies, and Account Status...",
            "action": "BUY" or "SELL" or "HOLD",
            "reasoning": "Concise reasoning for the final action..."
        }}
        """
        
        try:
            # Gọi Gemini API
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt_text,
                config={'response_mime_type': 'application/json'}
            )
            return json.loads(response.text)

        except Exception as e:
            logger.error(f"Error Decision Making: {e}")
            return None





