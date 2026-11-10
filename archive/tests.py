"""
My tests. I run them with:  python manage.py test

They check the main things of the prototype (units, sign up, adding a
kilim entry, the detail page) and of the MVP (similar names, craft types,
search, editing, reports and the JSON export).
"""

import io
import shutil
import tempfile

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from .models import Color, CraftEntry, CraftType, Report, Tag
from .similar import similar_names
from .units import from_base, to_base

# Uploaded test photos go into a temporary folder that I delete at the end.
TEST_MEDIA = tempfile.mkdtemp()


def make_test_image(name="kilim.png"):
    # A tiny red PNG made in memory, so I do not need a real photo file.
    buffer = io.BytesIO()
    Image.new("RGB", (20, 20), "red").save(buffer, format="PNG")
    return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/png")


class UnitTests(TestCase):
    def test_length_is_saved_in_cm(self):
        self.assertEqual(to_base(1.2, "m"), 120)
        self.assertEqual(to_base(120, "cm"), 120)
        self.assertEqual(to_base(50, "mm"), 5)

    def test_weight_is_saved_in_grams(self):
        self.assertEqual(to_base(2, "kg"), 2000)

    def test_back_from_base_unit(self):
        self.assertEqual(from_base(120, "m"), 1.2)


class SignUpTests(TestCase):
    def test_sign_up_logs_the_user_in(self):
        response = self.client.post(
            reverse("signup"),
            {
                "username": "berker",
                "email": "berker@example.com",
                "password1": "a-long-password-123",
                "password2": "a-long-password-123",
            },
        )
        self.assertRedirects(response, reverse("home"))
        self.assertTrue(User.objects.filter(username="berker").exists())
        # The password must not be saved as plain text (NFR-3).
        self.assertNotEqual(User.objects.get(username="berker").password, "a-long-password-123")

    def test_used_username_shows_an_error(self):
        User.objects.create_user("berker", "first@example.com", "pass12345!")
        response = self.client.post(
            reverse("signup"),
            {
                "username": "berker",
                "email": "other@example.com",
                "password1": "a-long-password-123",
                "password2": "a-long-password-123",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(User.objects.count(), 1)


@override_settings(MEDIA_ROOT=TEST_MEDIA)
class KilimEntryTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        # The same starting data as on the real site.
        call_command("load_initial_data", verbosity=0)
        cls.kilim = CraftType.objects.get(name="Kilim")
        cls.user = User.objects.create_user("berker", "b@example.com", "pass12345!")

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEST_MEDIA, ignore_errors=True)

    def field(self, name):
        # Form field name of a kilim attribute, for example "attr_3".
        return "attr_%d" % self.kilim.attributes.get(name=name).id

    def kilim_data(self):
        data = {
            "title": "Grandmother's kilim from Kayseri",
            "latitude": "38.72",
            "longitude": "35.48",
            "place_name": "Kayseri",
            "tags": "kayseri, dowry",
            "personal_story": "My grandmother wove this for her dowry.",
            self.field("Width"): "1.2",
            self.field("Width") + "_unit": "m",
            self.field("Length"): "180",
            self.field("Length") + "_unit": "cm",
            self.field("Weaving technique"): ["slit tapestry"],
            self.field("Warp material"): "wool",
            self.field("Weft material"): ["wool"],
            self.field("Dye type"): "natural",
            self.field("Patterns"): ["elibelinde", "su yolu (waterway)"],
            "colors": [Color.objects.get(name="red").id, Color.objects.get(name="indigo").id],
            "images": make_test_image(),
        }
        return data

    def test_add_entry_needs_login(self):
        response = self.client.get(reverse("add_entry", args=[self.kilim.id]))
        self.assertEqual(response.status_code, 302)

    def test_form_shows_only_kilim_fields(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("add_entry", args=[self.kilim.id]))
        self.assertContains(response, "Weaving technique")
        # A field of another craft type (Ebru) must not be on the kilim form.
        self.assertNotContains(response, "Ebru style")

    def test_add_kilim_entry(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse("add_entry", args=[self.kilim.id]), self.kilim_data())
        entry = CraftEntry.objects.get()
        self.assertRedirects(response, entry.get_absolute_url())

        # 1.2 m must be saved as 120 cm.
        width = entry.values.get(definition__name="Width")
        self.assertEqual(width.number, 120)
        self.assertEqual(entry.colors.count(), 2)
        self.assertEqual(entry.tags.count(), 2)
        self.assertEqual(entry.images.count(), 1)

    def test_missing_required_field_is_not_saved(self):
        self.client.force_login(self.user)
        data = self.kilim_data()
        del data[self.field("Width")]
        response = self.client.post(reverse("add_entry", args=[self.kilim.id]), data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(CraftEntry.objects.count(), 0)

    def test_missing_pin_is_not_saved(self):
        self.client.force_login(self.user)
        data = self.kilim_data()
        del data["latitude"]
        response = self.client.post(reverse("add_entry", args=[self.kilim.id]), data)
        self.assertContains(response, "Please drop a pin on the map.")

    def test_detail_page_shows_caption(self):
        self.client.force_login(self.user)
        self.client.post(reverse("add_entry", args=[self.kilim.id]), self.kilim_data())
        self.client.logout()

        # A visitor (not logged in) can see the entry.
        entry = CraftEntry.objects.get()
        response = self.client.get(entry.get_absolute_url())
        self.assertContains(response, "120 x 180 cm")
        self.assertContains(response, "Kayseri")
        self.assertContains(response, "My grandmother wove this")



class SimilarNameTests(TestCase):
    def test_typo_is_found(self):
        self.assertEqual(similar_names("Kilm", ["Kilim", "Ebru"]), ["Kilim"])

    def test_turkish_letters_and_case_are_ignored(self):
        self.assertEqual(similar_names("cinni", ["Çini"]), ["Çini"])

    def test_exact_same_name_is_not_similar(self):
        self.assertEqual(similar_names("Kilim", ["kilim"]), [])


@override_settings(MEDIA_ROOT=TEST_MEDIA)
class MvpTests(KilimEntryTests):
    """I reuse the kilim test data from KilimEntryTests."""

    def add_kilim(self, user=None, **changes):
        self.client.force_login(user or self.user)
        data = self.kilim_data()
        data.update(changes)
        self.client.post(reverse("add_entry", args=[self.kilim.id]), data)
        return CraftEntry.objects.latest("id")

    def test_define_craft_type_suggests_similar_name(self):
        self.client.force_login(self.user)
        data = {
            "name": "Kilm",
            "category": self.kilim.category.id,
            "description": "",
            "fields-TOTAL_FORMS": "1",
            "fields-INITIAL_FORMS": "0",
            "fields-MIN_NUM_FORMS": "1",
            "fields-MAX_NUM_FORMS": "1000",
            "fields-0-name": "Width",
            "fields-0-data_type": "measurement",
            "fields-0-unit": "cm",
        }
        response = self.client.post(reverse("define_craft_type"), data)
        self.assertContains(response, "Similar types already exist: Kilim")
        self.assertFalse(CraftType.objects.filter(name="Kilm").exists())

        # With the box ticked, the new type is saved.
        data["confirm_new_name"] = "on"
        self.client.post(reverse("define_craft_type"), data)
        self.assertTrue(CraftType.objects.filter(name="Kilm").exists())

    def test_measurement_field_needs_a_unit(self):
        self.client.force_login(self.user)
        data = {
            "name": "Felt",
            "category": self.kilim.category.id,
            "fields-TOTAL_FORMS": "1",
            "fields-INITIAL_FORMS": "0",
            "fields-MIN_NUM_FORMS": "1",
            "fields-MAX_NUM_FORMS": "1000",
            "fields-0-name": "Width",
            "fields-0-data_type": "measurement",
            "fields-0-unit": "",
        }
        response = self.client.post(reverse("define_craft_type"), data)
        self.assertContains(response, "A measurement needs a unit.")

    def test_tag_typo_asks_did_you_mean(self):
        Tag.objects.create(name="kayseri")
        self.client.force_login(self.user)
        data = self.kilim_data()
        data["tags"] = "kaysery"
        response = self.client.post(reverse("add_entry", args=[self.kilim.id]), data)
        self.assertContains(response, "did you mean")
        self.assertEqual(CraftEntry.objects.count(), 0)

    def test_tag_suggestions(self):
        self.add_kilim()
        response = self.client.get(reverse("tag_suggestions"), {"q": "kay"})
        self.assertEqual(response.json()["tags"][0]["name"], "kayseri")

    def test_filter_by_length_works_across_units(self):
        self.add_kilim()  # 180 cm long
        kilim_id = str(self.kilim.id)
        length_id = self.kilim.attributes.get(name="Length").id
        found = self.client.get(
            reverse("entry_list"), {"craft_type": kilim_id, f"min_{length_id}": "1.5", f"unit_{length_id}": "m"}
        )
        self.assertEqual(found.context["page"].paginator.count, 1)
        not_found = self.client.get(
            reverse("entry_list"), {"craft_type": kilim_id, f"min_{length_id}": "2", f"unit_{length_id}": "m"}
        )
        self.assertEqual(not_found.context["page"].paginator.count, 0)

    def test_filter_by_pattern(self):
        self.add_kilim()
        pattern_id = self.kilim.attributes.get(name="Patterns").id
        response = self.client.get(
            reverse("entry_list"), {"craft_type": self.kilim.id, f"val_{pattern_id}": "elibelinde"}
        )
        self.assertEqual(response.context["page"].paginator.count, 1)

    def test_only_owner_can_edit_and_delete(self):
        entry = self.add_kilim()
        other = User.objects.create_user("ayse", "a@example.com", "pass12345!")
        self.client.force_login(other)
        self.assertEqual(self.client.get(reverse("edit_entry", args=[entry.id])).status_code, 403)
        self.assertEqual(self.client.post(reverse("delete_entry", args=[entry.id])).status_code, 403)

        self.client.force_login(self.user)
        self.client.post(reverse("delete_entry", args=[entry.id]))
        self.assertEqual(CraftEntry.objects.count(), 0)

    def test_report_goes_only_to_admin_and_changes_nothing(self):
        entry = self.add_kilim()
        other = User.objects.create_user("ayse", "a@example.com", "pass12345!")
        self.client.force_login(other)
        self.client.post(reverse("report_content", args=["entry", entry.id]), {"reason": "wrong_value"})

        report = Report.objects.get()
        self.assertEqual(report.status, Report.OPEN)
        entry.refresh_from_db()
        self.assertFalse(entry.is_hidden)

        # A normal user cannot open the report queue.
        self.assertEqual(self.client.get(reverse("report_queue")).status_code, 302)

        # The admin hides the entry, and the report is resolved.
        admin = User.objects.create_user("admin", "admin@example.com", "pass12345!", is_staff=True)
        self.client.force_login(admin)
        self.client.post(reverse("resolve_report", args=[report.id]), {"action": "hide"})
        entry.refresh_from_db()
        self.assertTrue(entry.is_hidden)
        self.assertEqual(Report.objects.get().status, Report.RESOLVED)

        # Now a visitor sees "not available".
        self.client.logout()
        self.assertEqual(self.client.get(entry.get_absolute_url()).status_code, 404)

    def test_same_user_cannot_report_twice(self):
        entry = self.add_kilim()
        other = User.objects.create_user("ayse", "a@example.com", "pass12345!")
        self.client.force_login(other)
        url = reverse("report_content", args=["entry", entry.id])
        self.client.post(url, {"reason": "wrong_value"})
        self.client.post(url, {"reason": "meaningless"})
        self.assertEqual(Report.objects.count(), 1)

    def test_json_export(self):
        entry = self.add_kilim()
        data = self.client.get(reverse("entry_json", args=[entry.id])).json()
        self.assertEqual(data["attributes"]["Width"], {"value": 120, "unit": "cm"})
        self.assertIn("elibelinde", data["attributes"]["Patterns"])

    def test_browse_shows_entry_count(self):
        self.add_kilim()
        response = self.client.get(reverse("browse"))
        self.assertContains(response, "Kilim")
        self.assertContains(response, '<span class="badge text-bg-light">1</span>', html=True)
