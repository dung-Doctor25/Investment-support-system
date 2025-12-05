# your_app/models.py

from django.db import models

# Bảng chứa thông tin định danh của các công ty
class CongTy(models.Model):
    tenCongTy = models.CharField(max_length=255, verbose_name="Tên công ty")
    nganh = models.CharField(max_length=255, verbose_name="Ngành nghề", blank=True, null=True)
    maChungKhoan = models.CharField(max_length=10, unique=True, db_index=True, verbose_name="Mã chứng khoán")

    def __str__(self):
        return f"{self.maChungKhoan} - {self.tenCongTy}"

    class Meta:
        verbose_name = "Công Ty"
        verbose_name_plural = "Các Công Ty"

# Bảng chứa dữ liệu thị trường hàng ngày
class ThiTruongChungKhoang(models.Model):
    congTy = models.ForeignKey(CongTy, to_field='maChungKhoan', on_delete=models.CASCADE, verbose_name="Công ty")
    ngay = models.DateField(verbose_name="Ngày giao dịch")
    giaDongCua = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Giá đóng cửa (nghìn VNĐ)")
    giaDieuChinh = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Giá điều chỉnh (nghìn VNĐ)")
    thayDoi = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Thay đổi giá (+/-)")
    klKhopLenh = models.BigIntegerField(null=True, blank=True, verbose_name="KL khớp lệnh")
    gtKhopLenh = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True, verbose_name="GT khớp lệnh (tỷ VNĐ)")
    klThoaThuan = models.BigIntegerField(null=True, blank=True, verbose_name="KL thỏa thuận")
    gtThoaThuan = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True, verbose_name="GT thỏa thuận (tỷ VNĐ)")
    giaMoCua = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Giá mở cửa (nghìn VNĐ)")
    giaCaoNhat = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Giá cao nhất (nghìn VNĐ)")
    giaThapNhat = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Giá thấp nhất (nghìn VNĐ)")

    def __str__(self):
        return f"{self.congTy.maChungKhoan} - {self.ngay}"

    class Meta:
        verbose_name = "Dữ liệu thị trường"
        verbose_name_plural = "Dữ liệu thị trường"
        ordering = ['-ngay', 'congTy']
        unique_together = ('congTy', 'ngay') # Đảm bảo mỗi công ty chỉ có 1 bản ghi mỗi ngày

# Bảng trung gian, đóng vai trò là "bảng cha" cho mỗi kỳ báo cáo
class TongHopTaiChinh(models.Model):
    congTy = models.ForeignKey(CongTy, to_field='maChungKhoan', on_delete=models.CASCADE, verbose_name="Công ty")
    nam = models.IntegerField(verbose_name="Năm")
    quy = models.IntegerField(null=True, blank=True, verbose_name="Quý") # Ví dụ: 1, 2, 3, 4. Quý 0 hoặc 5 cho báo cáo năm.

    def __str__(self):
        return f"BCTC {self.congTy.maChungKhoan} - Năm {self.nam}, Quý {self.quy}"

    class Meta:
        verbose_name = "Báo Cáo Tài Chính"
        verbose_name_plural = "Các Báo Cáo Tài Chính"
        ordering = ['congTy', '-nam', '-quy']
        unique_together = ('congTy', 'nam', 'quy') # Đảm bảo mỗi cty chỉ có 1 báo cáo cho mỗi kỳ

