from django.urls import path, include
from rest_framework.routers import DefaultRouter

from mediaapp.views import upload_chunk, get_hls_playlist, get_image_thumbnail, upload_img, upload_file, get_pdf_url, delete_file

router = DefaultRouter()
# router.register(r"media", MediaFileViewSet)

urlpatterns = [
    path("", include(router.urls)),
    path('upload_file/', upload_file, name='upload-file'),
    path('upload_chunk/', upload_chunk, name='upload-chunk'),
    path('upload_image/', upload_img, name='upload-image'),
    path('video/<uuid:self_id>/hls_playlist/', get_hls_playlist, name='get-hls-playlist'),
    path('image/<uuid:self_id>/get_thumbnail/', get_image_thumbnail, name='get-thumbnail'),
    path('doc/<uuid:self_id>/get_pdf_url/', get_pdf_url, name='get-pdf-url'),
    path('delete_file/<str:file_type>/<str:self_id>/', delete_file, name='delete-file'),
]
