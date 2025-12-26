import re
import google.genai as genai
import os
import gspread
import numpy as np
import json

from django.db.models import Max, Count, Prefetch
from .models import CongTy, TongHopTaiChinh, BangCanDoiKeToan, BangKetQuaKinhDoanh, ThiTruongChungKhoang

from django.conf import settings
from google.oauth2.service_account import Credentials

def safe_divide(a, b):
    if b is None or b == 0: return 0
    return a / b

def get_financial_ratios_data():
    """
    Tính toán chỉ số tài chính cho một nhóm công ty cụ thể (đã được tối ưu Query).
    """
    target_companies_queryset=CongTy.objects.all().order_by('maChungKhoan')


    # 1. Xác định năm dữ liệu (Lấy global max year)
    latest_report = (
        TongHopTaiChinh.objects
        .exclude(congTy__maChungKhoan__in=["SCS",'a'])
        .aggregate(max_nam=Max('nam'))
    )
    latest_year = latest_report.get('max_nam')

    if not latest_year:
        return {}
    
    start_calc_year = latest_year - 4
    start_data_year = latest_year - 5 
    
    years_to_query = list(range(start_data_year, latest_year + 1))
    years_to_calculate = list(range(start_calc_year, latest_year + 1))

    # 2. TỐI ƯU HÓA QUERY (Eager Loading)
    # Bước này cực quan trọng: Gom tất cả dữ liệu cần thiết của 20 cty vào 1 lần query duy nhất
    # Thay vì query lắt nhắt trong vòng lặp.
    
    optimized_companies = target_companies_queryset.prefetch_related(
        # Lấy trước dữ liệu Báo cáo tài chính + join sẵn bảng con
        Prefetch(
            'tonghoptaichinh_set', # Lưu ý: Cần check lại related_name trong models.py nếu bạn đặt khác
            queryset=TongHopTaiChinh.objects.filter(
                nam__in=years_to_query,
                quy__in=[0, 5]
            ).select_related('bangcandoiketoan', 'bangketquakinhdoanh').order_by('nam'),
            to_attr='fetched_reports' # Lưu kết quả vào biến tạm này
        ),
        # Lấy trước dữ liệu Thị trường chứng khoán
        Prefetch(
            'thitruongchungkhoang_set', # Lưu ý: Check lại related_name
            queryset=ThiTruongChungKhoang.objects.filter(
                ngay__year__in=years_to_calculate
            ).order_by('-ngay'),
            to_attr='fetched_market_data'
        )
    )

    results = {}

    # 3. Lặp qua từng công ty (Lúc này chỉ chạy trên RAM, không gọi DB nữa)
    for company in optimized_companies:
        if company.maChungKhoan in ['a']:
            continue
        
        company_code = company.maChungKhoan
        
        # Lấy dữ liệu từ biến tạm (đã prefetch)
        reports_list = getattr(company, 'fetched_reports', [])
        market_data_list = getattr(company, 'fetched_market_data', [])
        
        total_collected_years = len(set(r.nam for r in reports_list))

        results[company_code] = {
            "tenCongTy": company.tenCongTy,
            "TongSoNamThuThap": total_collected_years,
            "annual_reports": {}
        }
        
        # Chuyển list reports thành Dictionary để tra cứu nhanh theo năm: Data[2023]
        processed_data = {}
        for report in reports_list:
            try:
                # Vì đã select_related ở trên nên truy cập vào đây không tốn query
                bcdt = report.bangcandoiketoan  
                kqkd = report.bangketquakinhdoanh
                
                processed_data[report.nam] = {
                    "LoiNhuanSauThue": kqkd.loiNhuanSauThueThuNhapDoanhNghiep,
                    "TongTaiSan": bcdt.tongCongTaiSan,
                    "VonChuSoHuu": bcdt.vonChuSoHuu, 
                    "TaiSanNganHan": bcdt.taiSanNganHan,
                    "NoNganHan": bcdt.noNganHan,
                    "NoPhaiTra": bcdt.noPhaiTra,
                    "VonGop": bcdt.vonGopCuaChuSoHuu,
                    "NoDaiHan": bcdt.noDaiHan
                }
            except (AttributeError, Exception):
                continue

        # Tính toán chỉ số
        for year in years_to_calculate:
            data_N = processed_data.get(year)
            data_N_minus_1 = processed_data.get(year - 1)
            
            if not data_N or not data_N_minus_1:
                continue

            # --- Dữ liệu Tài chính ---
            LNST_N = data_N["LoiNhuanSauThue"]
            TTS_N = data_N["TongTaiSan"]
            VCSH_N = data_N["VonChuSoHuu"]
            TSNH_N = data_N["TaiSanNganHan"]
            NNH_N = data_N["NoNganHan"]
            NPT_N = data_N["NoPhaiTra"]
            VonGop_N = data_N["VonGop"]
            NDH_N = data_N["NoDaiHan"]

            # Dữ liệu N-1
            LNST_N_1 = data_N_minus_1["LoiNhuanSauThue"]
            TTS_N_1 = data_N_minus_1["TongTaiSan"]
            VCSH_N_1 = data_N_minus_1["VonChuSoHuu"]

            # --- LẤY DỮ LIỆU THỊ TRƯỜNG (Lọc từ list RAM) ---
            # Tìm bản ghi thị trường đầu tiên khớp với năm hiện tại
            market_data = next((item for item in market_data_list if item.ngay.year == year), None)
            
            market_price = 0
            if market_data:
                if market_data.giaDongCua:
                    market_price = float(market_data.giaDongCua) * 1000
                elif market_data.giaDieuChinh:
                    market_price = float(market_data.giaDieuChinh) * 1000

            # --- TÍNH TOÁN (Giữ nguyên logic của bạn) ---
            avg_TTS = safe_divide(TTS_N + TTS_N_1, 2)
            avg_VCSH = safe_divide(VCSH_N + VCSH_N_1, 2)

            roa = safe_divide(LNST_N, avg_TTS)
            roe = safe_divide(LNST_N, avg_VCSH)
            current_ratio = safe_divide(TSNH_N, NNH_N)
            debt_to_assets = safe_divide(NPT_N, TTS_N)
            asset_growth = safe_divide(TTS_N - TTS_N_1, TTS_N_1)
            profit_growth = safe_divide(LNST_N - LNST_N_1, LNST_N_1)

            tong_von_hoa = (NDH_N if NDH_N else 0) + (VCSH_N if VCSH_N else 0)
            long_term_debt_ratio = safe_divide(NDH_N, tong_von_hoa)
            
            num_shares = safe_divide(VonGop_N, 10000)
            eps = safe_divide(LNST_N, num_shares)

            pe = safe_divide(market_price, eps) if eps and eps > 0 else 0
            
            bvps = safe_divide(VCSH_N, num_shares)
            pb = safe_divide(market_price, bvps)
            beta = 0 

            results[company_code]["annual_reports"][year] = {
                "ROA": roa,
                "ROE": roe,
                "TySuatThanhToanHienHanh": current_ratio,
                "HeSoNoTrenTongTaiSan": debt_to_assets,
                "TangTruongTaiSan": asset_growth,
                "TangTruongLoiNhuan": profit_growth,
                "EPS": eps,
                "PE": pe,
                "PB": pb,
                "Beta": beta, 
                "GiaDongCuaCuoiNam": market_price,
                "TyLeNoDaiHan": long_term_debt_ratio
            }
            
    return results


