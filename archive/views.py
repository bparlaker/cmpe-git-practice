from urllib.parse import quote

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, Q
from django.http import Http404, HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import (
    AttributeFormSet,
    CraftTypeForm,
    EntryForm,
    FilterForm,
    ReportForm,
    SignUpForm,
)
from .models import (
    AttributeDefinition,
    AttributeValue,
    Category,
    CraftEntry,
    CraftType,
    EntryImage,
    Report,
    Tag,
)
from .similar import similar_names
from .units import to_base


def visible_entries():
    # Hidden entries (after a report) are never listed for normal users.
    return CraftEntry.objects.filter(is_hidden=False).select_related("craft_type", "owner")


def home(request):
    # The newest entries on the start page.
    return render(request, "archive/home.html", {"entries": visible_entries()[:12]})


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


# ---------- Adding, editing and deleting entries ----------


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
    Saves an entry from a valid EntryForm. I use it for adding and for
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
    return render(request, "archive/entry_form.html", {"form": form, "craft_type": craft_type})


@login_required
def edit_entry(request, pk):
    """FR-3.8: only the owner can edit an entry."""
    entry = get_object_or_404(CraftEntry, pk=pk)
    if entry.owner != request.user:
        return HttpResponseForbidden("You can only edit your own entries.")

    if request.method == "POST":
        form = EntryForm(request.POST, request.FILES, craft_type=entry.craft_type, entry=entry)
        if form.is_valid():
            save_entry(form, entry, request.user)
            messages.success(request, "Your changes are saved.")
            return redirect(entry)
        messages.error(request, "Please fix the fields marked in red.")
    else:
        form = EntryForm(craft_type=entry.craft_type, entry=entry)
    return render(
        request, "archive/entry_form.html", {"form": form, "craft_type": entry.craft_type, "entry": entry}
    )


@login_required
def delete_entry(request, pk):
    """FR-3.8: only the owner can delete. I ask once more before deleting."""
    entry = get_object_or_404(CraftEntry, pk=pk)
    if entry.owner != request.user:
        return HttpResponseForbidden("You can only delete your own entries.")
    if request.method == "POST":
        entry.delete()
        messages.success(request, "The entry is deleted.")
        return redirect("profile", username=request.user.username)
    return render(request, "archive/entry_confirm_delete.html", {"entry": entry})


def entry_detail(request, pk):
    """US-04: everyone can see an entry, with a caption under the photo."""
    entry = get_object_or_404(
        CraftEntry.objects.select_related("craft_type__category__parent", "owner"), pk=pk
    )
    # UC-05 alternative flow: a hidden entry is "not available", except for the admin.
    if entry.is_hidden and not request.user.is_staff:
        return render(request, "archive/not_available.html", status=404)
    return render(request, "archive/entry_detail.html", {"entry": entry})


# ---------- Defining a new craft type ----------


@login_required
def define_craft_type(request):
    """US-05: a user defines a new craft type with its fields and units."""
    if request.method == "POST":
        form = CraftTypeForm(request.POST)
        formset = AttributeFormSet(request.POST, prefix="fields")
        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                craft_type = form.save(commit=False)
                craft_type.created_by = request.user
                craft_type.save()
                formset.instance = craft_type
                definitions = formset.save(commit=False)
                for order, definition in enumerate(definitions):
                    definition.order = order
                    definition.save()
            messages.success(request, f'"{craft_type.name}" is ready. Now you can add an entry of this type.')
            return redirect("add_entry", type_id=craft_type.id)
        messages.error(request, "Please fix the fields marked in red.")
    else:
        form = CraftTypeForm()
        formset = AttributeFormSet(prefix="fields")
    return render(request, "archive/craft_type_form.html", {"form": form, "formset": formset})


def similar_craft_types(request):
    """
    A small JSON answer for the craft type form. While the user types the
    name, the page asks this URL for similar existing names.
    """
    name = request.GET.get("name", "")
    names = CraftType.objects.values_list("name", flat=True)
    return JsonResponse({"similar": similar_names(name, names)})


def tag_suggestions(request):
    """
    US-06: tags that start with what the user typed, with how many entries
    use them, for example: kayseri (42 entries).
    """
    text = request.GET.get("q", "").strip().lower()
    if len(text) < 2:
        return JsonResponse({"tags": []})
    tags = (
        Tag.objects.filter(name__istartswith=text)
        .annotate(count=Count("entries"))
        .order_by("-count", "name")[:8]
    )
    return JsonResponse({"tags": [{"name": t.name, "count": t.count} for t in tags]})


# ---------- Browsing, search and the map ----------


def browse(request):
    """US-07: Domain > Family > Craft Type, each type with its number of entries."""
    domains = Category.objects.filter(parent=None).prefetch_related("children")
    counted_types = CraftType.objects.annotate(
        entry_count=Count("entries", filter=Q(entries__is_hidden=False))
    )
    # I group the counted types by their family so the template stays simple.
    types_by_family = {}
    for craft_type in counted_types:
        types_by_family.setdefault(craft_type.category_id, []).append(craft_type)
    tree = []
    for domain in domains:
        families = [(family, types_by_family.get(family.id, [])) for family in domain.children.all()]
        tree.append((domain, families))
    return render(request, "archive/browse.html", {"tree": tree})


