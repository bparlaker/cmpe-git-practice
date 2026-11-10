from django.urls import path

from . import views

# All the pages of my app. The names are used in templates with {% url %}.
urlpatterns = [
    path("", views.home, name="home"),
    path("signup/", views.signup, name="signup"),
    path("entries/new/", views.choose_craft_type, name="choose_craft_type"),
    path("entries/new/<int:type_id>/", views.add_entry, name="add_entry"),
    path("entries/<int:pk>/", views.entry_detail, name="entry_detail"),
]