try:
    api_key=os.environ["GEMINI_API_KEY"]
except KeyError:
    print("Vui lòng đặt GEMINI_API_KEY trong biến môi trường của bạn.")
    # Hoặc đặt cứng ở đây (không khuyến khích):
    api_key = settings.GEMINI_API_KEY


client = genai.Client(api_key=api_key)

def call_gemini(user_question: str) -> str:
    """
    Hàm xử lý logic gọi Gemini với vai trò Chuyên gia tài chính.
    """
    if not user_question.strip():
        return "Vui lòng nhập nội dung câu hỏi."

    # 1. Lấy dữ liệu tài chính mới nhất
    # Lưu ý: Hàm này có thể chạy hơi lâu nếu DB lớn. 
    # Trong thực tế nên cache lại kết quả này nếu dữ liệu không thay đổi liên tục.
    raw_data = get_financial_ratios_data()
    # raw_data=2
    # 2. Chuyển đổi dữ liệu sang chuỗi JSON để nạp vào prompt
    if raw_data:
        # ensure_ascii=False để giữ tiếng Việt, indent=2 cho dễ nhìn (nếu debug)
        data_context = json.dumps(raw_data, ensure_ascii=False, indent=2)
    else:
        data_context = "Hiện tại chưa có dữ liệu báo cáo tài chính trong hệ thống."

    # 3. Xây dựng Prompt Template (Kỹ thuật Prompt Engineering)
    # Đây là phần quan trọng nhất để định hình tính cách Bot
    prompt_template = f"""
    VAI TRÒ:
    Bạn là một Chuyên gia Tư vấn Đầu tư Tài chính cấp cao. Nhiệm vụ của bạn là hỗ trợ khách hàng phân tích sức khỏe doanh nghiệp và đưa ra lời khuyên đầu tư dựa trên dữ liệu thực tế.

    DỮ LIỆU CUNG CẤP (Context):
    Dưới đây là dữ liệu các chỉ số tài chính (ROA, ROE, PE, EPS, Tăng trưởng, Nợ...) của các công ty trong 5 năm gần nhất:
    ```json
    {data_context}
    ```

    CÂU HỎI CỦA KHÁCH HÀNG:
    "{user_question}"

    YÊU CẦU XỬ LÝ:
    Bước 1: Phân loại câu hỏi.
    - Kiểm tra xem câu hỏi của khách hàng có liên quan đến: Tài chính, Đầu tư, Chứng khoán, Kinh tế, hoặc hỏi về các Công ty trong dữ liệu cung cấp hay không.
    
    Bước 2: Phản hồi.
    - TRƯỜNG HỢP 1 (Không liên quan): Nếu câu hỏi hoàn toàn không liên quan đến các chủ đề trên (ví dụ: hỏi về thời tiết, tình cảm, chính trị, code, nấu ăn...), hãy trả lời DUY NHẤT một câu sau:
      "Bạn vui lòng hỏi về tài chính, cảm ơn bạn nhé."
    
    - TRƯỜNG HỢP 2 (Có liên quan): 
      + Hãy phân tích câu hỏi dựa trên dữ liệu JSON được cung cấp ở trên.
      + Đưa ra các "Insight" (nhận định sâu sắc): Ví dụ thấy ROE giảm dần thì cảnh báo, thấy Tăng trưởng lợi nhuận cao thì khen ngợi.
      + Sử dụng các con số cụ thể từ dữ liệu để dẫn chứng cho lời khuyên (Ví dụ: "Năm 2023 PE chỉ còn 10.5, thấp hơn trung bình...").
      + Giọng văn: Chuyên nghiệp, khách quan, sắc sảo nhưng thân thiện và hữu ích.
    """

    print(f"Đang gọi Gemini với câu hỏi: '{user_question[:30]}...'")
    
    try:
        # Gọi Gemini
        response = client.models.generate_content(
            model="gemini-2.5-flash", # Hoặc gemini-1.5-flash tùy version bạn có
            contents=prompt_template,
        )
        return response.text
    except Exception as e:
        print(f"Lỗi khi gọi Gemini: {e}")
        return f"Xin lỗi, hệ thống phân tích đang gặp sự cố kết nối. Vui lòng thử lại sau.\n{e}"
    


