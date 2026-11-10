from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render

from .forms import EntryForm, SignUpForm
from .models import AttributeValue, Category, CraftEntry, CraftType, EntryImage, Tag


def home(request):
    # The newest entries on the start page.
    entries = CraftEntry.objects.select_related("craft_type", "owner")[:12]
    return render(request, "archive/home.html", {"entries": entries})


def signup(request):
    """US-01: a visitor creates an account and is logged in right away."""
    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f"Welcome, {user.username}! Your account is ready.")
            return redirect("home")
    else:
        form = SignUpForm()
    return render(request, "registration/signup.html", {"form": form})


@login_required
def choose_craft_type(request):
    """
    Step 1 of adding an entry: pick the craft type.
    I show the tree as Domain > Family > Craft Type so it matches the wiki.
    """
    domains = Category.objects.filter(parent=None).prefetch_related("children__craft_types")
    return render(request, "archive/choose_type.html", {"domains": domains})


def save_entry(form, entry, user):
    """
    Saves an entry from a valid EntryForm. I use it for adding and (later)
    editing, so the saving logic is only written once.
    """
    data = form.cleaned_data
    entry.title = data["title"]
    entry.latitude = data["latitude"]
    entry.longitude = data["longitude"]
    entry.place_name = data["place_name"]
    entry.personal_story = data["personal_story"]
    if entry.pk is None:
        entry.owner = user
        entry.craft_type = form.craft_type

    # transaction.atomic: if something fails in the middle, nothing is saved.
    with transaction.atomic():
        entry.save()
        entry.colors.set(data["colors"])

        tags = [Tag.objects.get_or_create(name=name)[0] for name in data["tags"]]
        entry.tags.set(tags)

        # I delete the old values and write them again. It is simple and the
        # number of fields per entry is small.
        entry.values.all().delete()
        for definition, number, text in form.attribute_values():
            AttributeValue.objects.create(entry=entry, definition=definition, number=number, text=text)

        for image in data["images"]:
            EntryImage.objects.create(entry=entry, image=image)
    return entry


@login_required
def add_entry(request, type_id):
    """US-02 and US-03: fill in the fields of the chosen craft type and drop a pin."""
    craft_type = get_object_or_404(CraftType, pk=type_id)
    if request.method == "POST":
        form = EntryForm(request.POST, request.FILES, craft_type=craft_type)
        if form.is_valid():
            entry = save_entry(form, CraftEntry(), request.user)
            messages.success(request, "Your entry is saved.")
            return redirect(entry)
        messages.error(request, "Please fix the fields marked in red.")
    else:
        form = EntryForm(craft_type=craft_type)
    return render(
        request, "archive/entry_form.html", {"form": form, "craft_type": craft_type}
    )


def entry_detail(request, pk):
    """US-04: everyone can see an entry, with a caption under the photo."""
    entry = get_object_or_404(
        CraftEntry.objects.select_related("craft_type__category__parent", "owner"), pk=pk
    )
    return render(request, "archive/entry_detail.html", {"entry": entry})