class BangCanDoiKeToan(models.Model):
    baoCao = models.OneToOneField(TongHopTaiChinh, on_delete=models.CASCADE, primary_key=True, verbose_name="Báo cáo liên quan")

    # === TÀI SẢN ===
    # A. TÀI SẢN NGẮN HẠN
    taiSanNganHan = models.BigIntegerField(null=True, blank=True, verbose_name="A. TÀI SẢN NGẮN HẠN")
    tienVaCacKhoanTuongDuongTien = models.BigIntegerField(null=True, blank=True, verbose_name="Tiền và các khoản tương đương tiền")
    tien = models.BigIntegerField(null=True, blank=True, verbose_name="Tiền")
    cacKhoanTuongDuongTien = models.BigIntegerField(null=True, blank=True, verbose_name="Các khoản tương đương tiền")
    cacKhoanDauTuTaiChinhNganHan = models.BigIntegerField(null=True, blank=True, verbose_name="Các khoản đầu tư tài chính ngắn hạn")
    chungKhoanKinhDoanh = models.BigIntegerField(null=True, blank=True, verbose_name="Chứng khoán kinh doanh")
    duPhongGiamGiaChungKhoanKinhDoanh = models.BigIntegerField(null=True, blank=True, verbose_name="Dự phòng giảm giá chứng khoán kinh doanh")
    dauTuNamGiuDenNgayDaoHanNH = models.BigIntegerField(null=True, blank=True, verbose_name="Đầu tư nắm giữ đến ngày đáo hạn (NH)")
    cacKhoanPhaiThuNganHan = models.BigIntegerField(null=True, blank=True, verbose_name="Các khoản phải thu ngắn hạn")
    phaiThuNganHanCuaKhachHang = models.BigIntegerField(null=True, blank=True, verbose_name="Phải thu ngắn hạn của khách hàng")
    traTruocChoNguoiBanNganHan = models.BigIntegerField(null=True, blank=True, verbose_name="Trả trước cho người bán ngắn hạn")
    phaiThuNoiBoNganHan = models.BigIntegerField(null=True, blank=True, verbose_name="Phải thu nội bộ ngắn hạn")
    phaiThuTheoTienDoKeHoachHopDongXayDung = models.BigIntegerField(null=True, blank=True, verbose_name="Phải thu theo tiến độ kế hoạch hợp đồng xây dựng")
    phaiThuVeChoVayNganHan = models.BigIntegerField(null=True, blank=True, verbose_name="Phải thu về cho vay ngắn hạn")
    phaiThuNganHanKhac = models.BigIntegerField(null=True, blank=True, verbose_name="Phải thu ngắn hạn khác")
    duPhongPhaiThuNganHanKhoDoi = models.BigIntegerField(null=True, blank=True, verbose_name="Dự phòng phải thu ngắn hạn khó đòi")
    taiSanThieuChoXuLy = models.BigIntegerField(null=True, blank=True, verbose_name="Tài sản Thiếu chờ xử lý")
    hangTonKho = models.BigIntegerField(null=True, blank=True, verbose_name="Hàng tồn kho")
    duPhongGiamGiaHangTonKho = models.BigIntegerField(null=True, blank=True, verbose_name="Dự phòng giảm giá hàng tồn kho")
    taiSanNganHanKhac = models.BigIntegerField(null=True, blank=True, verbose_name="Tài sản ngắn hạn khác")
    chiPhiTraTruocNganHan = models.BigIntegerField(null=True, blank=True, verbose_name="Chi phí trả trước ngắn hạn")
    thueGTGTDuocKhauTru = models.BigIntegerField(null=True, blank=True, verbose_name="Thuế GTGT được khấu trừ")
    thueVaCacKhoanKhacPhaiThuNhaNuoc = models.BigIntegerField(null=True, blank=True, verbose_name="Thuế và các khoản khác phải thu Nhà nước")
    giaoDichMuaBanLaiTraiPhieuChinhPhu = models.BigIntegerField(null=True, blank=True, verbose_name="Giao dịch mua bán lại trái phiếu Chính phủ")
    
    # B. TÀI SẢN DÀI HẠN
    taiSanDaiHan = models.BigIntegerField(null=True, blank=True, verbose_name="B. TÀI SẢN DÀI HẠN")
    cacKhoanPhaiThuDaiHan = models.BigIntegerField(null=True, blank=True, verbose_name="Các khoản phải thu dài hạn")
    phaiThuDaiHanCuaKhachHang = models.BigIntegerField(null=True, blank=True, verbose_name="Phải thu dài hạn của khách hàng")
    traTruocChoNguoiBanDaiHan = models.BigIntegerField(null=True, blank=True, verbose_name="Trả trước cho người bán dài hạn")
    vonKinhDoanhODonViTrucThuoc = models.BigIntegerField(null=True, blank=True, verbose_name="Vốn kinh doanh ở đơn vị trực thuộc")
    phaiThuNoiBoDaiHan = models.BigIntegerField(null=True, blank=True, verbose_name="Phải thu nội bộ dài hạn")
    phaiThuVeChoVayDaiHan = models.BigIntegerField(null=True, blank=True, verbose_name="Phải thu về cho vay dài hạn")
    phaiThuDaiHanKhac = models.BigIntegerField(null=True, blank=True, verbose_name="Phải thu dài hạn khác")
    duPhongPhaiThuDaiHanKhoDoi = models.BigIntegerField(null=True, blank=True, verbose_name="Dự phòng phải thu dài hạn khó đòi")
    taiSanCoDinh = models.BigIntegerField(null=True, blank=True, verbose_name="Tài sản cố định")
    taiSanCoDinhHuuHinh = models.BigIntegerField(null=True, blank=True, verbose_name="Tài sản cố định hữu hình")
    nguyenGia = models.BigIntegerField(null=True, blank=True, verbose_name="Nguyên giá")
    giaTriHaoMonLuyKe = models.BigIntegerField(null=True, blank=True, verbose_name="Giá trị hao mòn lũy kế")
    taiSanCoDinhThueTaiChinh = models.BigIntegerField(null=True, blank=True, verbose_name="Tài sản cố định thuê tài chính")
    taiSanCoDinhVoHinh = models.BigIntegerField(null=True, blank=True, verbose_name="Tài sản cố định vô hình")
    batDongSanDauTu = models.BigIntegerField(null=True, blank=True, verbose_name="Bất động sản đầu tư")
    taiSanDoDangDaiHan = models.BigIntegerField(null=True, blank=True, verbose_name="Tài sản dở dang dài hạn")
    chiPhiSanXuatKinhDoanhDoDangDaiHan = models.BigIntegerField(null=True, blank=True, verbose_name="Chi phí sản xuất kinh doanh dở dang dài hạn")
    chiPhiXayDungCoBanDoDang = models.BigIntegerField(null=True, blank=True, verbose_name="Chi phí xây dựng cơ bản dở dang")
    dauTuTaiChinhDaiHan = models.BigIntegerField(null=True, blank=True, verbose_name="Đầu tư tài chính dài hạn")
    dauTuVaoCongTyCon = models.BigIntegerField(null=True, blank=True, verbose_name="Đầu tư vào công ty con")
    dauTuVaoCongTyLienKetLienDoanh = models.BigIntegerField(null=True, blank=True, verbose_name="Đầu tư vào công ty liên kết liên doanh")
    dauTuGopVonVaoDonViKhac = models.BigIntegerField(null=True, blank=True, verbose_name="Đầu tư góp vốn vào đơn vị khác")
    duPhongDauTuTaiChinhDaiHan = models.BigIntegerField(null=True, blank=True, verbose_name="Dự phòng đầu tư tài chính dài hạn")
    taiSanDaiHanKhac = models.BigIntegerField(null=True, blank=True, verbose_name="Tài sản dài hạn khác")
    chiPhiTraTruocDaiHan = models.BigIntegerField(null=True, blank=True, verbose_name="Chi phí trả trước dài hạn")
    taiSanThueThuNhapHoanLai = models.BigIntegerField(null=True, blank=True, verbose_name="Tài sản thuế thu nhập hoãn lại")
    thietBiVatTuPhuTungThayTheDaiHan = models.BigIntegerField(null=True, blank=True, verbose_name="Thiết bị vật tư phụ tùng thay thế dài hạn")
    loiTheThuongMai = models.BigIntegerField(null=True, blank=True, verbose_name="Lợi thế thương mại")
    
    tongCongTaiSan = models.BigIntegerField(null=True, blank=True, verbose_name="TỔNG CỘNG TÀI SẢN")
    
    # === NGUỒN VỐN ===
    # C. NỢ PHẢI TRẢ
    noPhaiTra = models.BigIntegerField(null=True, blank=True, verbose_name="C. NỢ PHẢI TRẢ")
    noNganHan = models.BigIntegerField(null=True, blank=True, verbose_name="Nợ ngắn hạn")
    phaiTraNguoiBanNganHan = models.BigIntegerField(null=True, blank=True, verbose_name="Phải trả người bán ngắn hạn")
    nguoiMuaTraTienTruocNganHan = models.BigIntegerField(null=True, blank=True, verbose_name="Người mua trả tiền trước ngắn hạn")
    thueVaCacKhoanPhaiNopNhaNuoc = models.BigIntegerField(null=True, blank=True, verbose_name="Thuế và các khoản phải nộp nhà nước")
    phaiTraNguoiLaoDong = models.BigIntegerField(null=True, blank=True, verbose_name="Phải trả người lao động")
    chiPhiPhaiTraNganHan = models.BigIntegerField(null=True, blank=True, verbose_name="Chi phí phải trả ngắn hạn")
    phaiTraNoiBoNganHan = models.BigIntegerField(null=True, blank=True, verbose_name="Phải trả nội bộ ngắn hạn")
    phaiTraTheoTienDoKeHoachHopDongXayDungNH = models.BigIntegerField(null=True, blank=True, verbose_name="Phải trả theo tiến độ kế hoạch hợp đồng xây dựng (NH)")
    doanhThuChuaThucHienNganHan = models.BigIntegerField(null=True, blank=True, verbose_name="Doanh thu chưa thực hiện ngắn hạn")
    phaiTraNganHanKhac = models.BigIntegerField(null=True, blank=True, verbose_name="Phải trả ngắn hạn khác")
    vayVaNoThueTaiChinhNganHan = models.BigIntegerField(null=True, blank=True, verbose_name="Vay và nợ thuê tài chính ngắn hạn")
    duPhongPhaiTraNganHan = models.BigIntegerField(null=True, blank=True, verbose_name="Dự phòng phải trả ngắn hạn")
    quyKhenThuongPhucLoi = models.BigIntegerField(null=True, blank=True, verbose_name="Quỹ khen thưởng phúc lợi")
    quyBinhOnGia = models.BigIntegerField(null=True, blank=True, verbose_name="Quỹ bình ổn giá")
    
    noDaiHan = models.BigIntegerField(null=True, blank=True, verbose_name="Nợ dài hạn")
    phaiTraNguoiBanDaiHan = models.BigIntegerField(null=True, blank=True, verbose_name="Phải trả người bán dài hạn")
    nguoiMuaTraTienTruocDaiHan = models.BigIntegerField(null=True, blank=True, verbose_name="Người mua trả tiền trước dài hạn")
    chiPhiPhaiTraDaiHan = models.BigIntegerField(null=True, blank=True, verbose_name="Chi phí phải trả dài hạn")
    phaiTraNoiBoVeVonKinhDoanh = models.BigIntegerField(null=True, blank=True, verbose_name="Phải trả nội bộ về vốn kinh doanh")
    phaiTraNoiBoDaiHan = models.BigIntegerField(null=True, blank=True, verbose_name="Phải trả nội bộ dài hạn")
    doanhThuChuaThucHienDaiHan = models.BigIntegerField(null=True, blank=True, verbose_name="Doanh thu chưa thực hiện dài hạn")
    phaiTraDaiHanKhac = models.BigIntegerField(null=True, blank=True, verbose_name="Phải trả dài hạn khác")
    vayVaNoThueTaiChinhDaiHan = models.BigIntegerField(null=True, blank=True, verbose_name="Vay và nợ thuê tài chính dài hạn")
    traiPhieuChuyenDoi = models.BigIntegerField(null=True, blank=True, verbose_name="Trái phiếu chuyển đổi")
    coPhieuUuDai = models.BigIntegerField(null=True, blank=True, verbose_name="Cổ phiếu ưu đãi (nợ)")
    thueThuNhapHoanLaiPhaiTra = models.BigIntegerField(null=True, blank=True, verbose_name="Thuế thu nhập hoãn lại phải trả")
    duPhongPhaiTraDaiHan = models.BigIntegerField(null=True, blank=True, verbose_name="Dự phòng phải trả dài hạn")
    quyPhatTrienKhoaHocVaCongNghe = models.BigIntegerField(null=True, blank=True, verbose_name="Quỹ phát triển khoa học và công nghệ")

    # D. VỐN CHỦ SỞ HỮU
    vonChuSoHuu = models.BigIntegerField(null=True, blank=True, verbose_name="D. VỐN CHỦ SỞ HỮU")
    vonChuSoHuuCon = models.BigIntegerField(null=True, blank=True, verbose_name="Vốn chủ sở hữu") # Đặt tên khác để tránh trùng lặp
    vonGopCuaChuSoHuu = models.BigIntegerField(null=True, blank=True, verbose_name="Vốn góp của chủ sở hữu")
    thangDuVonCoPhan = models.BigIntegerField(null=True, blank=True, verbose_name="Thặng dư vốn cổ phần")
    quyenChonChuyenDoiTraiPhieu = models.BigIntegerField(null=True, blank=True, verbose_name="Quyền chọn chuyển đổi trái phiếu")
    vonKhacCuaChuSoHuu = models.BigIntegerField(null=True, blank=True, verbose_name="Vốn khác của chủ sở hữu")
    coPhieuQuy = models.BigIntegerField(null=True, blank=True, verbose_name="Cổ phiếu quỹ")
    chenhLechDanhGiaLaiTaiSan = models.BigIntegerField(null=True, blank=True, verbose_name="Chênh lệch đánh giá lại tài sản")
    chenhLechTyGiaHoiDoai = models.BigIntegerField(null=True, blank=True, verbose_name="Chênh lệch tỷ giá hối đoái")
    quyDauTuPhatTrien = models.BigIntegerField(null=True, blank=True, verbose_name="Quỹ đầu tư phát triển")
    quyHoTroSapXepDoanhNghiep = models.BigIntegerField(null=True, blank=True, verbose_name="Quỹ hỗ trợ sắp xếp doanh nghiệp")
    quyKhacThuocVonChuSoHuu = models.BigIntegerField(null=True, blank=True, verbose_name="Quỹ khác thuộc vốn chủ sở hữu")
    loiNhuanSauThueChuaPhanPhoi = models.BigIntegerField(null=True, blank=True, verbose_name="Lợi nhuận sau thuế chưa phân phối")
    nguonVonDauTuXDCB = models.BigIntegerField(null=True, blank=True, verbose_name="Nguồn vốn đầu tư XDCB")
    loiIchCoDongKhongKiemSoat = models.BigIntegerField(null=True, blank=True, verbose_name="Lợi ích cổ đông không kiểm soát")
    nguonKinhPhiVaQuyKhac = models.BigIntegerField(null=True, blank=True, verbose_name="Nguồn kinh phí và quỹ khác")
    nguonKinhPhi = models.BigIntegerField(null=True, blank=True, verbose_name="Nguồn kinh phí")
    nguonKinhPhiDaHinhThanhTSCD = models.BigIntegerField(null=True, blank=True, verbose_name="Nguồn kinh phí đã hình thành TSCĐ")

    tongCongNguonVon = models.BigIntegerField(null=True, blank=True, verbose_name="TỔNG CỘNG NGUỒN VỐN")

    def __str__(self):
        return f"BCĐKT của {self.baoCao}"

    class Meta:
        verbose_name = "Bảng Cân Đối Kế Toán"
        verbose_name_plural = "Các Bảng Cân Đối Kế Toán"