# --- HÀM MỚI ĐỂ ĐẨY DỮ LIỆU LÊN GOOGLE SHEET ---

def format_number(value, is_percent=True):
    """
    Hàm helper để xử lý giá trị trước khi chèn.
    Google Sheet nên được định dạng là "Number" hoặc "Percent"
    để xử lý số, không nên đẩy chuỗi '%'.
    """
    if isinstance(value, (int, float)):
        return value  # Gửi số trực tiếp
    return None # Nếu là "Không đủ dữ liệu" hoặc lỗi

def update_financial_ratios_sheet(data_dict):

    # --- 1. XÁC THỰC THÔNG MINH (Hybrid Auth) ---
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    
    creds = None
    
    # Cách 1: Ưu tiên lấy từ Biến môi trường (Dành cho Cloud Run)
    json_creds_env = os.environ.get('GOOGLE_SHEETS_CREDENTIALS')
    
    if json_creds_env:
        try:
            # Parse chuỗi JSON từ biến môi trường thành Dictionary
            creds_dict = json.loads(json_creds_env)
            creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
            print("✅ Đã load credentials từ Biến Môi Trường (Cloud).", flush=True)
        except json.JSONDecodeError as e:
            print(f"❌ Lỗi decode JSON từ biến môi trường: {str(e)}", flush=True)

    # Cách 2: Nếu không có biến môi trường, tìm file (Dành cho Local)
    if not creds:
        local_file_path = 'credentials.json'
        if os.path.exists(local_file_path):
            try:
                creds = Credentials.from_service_account_file(local_file_path, scopes=scopes)
                print(f"✅ Đã load credentials từ file {local_file_path} (Local).", flush=True)
            except Exception as e:
                print(f"❌ Lỗi đọc file credentials: {str(e)}", flush=True)
        else:
            print("❌ LỖI NGHIÊM TRỌNG: Không tìm thấy Credentials ở cả ENV và FILE.", flush=True)
            return False # Dừng hàm nếu không có quyền truy cập
    
    # 1. Xác thực
    # Đảm bảo file service_account.json nằm ở đúng đường dẫn
    gc = gspread.authorize(creds)

    # 2. Mở Sheet bằng tên
    # Đảm bảo tên này khớp chính xác với Google Sheet của bạn
    sh = gc.open_by_url("https://docs.google.com/spreadsheets/d/1aY8IoFpUQ51LJd0_xVGsQp1d8dZonn3eNTVceebFJu8/edit?usp=sharing") 
    
    # Chọn worksheet (trang tính) đầu tiên
    worksheet = sh.get_worksheet(0)
    
    print("Đã kết nối Google Sheet thành công.", flush=True)

    # 3. Chuẩn bị dữ liệu (Chuyển đổi Dict lồng nhau thành danh sách phẳng)
    rows_to_insert = []
    
    # Tạo hàng tiêu đề
    header = [
        "Mã CK", "Tên Công Ty", "Năm", "ROA", "ROE", 
        "Tỷ Suất TT Hiện Hành", "Nợ/Tổng Tài Sản", 
        "Tăng Trưởng Tài Sản", "Tăng Trưởng Lợi Nhuận",
        "EPS", "PE", "PB", "Beta", "Giá đóng cửa cuối năm", "Tỷ lệ Nợ Dài Hạn" # Lưu thêm để kiểm tra
    ]
    rows_to_insert.append(header)

    # Lặp qua dữ liệu JSON
    for company_code, company_data in data_dict.items():
        ten_cong_ty = company_data.get("tenCongTy", "")
        
        # Sắp xếp các năm (mới nhất trước) cho dễ đọc
        annual_reports = company_data.get("annual_reports", {})
        sorted_years = sorted(annual_reports.keys(), reverse=True)

        for year in sorted_years:
            report = annual_reports[year]
            
            # Tạo một hàng
            if isinstance(report, str):
                # Trường hợp "Không đủ dữ liệu"
                row = [company_code, ten_cong_ty, year, report]
            else:
                # Trường hợp có dữ liệu
                row = [
                    company_code,
                    ten_cong_ty,
                    year,
                    format_number(report.get("ROA")),
                    format_number(report.get("ROE")),
                    format_number(report.get("TySuatThanhToanHienHanh"), is_percent=False), # Đây là tỷ lệ, không phải %
                    format_number(report.get("HeSoNoTrenTongTaiSan")),
                    format_number(report.get("TangTruongTaiSan")),
                    format_number(report.get("TangTruongLoiNhuan")),
                    format_number(report.get("EPS")),
                    format_number(report.get("PE")),
                    format_number(report.get("PB")),
                    format_number(report.get("Beta")),
                    format_number(report.get("GiaDongCuaCuoiNam")),
                    format_number(report.get("TyLeNoDaiHan"), is_percent=False)
                ]
            
            rows_to_insert.append(row)

    # 4. Cập nhật Sheet
    print(f"Đang chuẩn bị cập nhật {len(rows_to_insert)} hàng...")
    
    # Xóa toàn bộ nội dung cũ
    worksheet.clear()
    
    # Cập nhật tất cả dữ liệu một lúc (nhanh nhất)
    worksheet.update(f'A1:O{len(rows_to_insert)}', rows_to_insert, 
                        value_input_option='USER_ENTERED')
    
    print("Cập nhật Google Sheet thành công!")
    return True



