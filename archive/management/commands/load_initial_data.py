"""
python manage.py load_initial_data

Fills an empty database with my starting data: the category tree, the
color palette, some predefined tags and four predefined craft types.
I can run it many times, it does not create duplicates (get_or_create).
"""

from django.core.management.base import BaseCommand

from archive.models import AttributeDefinition as A
from archive.models import Category, Color, CraftType, Tag

# Level 1 (domain) -> list of level 2 (families)
CATEGORY_TREE = {
    "Textile Arts": ["Flat-woven Rugs", "Pile Rugs", "Embroidery"],
    "Ceramics and Tiles": ["Tiles", "Pottery"],
    "Paper Arts": ["Marbling", "Bookbinding"],
    "Painting and Calligraphy": ["Miniature", "Calligraphy"],
    "Wood and Metal Crafts": ["Woodwork", "Copperwork"],
}

COLORS = [
    ("red", "#b22222"),
    ("dark red", "#7b1e1e"),
    ("indigo", "#2c3e8f"),
    ("blue", "#1f6fb2"),
    ("turquoise", "#2aa5a0"),
    ("green", "#3c7a3b"),
    ("yellow", "#e1b12c"),
    ("orange", "#d9822b"),
    ("brown", "#7a4b2a"),
    ("cream", "#f3e9d2"),
    ("white", "#ffffff"),
    ("black", "#222222"),
    ("gold", "#c9a227"),
]

TAGS = ["dowry", "village", "workshop", "handmade", "natural dye", "anatolia", "family", "old"]

KILIM_PATTERNS = [
    "elibelinde",
    "koçboynuzu (ram's horn)",
    "bereket",
    "göz (eye)",
    "muska (amulet)",
    "bukağı (hobble)",
    "sandık (dowry chest)",
    "kurt ağzı (wolf's mouth)",
    "su yolu (waterway)",
    "hayat ağacı (tree of life)",
]

# Every craft type: (family, description, list of fields)
# A field is (name, data type, unit, allowed values, required, show in caption)
CRAFT_TYPES = {
    "Kilim": (
        "Flat-woven Rugs",
        "A flat-woven rug without pile, woven on a loom by interlocking the weft threads.",
        [
            ("Width", A.MEASUREMENT, "cm", [], True, True),
            ("Length", A.MEASUREMENT, "cm", [], True, True),
            ("Weight", A.MEASUREMENT, "kg", [], False, False),
            ("Weaving technique", A.MULTIPLE, "",
             ["slit tapestry", "dovetailing", "double interlocking", "cicim", "zili", "sumak"], True, False),
            ("Warp material", A.SINGLE, "", ["wool", "goat hair", "cotton"], True, True),
            ("Weft material", A.MULTIPLE, "", ["wool", "goat hair", "cotton", "silk"], True, False),
            ("Dye type", A.SINGLE, "", ["natural", "synthetic", "mixed", "unknown"], True, False),
            ("Natural dye sources", A.MULTIPLE, "",
             ["madder root (red)", "indigo (blue)", "walnut husk (brown)", "vine leaf (yellow)", "chamomile (yellow)"],
             False, False),
            ("Patterns", A.MULTIPLE, "", KILIM_PATTERNS, False, False),
            ("Use", A.SINGLE, "", ["floor rug", "prayer rug", "wall hanging", "cushion", "bag", "cover"], False, False),
            ("Culture or community", A.SINGLE, "", ["Yoruk", "Turkmen", "Kurdish", "village workshop", "unknown"], False, False),
            ("Production period", A.PERIOD, "", [], False, False),
            ("Maker", A.SHORT_TEXT, "", [], False, False),
            ("Condition", A.SINGLE, "", ["new", "good", "worn", "restored"], False, False),
        ],
    ),
    "Ebru": (
        "Marbling",
        "Paper marbling: colors floating on thickened water are moved into patterns and taken onto paper.",
        [
            ("Width", A.MEASUREMENT, "cm", [], True, True),
            ("Length", A.MEASUREMENT, "cm", [], True, True),
            ("Ebru style", A.SINGLE, "", ["battal", "gelgit", "taraklı", "şal", "hatip", "çiçekli"], True, True),
            ("Paper type", A.SINGLE, "", ["handmade paper", "factory paper", "fabric"], False, False),
            ("Production period", A.PERIOD, "", [], False, False),
            ("Maker", A.SHORT_TEXT, "", [], False, False),
        ],
    ),
    "Çini": (
        "Tiles",
        "Glazed tiles and ceramics with hand painted patterns, known from İznik and Kütahya.",
        [
            ("Width", A.MEASUREMENT, "cm", [], True, True),
            ("Length", A.MEASUREMENT, "cm", [], True, True),
            ("Production center", A.SINGLE, "", ["İznik", "Kütahya", "Çanakkale", "other"], True, True),
            ("Motifs", A.MULTIPLE, "", ["tulip", "carnation", "hyacinth", "rumi", "hatayi", "saz leaf"], False, False),
            ("Glaze", A.SINGLE, "", ["underglaze", "overglaze", "unknown"], False, False),
            ("Production period", A.PERIOD, "", [], False, False),
        ],
    ),
    "Miniature": (
        "Miniature",
        "Small, detailed paintings, usually made for books and albums.",
        [
            ("Width", A.MEASUREMENT, "cm", [], True, True),
            ("Length", A.MEASUREMENT, "cm", [], True, True),
            ("Paint", A.MULTIPLE, "", ["gouache", "watercolor", "gold leaf", "ink"], False, True),
            ("Subject", A.SINGLE, "", ["portrait", "city view", "story scene", "nature"], False, False),
            ("Production period", A.PERIOD, "", [], False, False),
            ("Artist", A.SHORT_TEXT, "", [], False, False),
        ],
    ),
}


class Command(BaseCommand):
    help = "Loads the category tree, colors, tags and predefined craft types."

    def handle(self, *args, **options):
        families = {}
        for domain_name, family_names in CATEGORY_TREE.items():
            domain, _ = Category.objects.get_or_create(name=domain_name, parent=None)
            for family_name in family_names:
                family, _ = Category.objects.get_or_create(name=family_name, parent=domain)
                families[family_name] = family

        for name, hex_code in COLORS:
            Color.objects.get_or_create(name=name, defaults={"hex_code": hex_code})

        for name in TAGS:
            Tag.objects.get_or_create(name=name, defaults={"is_predefined": True})

        for type_name, (family_name, description, fields) in CRAFT_TYPES.items():
            craft_type, _ = CraftType.objects.get_or_create(
                name=type_name,
                defaults={
                    "category": families[family_name],
                    "description": description,
                    "is_predefined": True,
                },
            )
            for order, (name, data_type, unit, values, required, caption) in enumerate(fields):
                A.objects.update_or_create(
                    craft_type=craft_type,
                    name=name,
                    defaults={
                        "data_type": data_type,
                        "unit": unit,
                        "allowed_values": "\n".join(values),
                        "required": required,
                        "show_in_caption": caption,
                        "order": order,
                    },
                )

        self.stdout.write(self.style.SUCCESS("Initial data is loaded."))
