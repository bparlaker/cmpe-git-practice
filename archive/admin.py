from django.contrib import admin

from .models import (
    AttributeDefinition,
    AttributeValue,
    Category,
    Color,
    CraftEntry,
    CraftType,
    EntryImage,
    Report,
    Tag,
)


# The fields of a craft type are edited on the craft type page itself.
class AttributeDefinitionInline(admin.TabularInline):
    model = AttributeDefinition
    extra = 1


@admin.register(CraftType)
class CraftTypeAdmin(admin.ModelAdmin):
    list_display = ["name", "category", "is_predefined", "created_by"]
    list_filter = ["is_predefined", "category"]
    inlines = [AttributeDefinitionInline]


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "parent"]


# On an entry page in the admin I also want to see its values and photos.
class AttributeValueInline(admin.TabularInline):
    model = AttributeValue
    extra = 0


class EntryImageInline(admin.TabularInline):
    model = EntryImage
    extra = 0


@admin.register(CraftEntry)
class CraftEntryAdmin(admin.ModelAdmin):
    list_display = ["title", "craft_type", "owner", "place_name", "is_hidden", "created_at"]
    list_filter = ["craft_type", "is_hidden"]
    search_fields = ["title", "place_name"]
    inlines = [AttributeValueInline, EntryImageInline]


admin.site.register(Color)
admin.site.register(Tag)


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ["__str__", "reporter", "status", "admin_action", "created_at"]
    list_filter = ["status", "reason"]
    actions = ["mark_resolved"]

    # A shortcut in the admin list: select reports and mark them resolved.
    @admin.action(description="Mark selected reports as resolved")
    def mark_resolved(self, request, queryset):
        queryset.update(status=Report.RESOLVED, admin_action="dismiss")