#######################################DATA SERVICE FUNCTION###################################################################################
# data_services.py
from .models import *
from django.db.models import Q
import datetime


def get_formatted_news(symbol, date, lookback_days=7):
    """
    Lấy 5 tin tức liên quan đến công ty mới nhất trong vòng 'lookback_days' ngày.
    Khắc phục tình trạng ngày hiện tại không có tin.
    """
    # 1. Xác định khung thời gian: Từ (Ngày hiện tại - 7 ngày) đến (Cuối ngày hiện tại)
    end_date = datetime.datetime.combine(date, datetime.time.max)
    start_date = datetime.datetime.combine(date - datetime.timedelta(days=lookback_days), datetime.time.min)

    # 2. Tìm tên công ty để lọc tin (như bạn yêu cầu quay lại lọc theo công ty)
    cty = CongTy.objects.filter(maChungKhoan=symbol).first()
    company_name = cty.tenCongTy if cty else ""

    # 3. Query DB
    # - Lọc theo thời gian (7 ngày qua)
    # - Lọc theo Từ khóa (Symbol hoặc Tên công ty)
    # - Sắp xếp: Mới nhất lên đầu
    # - Cắt: Lấy 5 tin
    news_list = TinTuc.objects.filter(
        time_post__range=(start_date, end_date)
    ).order_by('-time_post')[:5]
    # ).filter(
    #     Q(title__icontains=symbol) | 
    #     Q(content__icontains=symbol) |
    #     Q(title__icontains=company_name)  # Thêm lọc theo tên đầy đủ cho chắc

    if not news_list:
        return f"No specific news found for {symbol} in the last {lookback_days} days."

    text = ""
    for n in news_list:
        # Format ngày giờ để Agent biết tin này cũ hay mới
        # Quan trọng: Phải hiện ngày để Agent biết tin này là của hôm nay hay 3 ngày trước
        time_str = n.time_post.strftime('%Y-%m-%d %H:%M') if n.time_post else "N/A"
        
        # Lấy snippet
        content_preview = n.summary if n.summary else (n.content[:150] + "..." if n.content else "")
        
        text += f"- [{time_str}] {n.title}: {content_preview}\n"
        
    return text


