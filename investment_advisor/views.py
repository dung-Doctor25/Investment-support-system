from django.shortcuts import render
from .models import *
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from decimal import Decimal, InvalidOperation
from django.http import JsonResponse,HttpResponse
from django.db.models import Sum, Max, Count, F, Q
from .utils import update_financial_ratios_sheet,get_financial_ratios_data
import threading
import openpyxl
import json
import os
import time
from django.utils.dateparse import parse_datetime

def home(request):
    return render(request, 'home.html')

def congty_form(request):
    return render(request, "form/congty_post_form.html")
def thitruong_form(request):
    return render(request, "form/thitruong_form.html")
def tonghoptaichinh_form(request):
    return render(request, "form/tonghoptaichinh_post_form.html")
def bangcandoiketoan_form(request):
    return render(request, "form/bangcandoiketoan_post_form.html")
def bangketquakinhdoanh_form(request):
    return render(request, "form/bangketquakinhdoanh_post_form.html")

def file_upload(request):
    return render(request, "file/file_upload.html")
def chat_view(request):
    return render(request, 'chatbot.html')

def chart_view(request):
    return render(request, 'aggregated_data/chart_d3.html')
def chart_view_2(request):
    return render(request, 'aggregated_data/chart_hieu_suat.html')
def tableau_view(request):
    return render(request, 'aggregated_data/tableau.html')

def table_view(request):
    return render(request, 'aggregated_data/table.html')




#==========================GET DATA METHOD===========================
def get_CongTy_data(request):
    data = list(CongTy.objects.values())
    return JsonResponse(data, safe=False)
def get_TongHopTaiChinh_data(request):
    company_id = request.GET.get('company_id')
    
    if not company_id:
        return JsonResponse([], safe=False)

    try:
        # Chỉ query báo cáo của ĐÚNG công ty đó -> Cực nhanh
        data = list(
            TongHopTaiChinh.objects
            .filter(congTy_id=company_id)
            .values()
            .order_by('-nam', '-quy')[ :10 ]  # Giới hạn 10 bản ghi gần nhất
        )  # Giới hạn 10 bản ghi gần nhất
       
        return JsonResponse(data, safe=False)
    except Exception as e:
        print(f'Error retrieving reports for company {company_id}: {str(e)}', flush=True)
        return JsonResponse({'error': str(e)}, status=500)
def get_ThiTruongChungKhoan_data(request):
    data = list(ThiTruongChungKhoang.objects.values())
    return JsonResponse(data, safe=False)
def get_BangCanDoiKeToan_data(request):
    data = list(BangCanDoiKeToan.objects.values())
    return JsonResponse(data, safe=False)
def get_BangKetQuaKinhDoanh_data(request):
    data = list(BangKetQuaKinhDoanh.objects.values())
    return JsonResponse(data, safe=False)



#==========================DOWNLOAD DATA===========================


# View Export Excel Mới (Đầy đủ chỉ số)
def export_financial_ratios_excel(request):
    # 1. Lấy dữ liệu đã tính toán từ utils
    data = get_financial_ratios_data()
    
    if data is None:
        return HttpResponse("Không có dữ liệu để xuất.", status=404)

    # 2. Tạo Workbook Excel
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Chỉ Số Tài Chính"

    # 3. Ghi Header (Đầy đủ các cột)
    headers = [
        "Mã Cổ Phiếu", 
        "Tên Công Ty", 
        "Số Năm Thu Thập", 
        "Năm",
        "ROA", 
        "ROE", 
        "Tỷ Suất Thanh Toán Hiện Hành", # Current Ratio
        "Hệ Số Nợ / Tổng Tài Sản",      # Debt/Assets
        "Tăng Trưởng Tài Sản", 
        "Tăng Trưởng Lợi Nhuận",
        "EPS", 
        "P/E", 
        "P/B", 
        "Beta", 
        "Giá Đóng Cửa Cuối Năm", 
        "Tỷ Lệ Nợ Dài Hạn"
    ]
    ws.append(headers)

    # 4. Duyệt dữ liệu và ghi vào Excel
    for company_code, company_info in data.items():
        ten_cong_ty = company_info['tenCongTy']
        tong_nam = company_info['TongSoNamThuThap']
        reports = company_info['annual_reports']

        # Sắp xếp theo năm tăng dần
        sorted_years = sorted(reports.keys())

        for year in sorted_years:
            metrics = reports[year]
            
            # Bỏ qua nếu metrics là chuỗi thông báo lỗi (nếu có)
            if isinstance(metrics, str): 
                continue

            row = [
                company_code,
                ten_cong_ty,
                tong_nam,
                year,
                metrics.get("ROA"),
                metrics.get("ROE"),
                metrics.get("TySuatThanhToanHienHanh"),
                metrics.get("HeSoNoTrenTongTaiSan"),
                metrics.get("TangTruongTaiSan"),
                metrics.get("TangTruongLoiNhuan"),
                metrics.get("EPS"),
                metrics.get("PE"),
                metrics.get("PB"),
                metrics.get("Beta"),
                metrics.get("GiaDongCuaCuoiNam"),
                metrics.get("TyLeNoDaiHan")
            ]
            ws.append(row)

    # 5. Thiết lập HTTP Response để tải file
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename=BaoCaoChiSoTaiChinh.xlsx'
    
    wb.save(response)
    return response
