"""
My tests. I run them with:  python manage.py test

They check the main things of the prototype: units, sign up, adding a
kilim entry and the detail page.
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

from .models import Color, CraftEntry, CraftType
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
