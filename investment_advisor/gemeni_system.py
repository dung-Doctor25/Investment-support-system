import os
import google.genai as genai
import json
import logging
from typing import List, Dict, Any

from Thesis import settings


# gemini_agent.py
import os
import json
import logging
import chromadb
from google import genai
from google.genai import types
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
    # MODULE 1: MARKET INTELLIGENCE (Steps 1, 2, 3)
    # =========================================================================

    def step_1_analyze_latest(self, symbol, date_str, news_text, financial_text, price_text):
        """Phân tích dữ liệu hiện tại để lấy Sentiment & Query"""
        prompt = f"""
        You are a financial expert analyzing {symbol} on date {date_str}.
        
        **LATEST MARKET DATA:**
        1. FINANCIAL REPORTS:
        {financial_text}
        
        2. PRICE ACTION (Recent):
        {price_text}
        
        3. TODAY'S NEWS:
        {news_text}
        
        **YOUR TASKS:**
        1. Analyze the sentiment (Positive/Negative/Neutral) and the impact duration.
        2. Generate "Diversified Retrieval Queries" to find SIMILAR EVENTS in the past history.
           - Short-term query: Focus on immediate news impact.
           - Long-term query: Focus on fundamental shifts.
        3. Summarize the current situation.

        **OUTPUT JSON FORMAT:**
        {{
            "sentiment": "Positive/Negative/Neutral",
            "duration": "Short-term/Long-term",
            "summary": "Concise summary of today's situation...",
            "queries": {{
                "short": "query string...",
                "long": "query string..."
            }}
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
            logger.error(f"Error Step 1: {e}")
            return None

    def step_2_retrieve_history(self, queries):
        """Truy vấn lịch sử từ MARKET MEMORY"""
        if not queries: return ""
        historical_contexts = []
        
        for key, query_text in queries.items():
            if not query_text: continue
            try:
                results = self.market_memory.query(query_texts=[query_text], n_results=2)
                if results['documents']:
                    for doc, meta in zip(results['documents'][0], results['metadatas'][0]):
                        historical_contexts.append(f"- Past Event ({meta['date']}): {doc}")
            except Exception as e:
                logger.warning(f"Market retrieval warning: {e}")

        return "\n".join(historical_contexts) if historical_contexts else "No similar historical events found."

    def step_3_synthesize(self, latest_analysis, historical_context):
        """Tổng hợp Insight cuối cùng"""
        prompt = f"""
        Synthesize the Final Market Intelligence.

        **CURRENT ANALYSIS (Today):**
        - Sentiment: {latest_analysis.get('sentiment')}
        - Summary: {latest_analysis.get('summary')}

        **HISTORICAL LESSONS:**
        {historical_context}

        **TASK:**
        Combine current news with historical patterns. Does history support the current sentiment?

        **OUTPUT JSON:**
        {{
            "final_signal": "Bullish/Bearish/Neutral",
            "confidence": "High/Medium/Low",
            "reasoning": "Detailed explanation combining past and present...",
            "action_suggestion": "Buy/Sell/Hold"
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
            logger.error(f"Error Step 3: {e}")
            return None

    def save_market_memory(self, symbol, date_str, analysis_summary, final_insight):
        """Lưu vào MARKET MEMORY"""
        insight_text = final_insight.get('reasoning', '') if isinstance(final_insight, dict) else str(final_insight)
        content = f"Summary: {analysis_summary}. Insight: {insight_text}"
        signal = final_insight.get('final_signal', 'Neutral') if isinstance(final_insight, dict) else 'Neutral'
        
        try:
            self.market_memory.upsert(
                documents=[content],
                metadatas=[{"symbol": symbol, "date": date_str, "signal": signal, "type": "market"}],
                ids=[f"{symbol}_{date_str}_market"]
            )
            logger.info(f"Saved Market Memory for {symbol} on {date_str}")
        except Exception as e:
            logger.error(f"Error saving market memory: {e}")

    # =========================================================================
    # MODULE 2: LOW-LEVEL REFLECTION (Step 4) - ĐÃ TÍCH HỢP CODE CỦA BẠN
    # =========================================================================

    def step_4_low_level_reflection(self, 
                                    symbol: str, 
                                    date_str: str, # Thêm tham số này để dùng khi lưu DB
                                    market_intelligence: dict, 
                                    price_movements: dict, 
                                    kline_image_path: str = None) -> dict:
        """
        Thực hiện Low-level Reflection (Phân tích mối quan hệ Tin tức - Giá).
        """
        
        # 1. RAG Retrieval: Tìm kiếm các lý giải giá trong quá khứ từ LOW_LEVEL_MEMORY
        query_text = f"Reasoning for {symbol} price movement: {price_movements.get('short_term_desc', 'Unknown')}"
        
        past_context_str = ""
        try:
            results = self.low_level_memory.query(
                query_texts=[query_text],
                n_results=2
            )
            if results['documents']:
                for doc, meta in zip(results['documents'][0], results['metadatas'][0]):
                    past_context_str += f"- Past Pattern ({meta['date']}): {doc}\n"
        except Exception as e:
            logger.warning(f"Low-level retrieval warning: {e}")

        if not past_context_str:
            past_context_str = "No specific past price patterns found."

        # 2. Chuẩn bị nội dung gửi cho Gemini
        contents = []
        
        # # Xử lý hình ảnh (Nếu có)
        # if kline_image_path:
        #     try:
        #         from PIL import Image
        #         image = Image.open(kline_image_path)
        #         contents.append(image)
        #     except Exception as e:
        #         logger.error(f"Cannot load kline image: {e}")

        # 3. Tạo Prompt
        prompt = f"""
        You are the Low-level Reflection Module of FinAgent.
        Focus on analyzing the relationship between Market Intelligence and Price Movements for {symbol}.

        **Input Data:**
        1. Market Intelligence Summary: {json.dumps(market_intelligence)}
        2. Price Movements:
           - Short-term (under 1 year): {price_movements.get('short_term')}
           - Medium-term (3 - 5 years): {price_movements.get('medium_term')}
           - Long-term (over 5 years): {price_movements.get('long_term')}
        
        **Historical Lessons (Past Reasoning):**
        {past_context_str}

        **Task:**
        Analyze the data above (and the chart if provided). Explain WHY the price moved this way based on the news.
        - Did the market overreact to the news?
        - Is the price trend aligned with the sentiment?
        - IDENTIFY THE PATTERN (e.g., "Sell the news", "Panic selling", "Strong accumulation").
        
        **Output Format (JSON):**
        {{
            "reasoning": {{
                "short_term_reasoning": "Reasoning for short-term movement...",
                "medium_term_reasoning": "Reasoning for medium-term movement...",
                "long_term_reasoning": "Reasoning for long-term movement..."
            }},
            "learned_pattern": "What pattern did you learn? (e.g., Price drops despite good news due to macro factors)",
            "retrieval_query": "A concise sentence to retrieve this reasoning in the future."
        }}
        """
        
        contents.append(prompt)

        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=contents,
                config={'response_mime_type': 'application/json'}
            )
            result = json.loads(response.text)

            # --- TỰ ĐỘNG LƯU VÀO LOW-LEVEL MEMORY SAU KHI SUY LUẬN ---
            if result:
                self._save_low_level_memory(symbol, date_str, result)
            
            return result
            
        except Exception as e:
            logger.error(f"Error in Low-level Reflection: {e}")
            return {}

    def _save_low_level_memory(self, symbol, date_str, result_json):
        """Hàm phụ để lưu kết quả Low-level vào DB"""
        pattern = result_json.get('learned_pattern', 'No pattern')
        query = result_json.get('retrieval_query', '')
        
        # Nội dung lưu là Pattern + Lý do chi tiết
        content = f"Pattern: {pattern}. Detail: {json.dumps(result_json.get('reasoning'))}"
        
        try:
            self.low_level_memory.upsert(
                documents=[content],
                metadatas=[{"symbol": symbol, "date": date_str, "type": "low_level"}],
                ids=[f"{symbol}_{date_str}_low"]
            )
            logger.info(f"Saved Low-Level Memory for {symbol} on {date_str}")
        except Exception as e:
            logger.error(f"Error saving low-level memory: {e}")

 

# import google.generativeai as genai
import json
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class FinAgentReflection:
    def __init__(self, api_key: str, vector_db_client=None):
        genai.configure(api_key=api_key)
        # Model Gemini Flash hỗ trợ cả text và image (multimodal) nhanh chóng
        self.model = genai.GenerativeModel('gemini-2.5-flash',
                                           generation_config={"response_mime_type": "application/json"})
        self.vector_db = vector_db_client

    # =========================================================================
    # MODULE 1: LOW-LEVEL REFLECTION (LLR)
    # Mục tiêu: Liên kết Tin tức (Market Intelligence) với Biểu đồ giá (Kline Chart)
    # =========================================================================

    def step_4_low_level_reflection(self, 
                                    symbol: str, 
                                    market_intelligence: Dict, 
                                    price_movements: Dict, 
                                    kline_image_path: str = None) -> Dict:
        """
        Thực hiện Low-level Reflection (Phân tích mối quan hệ Tin tức - Giá).
        """
        
        # 1. RAG Retrieval: Tìm kiếm các lý giải giá trong quá khứ từ LOW_LEVEL_MEMORY
        # Tạo query dựa trên diễn biến giá ngắn hạn
        query_text = f"Reasoning for {symbol} price movement: {price_movements.get('short_term_desc', 'Unknown')}"
        
        # Sử dụng hàm helper chung _retrieve_from_collection (đã viết ở step trước)
        # Hoặc viết trực tiếp logic query nếu chưa có helper
        past_context_str = ""
        try:
            results = self.low_level_memory.query(
                query_texts=[query_text],
                n_results=2
            )
            if results['documents']:
                for doc, meta in zip(results['documents'][0], results['metadatas'][0]):
                    past_context_str += f"- Past Pattern ({meta['date']}): {doc}\n"
        except Exception as e:
            logger.warning(f"Low-level retrieval warning: {e}")

        if not past_context_str:
            past_context_str = "No specific past price patterns found."

        # 2. Chuẩn bị nội dung gửi cho Gemini (Contents List)
        contents = []
        
        # Xử lý hình ảnh (Nếu có đường dẫn ảnh)
        if kline_image_path:
            try:
                # Với SDK mới, bạn có thể gửi file path hoặc bytes
                # Cần đảm bảo thư viện PIL (Pillow) đã cài đặt: pip install Pillow
                from PIL import Image
                image = Image.open(kline_image_path)
                contents.append(image)
            except Exception as e:
                logger.error(f"Cannot load kline image: {e}")

        # 3. Tạo Prompt
        prompt = f"""
        You are the Low-level Reflection Module of FinAgent.
        Focus on analyzing the relationship between Market Intelligence and Price Movements for {symbol}.

        **Input Data:**
        1. Market Intelligence Summary: {json.dumps(market_intelligence)}
        2. Price Movements:
           - Short-term (1-5 days): {price_movements.get('short_term')}
           - Medium-term (1-4 weeks): {price_movements.get('medium_term')}
           - Long-term (1-3 months): {price_movements.get('long_term')}
        
        **Historical Lessons (Past Reasoning):**
        {past_context_str}

        **Task:**
        Analyze the data above (and the chart if provided). Explain WHY the price moved this way based on the news.
        - Did the market overreact to the news?
        - Is the price trend aligned with the sentiment?
        - IDENTIFY THE PATTERN (e.g., "Sell the news", "Panic selling", "Strong accumulation").
        
        **Output Format (JSON):**
        {{
            "reasoning": {{
                "short_term_reasoning": "Reasoning for short-term movement...",
                "medium_term_reasoning": "Reasoning for medium-term movement...",
                "long_term_reasoning": "Reasoning for long-term movement..."
            }},
            "learned_pattern": "What pattern did you learn? (e.g., Price drops despite good news due to macro factors)",
            "retrieval_query": "A concise sentence to retrieve this reasoning in the future."
        }}
        """
        
        contents.append(prompt)

        try:
            # --- SỬA ĐỔI QUAN TRỌNG: Dùng client mới ---
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=contents,
                config={'response_mime_type': 'application/json'}
            )
            return json.loads(response.text)
            
        except Exception as e:
            logger.error(f"Error in Low-level Reflection: {e}")
            return {}

    # =========================================================================
    # MODULE 2: HIGH-LEVEL REFLECTION (HLR)
    # Mục tiêu: Tự kiểm điểm các quyết định giao dịch trong quá khứ (Learning Process)
    # =========================================================================

    def step_5_high_level_reflection(self, 
                                     symbol: str, 
                                     current_market_info: Dict,
                                     past_decisions: List[Dict]) -> Dict:
        """
        Thực hiện High-level Reflection.
        Input:
            - current_market_info: Tổng hợp tin tức + LLR hiện tại.
            - past_decisions: List các quyết định cũ (Action) và Kết quả (Reward/Profit) thực tế.
              VD: [{'date': '2023-01-01', 'action': 'BUY', 'profit': '-5%', 'reason': '...'}]
        Output:
            - Reflection (Đúng/Sai).
            - Improvement (Cách sửa sai).
        """
        
        # 1. RAG Retrieval: Tìm kiếm các bài học kinh nghiệm cũ [cite: 354]
        # Query: "Reflection on mistaken BUY decision" hoặc "Lessons from successful HOLD"
        past_hlr_context = self._retrieve_past_hlr("Reflections on past trading errors and successes")
        
        # Format dữ liệu quyết định quá khứ để đưa vào Prompt
        decisions_str = "\n".join([
            f"- Date: {d['date']}, Action: {d['action']}, Result: {d['profit']}, Original Reasoning: {d['reason']}" 
            for d in past_decisions[-5:] # Chỉ lấy 5 quyết định gần nhất để soi xét
        ])

        # 2. Tạo Prompt [cite: 350-353]
        prompt = f"""
        You are the High-level Reflection Module of FinAgent. 
        Your goal is to emulate the cognitive learning process to improve future trading.

        **Current Market Context:**
        {json.dumps(current_market_info)}

        **Review of Past Decisions (Last 5 Trades):**
        {decisions_str}

        **Historical Reflections (Memory):**
        {past_hlr_context}

        **Task:**
        Reflect on the decisions above.
        1. Identify which decisions were RIGHT and which were WRONG based on the Result (Profit).
        2. For WRONG decisions: Why did we fail? (e.g., Ignored negative news? Too aggressive?)
        3. Suggest IMPROVEMENTS for the future.

        **Output Format (JSON):**
        {{
            "reflections": [
                {{
                    "date": "YYYY-MM-DD",
                    "evaluation": "Correct/Incorrect",
                    "cause_analysis": "Why it was right/wrong...",
                    "improvement_plan": "How to fix this next time (e.g., Set tighter stop-loss, wait for confirmation)"
                }}
            ],
            "general_lessons": "Summary of lessons learnt to adapt to future decisions.",
            "retrieval_query": "Key sentence to retrieve this reflection later."
        }}
        """

        try:
            response = self.model.generate_content(prompt)
            return json.loads(response.text)
        except Exception as e:
            logger.error(f"Error in High-level Reflection: {e}")
            return {}

    def _retrieve_past_hlr(self, query: str) -> str:
        """Helper: Tìm kiếm HLR trong quá khứ [cite: 385]"""
        if not self.vector_db: return ""
        # return self.vector_db.search(query)
        return "Past Lesson: Avoid BUYing immediately after CEO resignation even if price drops."