#==========================POST DATA METHOD===========================

@require_POST
def post_congty_data(request):
    try:
        data = json.loads(request.body)
        congty = CongTy.objects.create(
            tenCongTy=data.get("tenCongTy"),
            nganh=data.get("nganh"),
            maChungKhoan=data.get("maChungKhoan"),
        )
        return JsonResponse({"message": f"Đã thêm công ty: {congty.tenCongTy}"}, status=201)
    except Exception as e:
        return JsonResponse({"message": f"Lỗi: {str(e)}"}, status=400)


  
def post_thitruong_data(request):
    try:
        data = json.loads(request.body)
        if isinstance(data, dict):  # 🧠 Nếu chỉ có 1 bản ghi
            data = [data]

        created_records = []
        for record_data in data:
            cong_ty, _ = CongTy.objects.get_or_create(
                maChungKhoan=record_data["congTy"],
                defaults={
                    "tenCongTy": record_data.get("tenCongTy", record_data["congTy"]),
                    "nganh": record_data.get("nganh", None),
                }
            )

            record = ThiTruongChungKhoang(
                congTy=cong_ty,
                ngay=record_data["ngay"],
                giaDongCua=record_data["giaDongCua"],
                giaDieuChinh=record_data["giaDieuChinh"],
                thayDoi=record_data["thayDoi"],
                klKhopLenh=record_data["klKhopLenh"],
                gtKhopLenh=record_data["gtKhopLenh"],
                klThoaThuan=record_data.get("klThoaThuan"),
                gtThoaThuan=record_data.get("gtThoaThuan"),
                giaMoCua=record_data["giaMoCua"],
                giaCaoNhat=record_data["giaCaoNhat"],
                giaThapNhat=record_data["giaThapNhat"],
            )
            created_records.append(record)

        ThiTruongChungKhoang.objects.bulk_create(created_records)

        return JsonResponse({
            "message": f"Đã thêm {len(created_records)} bản ghi thành công!"
        }, status=201)

    except Exception as e:
        return JsonResponse({"message": f"Lỗi: {str(e)}"}, status=400)


@require_POST
def post_tonghoptaichinh_data(request):
    if request.method == "POST":
        body = json.loads(request.body)
        ma_cty = body.get("congTy")
        nam = body.get("nam")
        quy = body.get("quy")

        try:
            congty = CongTy.objects.get(maChungKhoan=ma_cty)
            record = TongHopTaiChinh.objects.create(
                congTy=congty, nam=nam, quy=quy
            )
            return JsonResponse({
                "message": f"Đã tạo mới báo cáo cho {ma_cty} năm {nam}, quý {quy}"
            })
        except CongTy.DoesNotExist:
            return JsonResponse({"message": "Công ty không tồn tại!"}, status=400)

    return JsonResponse({"message": "Phương thức không hợp lệ!"}, status=405)


