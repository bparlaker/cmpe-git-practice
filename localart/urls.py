from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.static import serve

urlpatterns = [
    path("admin/", admin.site.urls),
    # Django's ready made login and logout pages.
    path("accounts/", include("django.contrib.auth.urls")),
    path("", include("archive.urls")),
    # Uploaded photos. Django normally serves them only in DEBUG mode, but on
    # the free Render plan I have no other server for them, so I serve them
    # here. This is fine for a small class project, not for a big site.
    re_path(r"^media/(?P<path>.*)$", serve, {"document_root": settings.MEDIA_ROOT}),
]
