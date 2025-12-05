from django.urls import path
from investment_advisor import views

urlpatterns = [
    path('', views.home, name='home'),
    path('congty_form/', views.congty_form, name='congty_form'),
    path('thitruong_form/', views.thitruong_form, name='thitruong_form'),
    path('tonghoptaichinh_form/', views.tonghoptaichinh_form, name='tonghoptaichinh_form'),
    path('bangcandoiketoan_form/', views.bangcandoiketoan_form, name='bangcandoiketoan_form'),
    path('bangketquakinhdoanh_form/', views.bangketquakinhdoanh_form, name='bangketquakinhdoanh_form'),
    path('file_upload/', views.file_upload, name='file_upload'),
]


# API
urlpatterns += [
    path('api/get_congty_data/', views.get_CongTy_data, name='get_CongTy_data'),
    path('api/get_tonghoptaichinh_data/', views.get_TongHopTaiChinh_data, name='get_TongHopTaiChinh_data'),
    path('api/get_thitruongchungkhoan_data/', views.get_ThiTruongChungKhoan_data, name='get_ThiTruongChungKhoan_data'),
    path('api/get_bangcandoikettoan_data/', views.get_BangCanDoiKeToan_data, name='get_BangCanDoiKeToan_data'),
    path('api/get_bangketquakinhdoanh_data/', views.get_BangKetQuaKinhDoanh_data, name='get_BangKetQuaKinhDoanh_data'),

    path('api/post_congty_data/', views.post_congty_data, name='post_congty_data'),
    path('api/post_thitruong_data/', views.post_thitruong_data, name='post_thitruong_data'),
    path('api/post_tonghoptaichinh_data/', views.post_tonghoptaichinh_data, name='post_tonghoptaichinh_data'),
    path('api/post_bangcandoiketoan_data/', views.post_bangcandoiketoan_data, name='post_bangcandoiketoan_data'),
    path('api/post_bangketquakinhdoanh_data/', views.post_bangketquakinhdoanh_data, name='post_bangketquakinhdoanh_data'),
]

#retrieve querry
urlpatterns += [
    path('querry/retrieve_bangcandoikt/', views.retrieve_bangcandoikt, name='retrieve_bangcandoikt'),
]

# Chatbot view
urlpatterns += [
    path('chatbot/', views.chat_view, name='chat_view'),
    path('api/save-message/', views.save_message_view, name='save-message'),
    path('api/financial-ratios/', views.calculate_financial_ratios_view, name='financial_ratios_api'),
]

## Chart view
urlpatterns += [
    path('chart/', views.chart_view, name='chart_view'),
    path('chart_2/', views.chart_view_2, name='chart_view_2'),
    path('table/', views.table_view, name='table_view'),
    path('tableau/', views.tableau_view, name='tableau_view'),
]  

# Download financial ratios sheet
urlpatterns += [
    path('download-financial-ratios/', views.export_financial_ratios_excel, name='export_financial_ratios_excel'),
]