@require_POST
def post_bangcandoiketoan_data(request):

    try:
        data = json.loads(request.body)

        # ==========================================================
        # TRƯỜNG HỢP 1: DỮ LIỆU HÀNG LOẠT (TỪ FILE CSV)
        # ==========================================================
        if isinstance(data, list):
            bcdt_to_create = []
            errors = []

            for index, item in enumerate(data):
                try:
                    ma_chung_khoan = item.get('ma')
                    nam = item.get('years')
                    quy = item.get('quy')
                    
                    if not ma_chung_khoan or nam is None or quy is None:
                        errors.append(f"Dòng {index + 1}: Thiếu 'ma', 'years', hoặc 'quy'. Bỏ qua.")
                        continue

                    # 1. Lấy hoặc tạo CongTy
                    cong_ty_instance, _ = CongTy.objects.get_or_create(
                        maChungKhoan=ma_chung_khoan.upper(),
                        defaults={'tenCongTy': f"Công ty {ma_chung_khoan.upper()}"}
                    )
                    # 2. Lấy hoặc tạo TongHopTaiChinh
                    tong_hop_instance, _ = TongHopTaiChinh.objects.get_or_create(
                        congTy=cong_ty_instance,
                        nam=nam,
                        quy=quy
                    )
                    
                    item.pop('ma', None); item.pop('years', None); item.pop('quy', None)

                    # 3. Chuẩn bị đối tượng (chưa lưu)
                    bcdt_object = BangCanDoiKeToan(baoCao=tong_hop_instance, **item)
                    bcdt_to_create.append(bcdt_object)
                
                except Exception as e:
                    errors.append(f"Dòng {index + 1} (Mã: {item.get('ma')}): Lỗi - {str(e)}")

            # 4. Lưu hàng loạt
            if bcdt_to_create:
                BangCanDoiKeToan.objects.bulk_create(bcdt_to_create, ignore_conflicts=True)
            
            message = f"Hoàn tất xử lý HÀNG LOẠT! Đã gửi {len(bcdt_to_create)} bản ghi. Lỗi: {len(errors)}."
            return JsonResponse({'message': message, 'errors': errors}, status=200)

        # ==========================================================
        # TRƯỜNG HỢP 2: DỮ LIỆU LẺ (TỪ FORM NHẬP TAY)
        # ==========================================================
        elif isinstance(data, dict):
            # 1. Lấy ID báo cáo trực tiếp
            bao_cao_id = data.get('baoCao')
            if not bao_cao_id:
                return JsonResponse({'message': 'Lỗi: Dữ liệu lẻ thiếu "baoCao" ID.'}, status=400)

            # 2. Tìm TongHopTaiChinh
            try:
                tong_hop_instance = TongHopTaiChinh.objects.get(pk=bao_cao_id)
            except TongHopTaiChinh.DoesNotExist:
                return JsonResponse({'message': f'Lỗi: Không tìm thấy Báo cáo tài chính với ID {bao_cao_id}.'}, status=404)
            
            # 3. Chuẩn bị dữ liệu (loại bỏ key 'baoCao')
            del data['baoCao']
            for key, value in data.items():
                if value == '': data[key] = None

            # 4. Dùng update_or_create để cập nhật hoặc tạo mới
            bcdt_object, created = BangCanDoiKeToan.objects.update_or_create(
                baoCao=tong_hop_instance,
                defaults=data
            )
            
            message = "Đã TẠO MỚI" if created else "Đã CẬP NHẬT"
            status_code = 201 if created else 200
            return JsonResponse({'message': f"{message} thành công Bảng CĐKT cho {tong_hop_instance}."}, status=status_code)
        
        # Trường hợp không phải list hoặc dict
        else:
            return JsonResponse({'message': 'Lỗi: Dữ liệu phải là một object {} hoặc một mảng [{}].'}, status=400)

    except json.JSONDecodeError:
        return JsonResponse({'message': 'Lỗi: Dữ liệu JSON không hợp lệ.'}, status=400)
    except Exception as e:
        return JsonResponse({'message': f'Đã xảy ra lỗi nghiêm trọng: {str(e)}'}, status=500)