def get_formatted_financials(symbol, date):
    """Lấy BCTC gần nhất so với ngày hiện tại"""
    # Tìm kỳ báo cáo gần nhất đã công bố trước ngày này
    # Logic: Tìm TongHopTaiChinh mới nhất
    cty = CongTy.objects.filter(maChungKhoan=symbol).first()
    if not cty: return "Company not found."

    # Giả sử năm hiện tại, quý gần nhất
    report_wrapper = TongHopTaiChinh.objects.filter(
        congTy=cty,
        nam__lte=date.year
    ).order_by('-nam', '-quy').first()

    if not report_wrapper:
        return "No financial report data available."

    # Lấy KQKD và CĐKT
    kqkd = BangKetQuaKinhDoanh.objects.filter(baoCao=report_wrapper).first()
    cdkt = BangCanDoiKeToan.objects.filter(baoCao=report_wrapper).first()

    text = f"**Report Period: Q{report_wrapper.quy}/{report_wrapper.nam}**\n"
    
    if kqkd:
        text += f"- Revenue: {kqkd.doanhThuThuan} VND\n"
        text += f"- Net Income: {kqkd.loiNhuanSauThueThuNhapDoanhNghiep} VND\n"
        text += f"- Gross Profit: {kqkd.loiNhuanGop} VND\n"
    
    if cdkt:
        text += f"- Total Assets: {cdkt.tongCongTaiSan} VND\n"
        text += f"- Total Equity: {cdkt.vonChuSoHuu} VND\n"
        text += f"- Total Debt: {cdkt.noPhaiTra} VND\n"

    return text

def get_price_action(symbol, date):
    """Lấy biến động giá gần đây"""
    # Lấy giá của ngày hiện tại và 30 ngày trước
    prices = ThiTruongChungKhoang.objects.filter(
        congTy__maChungKhoan=symbol,
        ngay__lte=date
    ).order_by('-ngay')[:30]

    if not prices.exists():
        return "No price data."

    today_price = prices[0]
    prev_price = prices[1] if len(prices) > 1 else today_price
    
    # Tính toán đơn giản
    change = today_price.giaDongCua - prev_price.giaDongCua
    percent = (change / prev_price.giaDongCua * 100) if prev_price.giaDongCua else 0

    text = f"- Close Price: {today_price.giaDongCua}\n"
    text += f"- Daily Change: {change} ({percent:.2f}%)\n"
    text += f"- Volume: {today_price.klKhopLenh}\n"
    
    # Trend 7 ngày
    if len(prices) >= 7:
        p7 = prices[6]
        trend_7d = ((today_price.giaDongCua - p7.giaDongCua) / p7.giaDongCua) * 100
        text += f"- 7-Day Trend: {trend_7d:.2f}%\n"

    return text









