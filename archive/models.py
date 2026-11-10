"""
My data model. It follows the Domain Model page in the wiki:

    Category (level 1 and 2) > CraftType (level 3) > AttributeDefinition
    CraftEntry fills in one AttributeValue for each definition of its type.

The idea from class: an entry is not free text. The craft type decides
which fields a user fills in. The only free text is the personal story.
"""

from django.conf import settings
from django.db import models
from django.urls import reverse

from .units import UNIT_CHOICES, from_base


class Category(models.Model):
    """Level 1 (domain, e.g. Textile Arts) or level 2 (family, e.g. Flat-woven Rugs)."""

    name = models.CharField(max_length=100)
    # A domain has no parent. A family has a domain as parent.
    parent = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.CASCADE, related_name="children"
    )

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "categories"

    def __str__(self):
        if self.parent:
            return f"{self.parent.name} > {self.name}"
        return self.name

    @property
    def level(self):
        # I only have two category levels, the third level is the craft type.
        return 2 if self.parent else 1


class CraftType(models.Model):
    """Level 3 of the tree, e.g. Kilim. It owns the list of fields (attributes)."""

    name = models.CharField(max_length=100, unique=True)
    # The craft type always hangs under a level 2 category (a family).
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="craft_types")
    description = models.TextField(blank=True)
    # Predefined types come from my seed data, the others are made by users.
    is_predefined = models.BooleanField(default=False)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL
    )

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def path(self):
        # Full path for breadcrumbs: Textile Arts > Flat-woven Rugs > Kilim
        return f"{self.category} > {self.name}"


class AttributeDefinition(models.Model):
    """One field of a craft type, for example "Width (cm)" or "Colors"."""

    MEASUREMENT = "measurement"
    SINGLE = "single"
    MULTIPLE = "multiple"
    PERIOD = "period"
    YES_NO = "yesno"
    SHORT_TEXT = "short_text"
    DATA_TYPES = [
        (MEASUREMENT, "Measurement (number with a unit)"),
        (SINGLE, "Single choice"),
        (MULTIPLE, "Multiple choice"),
        (PERIOD, "Year or period"),
        (YES_NO, "Yes or no"),
        (SHORT_TEXT, "Short name (max 100 characters)"),
    ]

    craft_type = models.ForeignKey(CraftType, on_delete=models.CASCADE, related_name="attributes")
    name = models.CharField(max_length=100)
    data_type = models.CharField(max_length=20, choices=DATA_TYPES)
    # Only for measurements: the unit I show by default (cm, kg...).
    unit = models.CharField(max_length=5, choices=UNIT_CHOICES, blank=True)
    # Only for choices: the allowed values, one per line.
    allowed_values = models.TextField(blank=True, help_text="One value per line")
    required = models.BooleanField(default=False)
    # If true, the value is shown in the caption under the photo (FR-3.7).
    show_in_caption = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]
        unique_together = ["craft_type", "name"]

    def __str__(self):
        return f"{self.craft_type.name}: {self.name}"

    def choices_list(self):
        # I store the allowed values as text, one per line, and split them here.
        return [line.strip() for line in self.allowed_values.splitlines() if line.strip()]


class Color(models.Model):
    """The fixed color palette. An entry can have many colors (FR-3.4)."""

    name = models.CharField(max_length=30, unique=True)
    hex_code = models.CharField(max_length=7, help_text="For example #b22222")

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Tag(models.Model):
    name = models.CharField(max_length=50, unique=True)
    # Predefined tags come from the seed data (FR-4.1).
    is_predefined = models.BooleanField(default=False)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class CraftEntry(models.Model):
    """One object a user adds, for example my grandmother's kilim."""

    title = models.CharField(max_length=150)
    craft_type = models.ForeignKey(CraftType, on_delete=models.PROTECT, related_name="entries")
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="entries"
    )
    # Production place as a map pin (FR-5.1).
    latitude = models.FloatField()
    longitude = models.FloatField()
    place_name = models.CharField(max_length=150, blank=True)
    colors = models.ManyToManyField(Color, blank=True)
    tags = models.ManyToManyField(Tag, blank=True, related_name="entries")
    # The only free text field (FR-3.6).
    personal_story = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    # The admin can hide an entry after a report (FR-7.3). Hidden entries are
    # not shown in lists, search or on the map.
    is_hidden = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]
        verbose_name_plural = "craft entries"

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("entry_detail", args=[self.pk])

    def to_dict(self):
        """
        The entry as plain data for the JSON export (NFR-8). Everything except
        the personal story is structured, so another program can read it.
        """
        return {
            "id": self.pk,
            "title": self.title,
            "craft_type": self.craft_type.name,
            "category": str(self.craft_type.category),
            "owner": self.owner.username,
            "place": {
                "name": self.place_name,
                "latitude": self.latitude,
                "longitude": self.longitude,
            },
            "attributes": {v.definition.name: v.export_value() for v in self.values_in_order()},
            "colors": [c.name for c in self.colors.all()],
            "tags": [t.name for t in self.tags.all()],
            "personal_story": self.personal_story,
            "created_at": self.created_at.isoformat(),
        }

    def values_in_order(self):
        # The values sorted the same way as the fields of the craft type.
        return self.values.select_related("definition").order_by("definition__order", "definition__id")

    def caption(self):
        """
        Short text under the photo, for example:
        120 x 180 cm, red, indigo, cream, wool, Kayseri
        """
        parts = []
        values = {v.definition.name: v for v in self.values_in_order()}

        # If the type has Width and Length I show them together like "120 x 180 cm".
        width = values.get("Width")
        length = values.get("Length")
        if width and length and width.number is not None and length.number is not None:
            unit = width.definition.unit
            parts.append(f"{width.display_number()} x {length.display_number()} {unit}")

        # Then every other field that is marked for the caption.
        for name, value in values.items():
            if name in ("Width", "Length"):
                continue
            if value.definition.show_in_caption and value.display():
                parts.append(value.display())

        color_names = [c.name for c in self.colors.all()]
        if color_names:
            parts.append(", ".join(color_names))
        if self.place_name:
            parts.append(self.place_name)
        return " · ".join(parts)


