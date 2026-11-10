from django.contrib import admin

from .models import (
    AttributeDefinition,
    AttributeValue,
    Category,
    Color,
    CraftEntry,
    CraftType,
    EntryImage,
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
    list_display = ["title", "craft_type", "owner", "place_name", "created_at"]
    list_filter = ["craft_type"]
    search_fields = ["title", "place_name"]
    inlines = [AttributeValueInline, EntryImageInline]


admin.site.register(Color)
admin.site.register(Tag)
