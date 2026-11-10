from django.urls import path

from . import views

# All the pages of my app. The names are used in templates with {% url %}.
urlpatterns = [
    path("", views.home, name="home"),
    path("signup/", views.signup, name="signup"),
    path("users/<str:username>/", views.profile, name="profile"),
    # Entries
    path("entries/", views.entry_list, name="entry_list"),
    path("entries/new/", views.choose_craft_type, name="choose_craft_type"),
    path("entries/new/<int:type_id>/", views.add_entry, name="add_entry"),
    path("entries/<int:pk>/", views.entry_detail, name="entry_detail"),
    path("entries/<int:pk>/edit/", views.edit_entry, name="edit_entry"),
    path("entries/<int:pk>/delete/", views.delete_entry, name="delete_entry"),
    path("entries/<int:pk>/json/", views.entry_json, name="entry_json"),
    path("export.json", views.export_json, name="export_json"),
    # Browsing and the map
    path("browse/", views.browse, name="browse"),
    path("map/", views.map_view, name="map"),
    # Craft types and tags
    path("craft-types/new/", views.define_craft_type, name="define_craft_type"),
    path("craft-types/similar/", views.similar_craft_types, name="similar_craft_types"),
    path("tags/suggest/", views.tag_suggestions, name="tag_suggestions"),
    # Reports
    path("report/<str:kind>/<int:pk>/", views.report_content, name="report_content"),
    path("reports/", views.report_queue, name="report_queue"),
    path("reports/<int:pk>/resolve/", views.resolve_report, name="resolve_report"),
]