class EntryImage(models.Model):
    entry = models.ForeignKey(CraftEntry, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to="entries/")

    def __str__(self):
        return f"Image of {self.entry}"


class AttributeValue(models.Model):
    """The value one entry has for one field of its craft type."""

    entry = models.ForeignKey(CraftEntry, on_delete=models.CASCADE, related_name="values")
    definition = models.ForeignKey(AttributeDefinition, on_delete=models.CASCADE)
    # Measurements are always saved in the base unit (cm or g), see units.py.
    number = models.FloatField(null=True, blank=True)
    # Everything else is saved as text.
    # For multiple choice I save "|red|indigo|" so I can search for "|red|".
    text = models.TextField(blank=True)

    class Meta:
        unique_together = ["entry", "definition"]

    def __str__(self):
        return f"{self.definition.name} = {self.display()}"

    def display_number(self):
        # Convert back from the base unit to the unit of the field, and drop ".0".
        shown = from_base(self.number, self.definition.unit)
        return f"{shown:g}"

    def display(self):
        """The value as people should read it."""
        d = self.definition
        if d.data_type == AttributeDefinition.MEASUREMENT:
            if self.number is None:
                return ""
            return f"{self.display_number()} {d.unit}"
        if d.data_type == AttributeDefinition.MULTIPLE:
            return ", ".join(self.multiple_values())
        return self.text

    def multiple_values(self):
        return [v for v in self.text.split("|") if v]

    def export_value(self):
        """The value for the JSON export. Measurements keep their base unit."""
        d = self.definition
        if d.data_type == AttributeDefinition.MEASUREMENT:
            base_unit = "cm" if d.unit in ("mm", "cm", "m") else "g"
            return {"value": self.number, "unit": base_unit}
        if d.data_type == AttributeDefinition.MULTIPLE:
            return self.multiple_values()
        return self.text


class Report(models.Model):
    """
    A report about wrong or meaningless data (FR-7.1, FR-7.2).

    Only the admin sees reports. A report never changes the content by
    itself, the admin decides what to do.
    A report is about exactly one thing: an entry, a craft type or a tag.
    """

    REASONS = [
        ("wrong_value", "A value is wrong (for example an impossible size)"),
        ("meaningless", "Meaningless or nonsense data"),
        ("duplicate", "Duplicate of another entry or type"),
        ("wrong_type", "Wrong craft type or category"),
        ("inappropriate", "Inappropriate content"),
    ]
    OPEN = "open"
    RESOLVED = "resolved"
    STATUSES = [(OPEN, "Open"), (RESOLVED, "Resolved")]

    reporter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    entry = models.ForeignKey(CraftEntry, null=True, blank=True, on_delete=models.CASCADE)
    craft_type = models.ForeignKey(CraftType, null=True, blank=True, on_delete=models.CASCADE)
    tag = models.ForeignKey(Tag, null=True, blank=True, on_delete=models.CASCADE)
    reason = models.CharField(max_length=20, choices=REASONS)
    status = models.CharField(max_length=10, choices=STATUSES, default=OPEN)
    # What the admin did, for example "hidden" or "dismissed".
    admin_action = models.CharField(max_length=30, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"Report on {self.target()} ({self.get_reason_display()})"

    def target(self):
        return self.entry or self.craft_type or self.tag

    def target_kind(self):
        if self.entry_id:
            return "entry"
        if self.craft_type_id:
            return "craft type"
        return "tag"
