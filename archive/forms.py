from django import forms
from django.conf import settings
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import AttributeDefinition, Color
from .units import to_base, from_base, units_like


def add_bootstrap_classes(form):
    """
    Bootstrap needs a CSS class on every input to look nice. Instead of
    writing the class in every template, I add it here once.
    """
    for field in form.fields.values():
        widget = field.widget
        if isinstance(widget, (forms.CheckboxSelectMultiple, forms.HiddenInput)):
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

    def clean_tags(self):
        # "Kayseri, dowry ,," -> ["kayseri", "dowry"]
        raw = self.cleaned_data.get("tags", "")
        names = []
        for part in raw.split(","):
            name = part.strip().lower()
            if name and name not in names:
                names.append(name)
        return names

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