class BangKetQuaKinhDoanh(models.Model):
    baoCao = models.OneToOneField(TongHopTaiChinh, on_delete=models.CASCADE, primary_key=True, verbose_name="Báo cáo liên quan")

    # Các trường dữ liệu của Bảng Kết Quả Hoạt Động Kinh Doanh
    doanhThuBanHangVaCungCapDichVu = models.BigIntegerField(null=True, blank=True, verbose_name="Doanh thu bán hàng và cung cấp dịch vụ")
    cacKhoanGiamTruDoanhThu = models.BigIntegerField(null=True, blank=True, verbose_name="Các khoản giảm trừ doanh thu")
    doanhThuThuan = models.BigIntegerField(null=True, blank=True, verbose_name="Doanh thu thuần về bán hàng và cung cấp dịch vụ")
    giaVonHangBan = models.BigIntegerField(null=True, blank=True, verbose_name="Giá vốn hàng bán")
    loiNhuanGop = models.BigIntegerField(null=True, blank=True, verbose_name="Lợi nhuận gộp về bán hàng và cung cấp dịch vụ")
    doanhThuHoatDongTaiChinh = models.BigIntegerField(null=True, blank=True, verbose_name="Doanh thu hoạt động tài chính")
    chiPhiTaiChinh = models.BigIntegerField(null=True, blank=True, verbose_name="Chi phí tài chính")
    trongDoChiPhiLaiVay = models.BigIntegerField(null=True, blank=True, verbose_name="Trong đó: Chi phí lãi vay")
    phanLaiLoTrongCongTyLienDoanhLienKet = models.BigIntegerField(null=True, blank=True, verbose_name="Phần lãi lỗ trong công ty liên doanh liên kết")
    chiPhiBanHang = models.BigIntegerField(null=True, blank=True, verbose_name="Chi phí bán hàng")
    chiPhiQuanLyDoanhNghiep = models.BigIntegerField(null=True, blank=True, verbose_name="Chi phí quản lý doanh nghiệp")
    loiNhuanThuanTuHoatDongKinhDoanh = models.BigIntegerField(null=True, blank=True, verbose_name="Lợi nhuận thuần từ hoạt động kinh doanh")
    thuNhapKhac = models.BigIntegerField(null=True, blank=True, verbose_name="Thu nhập khác")
    chiPhiKhac = models.BigIntegerField(null=True, blank=True, verbose_name="Chi phí khác")
    loiNhuanKhac = models.BigIntegerField(null=True, blank=True, verbose_name="Lợi nhuận khác")
    tongLoiNhuanKeToanTruocThue = models.BigIntegerField(null=True, blank=True, verbose_name="Tổng lợi nhuận kế toán trước thuế")
    chiPhiThueTNDNHienHanh = models.BigIntegerField(null=True, blank=True, verbose_name="Chi phí thuế TNDN hiện hành")
    chiPhiThueTNDNHoanLai = models.BigIntegerField(null=True, blank=True, verbose_name="Chi phí thuế TNDN hoãn lại")
    loiNhuanSauThueThuNhapDoanhNghiep = models.BigIntegerField(null=True, blank=True, verbose_name="Lợi nhuận sau thuế thu nhập doanh nghiệp")

    def __str__(self):
        return f"KQKD của {self.baoCao}"

    class Meta:
        verbose_name = "Bảng Kết Quả Kinh Doanh"
        verbose_name_plural = "Các Bảng Kết Quả Kinh Doanh"




