from django import forms
from django.conf import settings
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import AttributeDefinition, Category, Color, CraftType, Report, Tag
from .similar import same_name_exists, similar_names
from .units import to_base, from_base, units_like


def add_bootstrap_classes(form):
    """
    Bootstrap needs a CSS class on every input to look nice. Instead of
    writing the class in every template, I add it here once.
    """
    for field in form.fields.values():
        widget = field.widget
        if isinstance(widget, (forms.CheckboxSelectMultiple, forms.HiddenInput, forms.RadioSelect)):
            continue
        if isinstance(widget, forms.CheckboxInput):
            widget.attrs["class"] = "form-check-input"
            continue
        if isinstance(widget, forms.Select):
            widget.attrs["class"] = "form-select"
        else:
            widget.attrs["class"] = "form-control"


class SignUpForm(UserCreationForm):
    """Django's own sign up form plus an e-mail field (FR-1.1)."""

    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ["username", "email"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        add_bootstrap_classes(self)

    def clean_email(self):
        # Two accounts with the same e-mail would be confusing, so I block it.
        email = self.cleaned_data["email"]
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("This e-mail is already used.")
        return email


class MultipleImageInput(forms.ClearableFileInput):
    # Django needs this flag to let me pick more than one file at once.
    allow_multiple_selected = True


class MultipleImageField(forms.ImageField):
    """An image field that accepts a list of files (FR-3.7: one or more images)."""

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleImageInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_clean = super().clean
        if isinstance(data, (list, tuple)):
            return [single_clean(d, initial) for d in data]
        if data:
            return [single_clean(data, initial)]
        return []


class EntryForm(forms.Form):
    """
    The form for adding a craft entry.

    The fixed part (title, place, colors, tags, story) is the same for every
    craft type. The rest of the fields are built from the attribute
    definitions of the chosen craft type, so a kilim form and an ebru form
    look different. There is no way to add your own field here (FR-3.2).
    """

    title = forms.CharField(max_length=150)
    latitude = forms.FloatField(widget=forms.HiddenInput)
    longitude = forms.FloatField(widget=forms.HiddenInput)
    place_name = forms.CharField(max_length=150, required=False)
    colors = forms.ModelMultipleChoiceField(
        queryset=Color.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
    )
    tags = forms.CharField(
        required=False,
        help_text="Separate tags with commas, for example: kayseri, dowry",
    )
    # Only needed when a new tag looks like a typo of an existing tag.
    confirm_new_tags = forms.BooleanField(
        required=False,
        label="Yes, I really want to create these new tags",
    )
    images = MultipleImageField(required=False)
    personal_story = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 4}),
        required=False,
        help_text="The only free text field. Tell the story of this object.",
    )

    def __init__(self, *args, craft_type, entry=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.craft_type = craft_type
        self.definitions = list(craft_type.attributes.all())

        # The latitude and longitude are hidden, the map fills them in.
        # I give a clear error if the user forgot to drop a pin.
        self.fields["latitude"].error_messages["required"] = "Please drop a pin on the map."
        self.fields["longitude"].error_messages["required"] = "Please drop a pin on the map."

        # I build one form field (or two for measurements) per attribute.
        for d in self.definitions:
            self.fields.update(self.make_fields(d))

        # When editing, I fill in the values the entry already has.
        if entry is not None:
            self.fill_initial(entry)

        add_bootstrap_classes(self)

    def make_fields(self, d):
        name = f"attr_{d.id}"
        label = d.name
        if d.data_type == AttributeDefinition.MEASUREMENT:
            return {
                name: forms.FloatField(label=label, required=d.required, min_value=0),
                name + "_unit": forms.ChoiceField(
                    label=label + " unit",
                    choices=[(u, u) for u in units_like(d.unit)],
                    initial=d.unit,
                    # The unit is not required alone: if the number is empty,
                    # the unit does not matter. If it is missing I use the default.
                    required=False,
                ),
            }
        if d.data_type == AttributeDefinition.SINGLE:
            choices = [("", "---")] + [(c, c) for c in d.choices_list()]
            return {name: forms.ChoiceField(label=label, choices=choices, required=d.required)}
        if d.data_type == AttributeDefinition.MULTIPLE:
            return {
                name: forms.MultipleChoiceField(
                    label=label,
                    choices=[(c, c) for c in d.choices_list()],
                    widget=forms.CheckboxSelectMultiple,
                    required=d.required,
                )
            }
        if d.data_type == AttributeDefinition.YES_NO:
            choices = [("", "---"), ("Yes", "Yes"), ("No", "No")]
            return {name: forms.ChoiceField(label=label, choices=choices, required=d.required)}
        if d.data_type == AttributeDefinition.PERIOD:
            return {
                name: forms.CharField(
                    label=label,
                    max_length=50,
                    required=d.required,
                    help_text="A year (1965), a range (1950-1970) or a period (Ottoman)",
                )
            }
        # Short text, for example the maker's name.
        return {name: forms.CharField(label=label, max_length=100, required=d.required)}

    def fill_initial(self, entry):
        self.initial.update(
            {
                "title": entry.title,
                "latitude": entry.latitude,
                "longitude": entry.longitude,
                "place_name": entry.place_name,
                "colors": list(entry.colors.all()),
                "tags": ", ".join(t.name for t in entry.tags.all()),
                "personal_story": entry.personal_story,
            }
        )
        for v in entry.values.all():
            name = f"attr_{v.definition_id}"
            if v.definition.data_type == AttributeDefinition.MEASUREMENT:
                self.initial[name] = from_base(v.number, v.definition.unit)
                self.initial[name + "_unit"] = v.definition.unit
            elif v.definition.data_type == AttributeDefinition.MULTIPLE:
                self.initial[name] = v.multiple_values()
            else:
                self.initial[name] = v.text

    def clean_images(self):
        images = self.cleaned_data.get("images") or []
        for img in images:
            # NFR-4: only JPG or PNG, at most 5 MB.
            if img.size > settings.MAX_IMAGE_SIZE:
                raise forms.ValidationError(f"{img.name} is bigger than 5 MB.")
            if not img.name.lower().endswith((".jpg", ".jpeg", ".png")):
                raise forms.ValidationError(f"{img.name} is not a JPG or PNG file.")
        return images

    def clean(self):
        cleaned = super().clean()
        # "Kayseri, dowry ,," -> ["kayseri", "dowry"]
        names = []
        for part in cleaned.get("tags", "").split(","):
            name = part.strip().lower()
            if name and name not in names:
                names.append(name)

        # FR-4.3: if a new tag is almost the same as an existing one, it is
        # probably a typo, so I ask "Did you mean ...?" before creating it.
        existing = list(Tag.objects.values_list("name", flat=True))
        hints = []
        for name in names:
            if name in existing:
                continue
            close = similar_names(name, existing, max_distance=2)
            if close:
                hints.append(f'"{name}": did you mean "{close[0]}"?')
        if hints and not cleaned.get("confirm_new_tags"):
            self.add_error(
                "tags",
                "Some tags look like existing ones. "
                + " ".join(hints)
                + " Fix the tag, or tick the box below to create it anyway.",
            )
        cleaned["tags"] = names
        return cleaned

    def attribute_fields(self):
        """
        Pairs of (definition, field, unit field) so the template can show
        each measurement and its unit next to each other.
        """
        rows = []
        for d in self.definitions:
            name = f"attr_{d.id}"
            unit_field = self[name + "_unit"] if name + "_unit" in self.fields else None
            rows.append((d, self[name], unit_field))
        return rows

    def attribute_values(self):
        """
        Turns the cleaned form data into (definition, number, text) so the
        view can save AttributeValue rows. Empty optional fields are skipped.
        """
        result = []
        for d in self.definitions:
            name = f"attr_{d.id}"
            value = self.cleaned_data.get(name)
            if value in (None, "", []):
                continue
            if d.data_type == AttributeDefinition.MEASUREMENT:
                unit = self.cleaned_data.get(name + "_unit") or d.unit
                result.append((d, to_base(value, unit), ""))
            elif d.data_type == AttributeDefinition.MULTIPLE:
                result.append((d, None, "|" + "|".join(value) + "|"))
            else:
                result.append((d, None, value))
        return result


class CraftTypeForm(forms.ModelForm):
    """
    A user defines a new craft type (FR-2.3). The fields of the type are
    added below it with AttributeFormSet.
    """

    confirm_new_name = forms.BooleanField(
        required=False,
        label="This is really a new craft type, not one of the suggested ones",
    )

    class Meta:
        model = CraftType
        fields = ["name", "category", "description"]
        labels = {"category": "Family (level 2)"}
        widgets = {"description": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # A craft type can only hang under a family (level 2), not a domain.
        self.fields["category"].queryset = Category.objects.exclude(parent=None)
        add_bootstrap_classes(self)

    def clean(self):
        cleaned = super().clean()
        name = cleaned.get("name", "")
        existing = list(CraftType.objects.values_list("name", flat=True))
        if name and same_name_exists(name, existing):
            self.add_error("name", "This craft type already exists.")
        elif name:
            # FR-2.5: similar names (max 2 letters different) are suggested.
            close = similar_names(name, existing)
            if close and not cleaned.get("confirm_new_name"):
                self.add_error(
                    "name",
                    "Similar types already exist: " + ", ".join(close)
                    + ". Use one of them, or tick the box below if yours is really new.",
                )
        return cleaned


class AttributeDefinitionForm(forms.ModelForm):
    class Meta:
        model = AttributeDefinition
        fields = ["name", "data_type", "unit", "allowed_values", "required", "show_in_caption"]
        widgets = {"allowed_values": forms.Textarea(attrs={"rows": 2})}
        labels = {"show_in_caption": "Show under photo"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        add_bootstrap_classes(self)

    def clean(self):
        cleaned = super().clean()
        data_type = cleaned.get("data_type")
        if data_type == AttributeDefinition.MEASUREMENT and not cleaned.get("unit"):
            # UC-07 alternative flow 3a: a measurement needs a unit.
            self.add_error("unit", "A measurement needs a unit.")
        if data_type != AttributeDefinition.MEASUREMENT:
            # A unit only makes sense for measurements, so I clear it.
            cleaned["unit"] = ""
        if data_type in (AttributeDefinition.SINGLE, AttributeDefinition.MULTIPLE):
            if not cleaned.get("allowed_values", "").strip():
                self.add_error("allowed_values", "Write the allowed values, one per line.")
        return cleaned


# A list of field forms under the craft type form. "extra=3" shows three
# empty rows, and at least one field is required.
AttributeFormSet = forms.inlineformset_factory(
    CraftType,
    AttributeDefinition,
    form=AttributeDefinitionForm,
    extra=3,
    min_num=1,
    validate_min=True,
    can_delete=False,
)


class ReportForm(forms.Form):
    """The user only picks a reason from a list (FR-7.1)."""

    reason = forms.ChoiceField(choices=Report.REASONS, widget=forms.RadioSelect)


class FilterForm(forms.Form):
    """
    Search and filter (FR-6.2, FR-6.3). When a craft type is chosen, I add a
    filter for each of its fields: a min and max for measurements, and a
    list for choices.
    """

    q = forms.CharField(required=False, label="Keyword")
    craft_type = forms.ModelChoiceField(
        queryset=CraftType.objects.all(), required=False, empty_label="All craft types"
    )
    color = forms.ModelChoiceField(queryset=Color.objects.all(), required=False, empty_label="Any color")
    tag = forms.CharField(required=False, widget=forms.HiddenInput)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.attribute_filters = []
        craft_type = None
        if self.is_bound and self.data.get("craft_type"):
            craft_type = CraftType.objects.filter(pk=self.data.get("craft_type")).first()

        if craft_type:
            for d in craft_type.attributes.all():
                if d.data_type == AttributeDefinition.MEASUREMENT:
                    self.fields[f"min_{d.id}"] = forms.FloatField(required=False, label=f"{d.name} from")
                    self.fields[f"max_{d.id}"] = forms.FloatField(required=False, label="to")
                    # The default unit of the field comes first in the list, so
                    # it is the one selected when the user has not chosen yet.
                    units = [d.unit] + [u for u in units_like(d.unit) if u != d.unit]
                    self.fields[f"unit_{d.id}"] = forms.ChoiceField(
                        choices=[(u, u) for u in units], required=False, label="unit"
                    )
                    self.attribute_filters.append((d, "measurement"))
                elif d.data_type in (AttributeDefinition.SINGLE, AttributeDefinition.MULTIPLE):
                    choices = [("", "Any")] + [(c, c) for c in d.choices_list()]
                    self.fields[f"val_{d.id}"] = forms.ChoiceField(choices=choices, required=False, label=d.name)
                    self.attribute_filters.append((d, "choice"))
        add_bootstrap_classes(self)

    def filter_rows(self):
        """Ready to show rows for the template: (definition, kind, fields...)."""
        rows = []
        for d, kind in self.attribute_filters:
            if kind == "measurement":
                rows.append((d, kind, [self[f"min_{d.id}"], self[f"max_{d.id}"], self[f"unit_{d.id}"]]))
            else:
                rows.append((d, kind, [self[f"val_{d.id}"]]))
        return rows