@require_POST
def post_bangketquakinhdoanh_data(request):
    
    try:
        data = json.loads(request.body)

        # ==========================================================
        # TRƯỜNG HỢP 1: DỮ LIỆU HÀNG LOẠT (TỪ FILE CSV)
        # ==========================================================
        if isinstance(data, list):
            kqkd_to_create = []
            errors = []

            for index, item in enumerate(data):
                try:
                    ma_chung_khoan = item.get('ma')
                    nam = item.get('years')
                    quy = item.get('quy')
                    
                    if not ma_chung_khoan or nam is None or quy is None:
                        errors.append(f"Dòng {index + 1}: Thiếu 'ma', 'years', hoặc 'quy'. Bỏ qua.")
                        continue

                    # 1. Lấy hoặc tạo CongTy
                    cong_ty_instance, _ = CongTy.objects.get_or_create(
                        maChungKhoan=ma_chung_khoan.upper(),
                        defaults={'tenCongTy': f"Công ty {ma_chung_khoan.upper()}"}
                    )
                    # 2. Lấy hoặc tạo TongHopTaiChinh
                    tong_hop_instance, _ = TongHopTaiChinh.objects.get_or_create(
                        congTy=cong_ty_instance,
                        nam=nam,
                        quy=quy
                    )
                    
                    item.pop('ma', None); item.pop('years', None); item.pop('quy', None)

                    # 3. Chuẩn bị đối tượng (chưa lưu)
                    kqkd_object = BangKetQuaKinhDoanh(baoCao=tong_hop_instance, **item)
                    kqkd_to_create.append(kqkd_object)
                
                except Exception as e:
                    errors.append(f"Dòng {index + 1} (Mã: {item.get('ma')}): Lỗi - {str(e)}")

            # 4. Lưu hàng loạt
            if kqkd_to_create:
                BangKetQuaKinhDoanh.objects.bulk_create(kqkd_to_create, ignore_conflicts=True)
            
            message = f"Hoàn tất xử lý HÀNG LOẠT! Đã gửi {len(kqkd_to_create)} bản ghi KQKD. Lỗi: {len(errors)}."
            return JsonResponse({'message': message, 'errors': errors}, status=200)

        # ==========================================================
        # TRƯỜNG HỢP 2: DỮ LIỆU LẺ (TỪ FORM NHẬP TAY)
        # ==========================================================
        elif isinstance(data, dict):
            # 1. Lấy ID báo cáo trực tiếp
            bao_cao_id = data.get('baoCao')
            if not bao_cao_id:
                return JsonResponse({'message': 'Lỗi: Dữ liệu lẻ thiếu "baoCao" ID.'}, status=400)

            # 2. Tìm TongHopTaiChinh
            try:
                tong_hop_instance = TongHopTaiChinh.objects.get(pk=bao_cao_id)
            except TongHopTaiChinh.DoesNotExist:
                return JsonResponse({'message': f'Lỗi: Không tìm thấy Báo cáo tài chính với ID {bao_cao_id}.'}, status=404)
            
            # 3. Chuẩn bị dữ liệu (loại bỏ key 'baoCao' và chuẩn hóa giá trị rỗng)
            del data['baoCao']
            for key, value in data.items():
                if value == '' or value is None:
                    data[key] = None # Hoặc 0, tùy thuộc vào model, nhưng None an toàn hơn nếu model cho phép

            # 4. Dùng update_or_create để cập nhật hoặc tạo mới
            kqkd_object, created = BangKetQuaKinhDoanh.objects.update_or_create(
                baoCao=tong_hop_instance,
                defaults=data
            )
            
            message = "Đã TẠO MỚI" if created else "Đã CẬP NHẬT"
            status_code = 201 if created else 200
            return JsonResponse({'message': f"{message} thành công Bảng KQKD cho {tong_hop_instance}."}, status=status_code)
        
        # Trường hợp không phải list hoặc dict
        else:
            return JsonResponse({'message': 'Lỗi: Dữ liệu phải là một object {} hoặc một mảng [{}].'}, status=400)

    except json.JSONDecodeError:
        return JsonResponse({'message': 'Lỗi: Dữ liệu JSON không hợp lệ.'}, status=400)
    except Exception as e:
        return JsonResponse({'message': f'Đã xảy ra lỗi nghiêm trọng: {str(e)}'}, status=500)
def post_TinTuc_data(request):
    try:
        # 1. Parse dữ liệu từ body request
        data = json.loads(request.body)
        
        # Kiểm tra nếu data là dict (1 bài) thì chuyển thành list
        if isinstance(data, dict):
            data = [data]
            
        news_to_create = []
        count_success = 0
        
        # 2. Duyệt qua từng bài viết
        for item in data:
            try:
                # Lấy dữ liệu
                title = item.get('title')
                content = item.get('content')
                link = item.get('link')
                time_str = item.get('time_post')
                summary = item.get('summary')

                # Kiểm tra dữ liệu bắt buộc
                if not title or not link or not time_str:
                    continue

                # Parse thời gian (ISO format: "2025-12-13T09:17:00")
                time_post = parse_datetime(time_str)

                # Tạo đối tượng (chưa lưu vào DB)
                news_obj = TinTuc(
                    title=title,
                    content=content,
                    link=link,
                    time_post=time_post,
                    summary=summary
                )
                news_to_create.append(news_obj)
                
            except Exception as e:
                print(f"Lỗi khi xử lý bài viết {item.get('title', 'Unknown')}: {e}")
                continue

        # 3. Lưu hàng loạt vào Database (Tối ưu tốc độ)
        if news_to_create:
            # ignore_conflicts=True giúp bỏ qua lỗi nếu trùng lặp (nếu DB có ràng buộc unique)
            TinTuc.objects.bulk_create(news_to_create, ignore_conflicts=True)
            
        return JsonResponse({
            "message": f"Đã thêm thành công {len(news_to_create)} bài viết tin tức!"
        }, status=201)

    except json.JSONDecodeError:
        return JsonResponse({"message": "Lỗi: File JSON không đúng định dạng."}, status=400)
    except Exception as e:
        return JsonResponse({"message": f"Lỗi Server: {str(e)}"}, status=500)