def entry_list(request):
    """US-08: keyword search plus filters. Filters can be combined."""
    form = FilterForm(request.GET or None)
    entries = visible_entries()

    if form.is_valid():
        data = form.cleaned_data
        if data["q"]:
            q = data["q"]
            entries = entries.filter(
                Q(title__icontains=q) | Q(craft_type__name__icontains=q) | Q(tags__name__icontains=q)
            )
        if data["craft_type"]:
            entries = entries.filter(craft_type=data["craft_type"])
        if data["color"]:
            entries = entries.filter(colors=data["color"])
        if data["tag"]:
            entries = entries.filter(tags__name=data["tag"])

        # One filter call per field. Each filter() looks at its own value row.
        for definition, kind in form.attribute_filters:
            if kind == "measurement":
                unit = data.get(f"unit_{definition.id}") or definition.unit
                low = data.get(f"min_{definition.id}")
                high = data.get(f"max_{definition.id}")
                # 1 m and 100 cm are the same, because I compare base units.
                if low is not None:
                    entries = entries.filter(
                        values__definition=definition, values__number__gte=to_base(low, unit)
                    )
                if high is not None:
                    entries = entries.filter(
                        values__definition=definition, values__number__lte=to_base(high, unit)
                    )
            else:
                chosen = data.get(f"val_{definition.id}")
                if chosen:
                    if definition.data_type == AttributeDefinition.MULTIPLE:
                        # Multiple choice values are saved like "|red|indigo|".
                        entries = entries.filter(
                            values__definition=definition, values__text__contains=f"|{chosen}|"
                        )
                    else:
                        entries = entries.filter(values__definition=definition, values__text=chosen)

    # distinct(): the joins above can return the same entry twice.
    entries = entries.distinct()
    page = Paginator(entries, 12).get_page(request.GET.get("page"))

    # The other GET values without "page", for the next and previous links.
    query = request.GET.copy()
    query.pop("page", None)
    return render(
        request,
        "archive/entry_list.html",
        {"form": form, "page": page, "query": query.urlencode()},
    )


def map_view(request):
    """FR-5.2: all entries as pins on one map."""
    points = [
        {
            "title": e.title,
            "type": e.craft_type.name,
            "lat": e.latitude,
            "lng": e.longitude,
            "url": e.get_absolute_url(),
        }
        for e in visible_entries()
    ]
    return render(request, "archive/map.html", {"points": points})


def profile(request, username):
    """FR-1.3: the entries and craft types of one user."""
    person = get_object_or_404(User, username=username)
    entries = visible_entries().filter(owner=person)
    if request.user == person:
        # On my own profile I also see my hidden entries.
        entries = CraftEntry.objects.filter(owner=person)
    return render(
        request,
        "archive/profile.html",
        {"person": person, "entries": entries, "craft_types": CraftType.objects.filter(created_by=person)},
    )


# ---------- JSON export (NFR-8) ----------


def entry_json(request, pk):
    entry = get_object_or_404(visible_entries(), pk=pk)
    return JsonResponse(entry.to_dict(), json_dumps_params={"ensure_ascii": False, "indent": 2})


def export_json(request):
    data = [e.to_dict() for e in visible_entries().prefetch_related("values__definition", "colors", "tags")]
    return JsonResponse(data, safe=False, json_dumps_params={"ensure_ascii": False, "indent": 2})


# ---------- Reports (only the admin sees them) ----------

REPORTABLE = {
    # kind in the URL -> (model, field name on Report)
    "entry": (CraftEntry, "entry"),
    "type": (CraftType, "craft_type"),
    "tag": (Tag, "tag"),
}


@login_required
def report_content(request, kind, pk):
    """
    US-09: a logged in user reports wrong or meaningless data.
    The report goes only to the admin and does not change anything by itself.
    """
    if kind not in REPORTABLE:
        raise Http404
    model, field = REPORTABLE[kind]
    target = get_object_or_404(model, pk=pk)

    # After reporting I send the user back to the page of the reported thing.
    if kind == "entry":
        back = target.get_absolute_url()
    elif kind == "type":
        back = f"/entries/?craft_type={target.pk}"
    else:
        back = "/entries/?tag=" + quote(target.name)

    # UC-09 alternative flow: the same user cannot report the same thing twice.
    already = Report.objects.filter(reporter=request.user, **{field: target}, status=Report.OPEN)
    if already.exists():
        messages.info(request, "You already reported this. The admin will look at it.")
        return redirect(back)

    if request.method == "POST":
        form = ReportForm(request.POST)
        if form.is_valid():
            Report.objects.create(reporter=request.user, reason=form.cleaned_data["reason"], **{field: target})
            messages.success(request, "Thank you. Your report was sent to the admin.")
            return redirect(back)
    else:
        form = ReportForm()
    return render(request, "archive/report_form.html", {"form": form, "target": target, "kind": kind})


@staff_member_required
def report_queue(request):
    """US-10: the admin sees the open reports, oldest first."""
    reports = Report.objects.filter(status=Report.OPEN).select_related(
        "reporter", "entry", "craft_type", "tag"
    )
    return render(request, "archive/report_queue.html", {"reports": reports})


@staff_member_required
@require_POST
def resolve_report(request, pk):
    """
    The admin decides what to do. UC-10 alternative flow: all open reports
    about the same thing are resolved together.
    """
    report = get_object_or_404(Report, pk=pk)
    action = request.POST.get("action")
    same_target = Report.objects.filter(
        status=Report.OPEN, entry=report.entry, craft_type=report.craft_type, tag=report.tag
    )

    if action == "hide" and report.entry:
        report.entry.is_hidden = True
        report.entry.save()
    elif action == "delete" and report.entry:
        # Deleting the entry also deletes its reports (on_delete=CASCADE).
        report.entry.delete()
        messages.success(request, "The entry is deleted.")
        return redirect("report_queue")
    elif action == "delete" and report.tag:
        report.tag.delete()
        messages.success(request, "The tag is deleted.")
        return redirect("report_queue")
    elif action != "dismiss":
        messages.error(request, "Unknown action.")
        return redirect("report_queue")

    same_target.update(status=Report.RESOLVED, admin_action=action)
    messages.success(request, "The report is resolved.")
    return redirect("report_queue")
