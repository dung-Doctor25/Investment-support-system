from django.contrib import admin
from django.contrib import messages
from .models import (
    CongTy, ThiTruongChungKhoang, TongHopTaiChinh, 
    BangCanDoiKeToan, BangKetQuaKinhDoanh, Conversation, Message
)

# --- PHẦN XỬ LÝ NÚT XÓA ---

@admin.action(description='🔥 Xóa SẠCH dữ liệu của bảng này (Reset bảng)')
def delete_table_data(modeladmin, request, queryset):
    # 1. Kiểm tra quyền Admin cao nhất
    if not request.user.is_superuser:
        modeladmin.message_user(request, "Chỉ Superuser mới được xóa toàn bộ bảng!", level=messages.ERROR)
        return

    # 2. Xác định bảng đang thao tác
    # modeladmin.model chính là Class (Bảng) bạn đang đứng.
    # Ví dụ: Nếu bạn đang ở trang CongTy, biến này là model CongTy.
    current_model = modeladmin.model
    model_name = current_model._meta.verbose_name
    
    # 3. Đếm số lượng trước khi xóa
    count = current_model.objects.all().count()
    
    if count == 0:
        modeladmin.message_user(request, f"Bảng {model_name} đang trống, không có gì để xóa.", level=messages.WARNING)
        return

    # 4. Thực hiện xóa TOÀN BỘ dữ liệu chỉ của bảng này
    # Lệnh này tương đương: DELETE FROM ten_bang;
    current_model.objects.all().delete()
    
    modeladmin.message_user(request, f"Đã xóa thành công toàn bộ {count} dòng dữ liệu trong bảng {model_name}.", level=messages.SUCCESS)


# --- PHẦN ĐĂNG KÝ VÀO TRANG ADMIN ---

# Tạo class chung để không phải viết lại code nhiều lần
class CommonAdmin(admin.ModelAdmin):
    actions = [delete_table_data]
    list_per_page = 20

# Đăng ký từng bảng
admin.site.register(CongTy, CommonAdmin)
admin.site.register(ThiTruongChungKhoang, CommonAdmin)
admin.site.register(TongHopTaiChinh, CommonAdmin)
admin.site.register(BangCanDoiKeToan, CommonAdmin)
admin.site.register(BangKetQuaKinhDoanh, CommonAdmin)
admin.site.register(Conversation, CommonAdmin)
admin.site.register(Message, CommonAdmin)