class Conversation(models.Model):
 
    title = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        # Hiển thị tiêu đề nếu có, nếu không thì hiển thị ID
        if self.title:
            return f"'{self.title}' của {self.id}"
        return f"Cuộc trò chuyện {self.id}"

class Message(models.Model):
    
    # Định nghĩa các lựa chọn cho người gửi
    class SenderChoices(models.TextChoices):
        USER = 'user', 'User'
        BOT = 'bot', 'Bot'

    # Khóa ngoại liên kết đến cuộc trò chuyện
    conversation = models.ForeignKey(
        Conversation, 
        on_delete=models.CASCADE,
        related_name="messages" # Rất quan trọng: giúp lấy tất cả tin nhắn từ 1 conversation
    )
    
    # Người gửi: 'user' hoặc 'bot'
    sender = models.CharField(
        max_length=10, 
        choices=SenderChoices.choices,
        default=SenderChoices.USER
    )
    
    # Nội dung tin nhắn, dùng TextField vì có thể rất dài
    content = models.TextField()
    
    # Dấu thời gian, tự động thêm khi tin nhắn được tạo
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Sắp xếp tin nhắn theo thời gian tạo (cũ nhất đến mới nhất)
        ordering = ['timestamp']

    def __str__(self):
        # Hiển thị 50 ký tự đầu tiên của tin nhắn
        return f"{self.get_sender_display()}: {self.content[:50]}..."