# ==========================RETRIEVE QUERY METHOD===========================

def retrieve_bangcandoikt(request):
    try:
        start_time = time.time()
        
        data = (
            BangCanDoiKeToan.objects
            .select_related('baoCao__congTy')  # nếu có quan hệ foreign key
            .values('baoCao__congTy__tenCongTy')  # group by theo tên công ty
            .annotate(tong_tai_san=Sum('tongCongTaiSan'))
            .order_by('-tong_tai_san')
        )
        duration = time.time() - start_time

        result = list(data)

        return JsonResponse({
            "message": f"Lấy dữ liệu thành công trong {duration:.2f} giây. giá trị: {result}."
        }, status=200)
    except:
        return JsonResponse({"message": "Bảng cân đối kế toán không tồn tại!"}, status=404)


# chatbot/views.py

@require_POST # Chỉ cho phép phương thức POST
def save_message_view(request):
    """
    API View để lưu một tin nhắn (từ user hoặc bot) vào CSDL.
    """
    try:
        # Lấy dữ liệu thô từ body của fetch
        data = json.loads(request.body)
        message_content = data.get('content')
        sender = data.get('sender') # Sẽ là 'user' hoặc 'bot'

        if not message_content or not sender:
            return JsonResponse({'status': 'error', 'message': 'Thiếu content hoặc sender'}, status=400)

        # --- Logic Session y hệt như trong Consumer ---
        session = request.session
        conversation_id = session.get('conversation_id')
        
        if conversation_id:
            try:
                conversation = Conversation.objects.get(id=conversation_id)
            except Conversation.DoesNotExist:
                # Nếu ID trong session bị sai, tạo cái mới
                conversation = Conversation.objects.create()
                session['conversation_id'] = conversation.id
        else:
            # Nếu chưa có, tạo mới
            conversation = Conversation.objects.create()
            session['conversation_id'] = conversation.id
        
        # Lưu session
        session.save()
        # --- Hết logic Session ---

        # Tạo và lưu tin nhắn
        Message.objects.create(
            conversation=conversation,
            sender=sender,
            content=message_content
        )
        
        return JsonResponse({'status': 'success', 'message': 'Đã lưu tin nhắn'})

    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Dữ liệu JSON không hợp lệ'}, status=400)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    


# Đặt hàm này ở đầu file view của bạn hoặc trong một file utils.py

def safe_divide(numerator, denominator):
    """
    Hàm chia an toàn, xử lý giá trị None và chia cho 0.
    Tất cả dữ liệu tài chính của bạn là BigIntegerField hoặc DecimalField, 
    nên chúng ta sẽ làm việc với Decimal để giữ độ chính xác.
    """
    if numerator is None or denominator is None:
        return None
    
    # Chuyển đổi sang Decimal để tính toán
    try:
        numerator_d = Decimal(numerator)
        denominator_d = Decimal(denominator)
        
        if denominator_d == Decimal(0):
            return None # Hoặc bạn có thể trả về 'Infinity'
        
        # Trả về một số float để dễ dàng serialize sang JSON
        return float(numerator_d / denominator_d)
        
    except (TypeError, ValueError, InvalidOperation):
        return None





# View API JSON cũ (được rút gọn)
def calculate_financial_ratios_view(request):
    data = get_financial_ratios_data()
    if data is None:
        return JsonResponse({"error": "Không có dữ liệu báo cáo tài chính"}, status=404)
    
    # update_financial_ratios_sheet(data) # Uncomment nếu cần update Google Sheet
    return JsonResponse(data, safe=False, json_dumps_params={'indent': 2, 'ensure_ascii': False})


# View API JSON cũ (được rút gọn)
def update_google_sheet(request):
    data = get_financial_ratios_data()
    json_creds = os.environ.get('GOOGLE_SHEETS_CREDENTIALS')
    
    if not json_creds:
        print("Thiếu credentials", flush=True)
        
    if data is None:
        return JsonResponse({"error": "Không có dữ liệu báo cáo tài chính"}, status=404)
    thread = threading.Thread(target=update_financial_ratios_sheet, args=(data,))
    thread.start()    
    
    return JsonResponse(data, safe=False, json_dumps_params={'indent': 2, 'ensure_ascii': False})






#==========================AI ADVISOR SYSTEM===========================
