"""
Finding names that are almost the same (FR-2.5 and FR-4.3).

If someone types "Kilm" while "Kilim" already exists, I want to ask
"Did you mean Kilim?" instead of creating a second, broken craft type.
"""

# Turkish letters are changed to plain ones, so "çini" and "cini" match.
TURKISH = str.maketrans("çğıöşüÇĞİÖŞÜ", "cgiosuCGIOSU")


def normalize(text):
    return text.translate(TURKISH).lower().strip()


def edit_distance(a, b):
    """
    How many single letter changes (add, remove or replace) turn a into b.
    This is the classic Levenshtein distance. I fill the table one row at a
    time so I only keep two rows in memory.
    """
    previous = list(range(len(b) + 1))
    for i, letter_a in enumerate(a, start=1):
        current = [i]
        for j, letter_b in enumerate(b, start=1):
            cost = 0 if letter_a == letter_b else 1
            current.append(
                min(
                    previous[j] + 1,  # remove a letter
                    current[j - 1] + 1,  # add a letter
                    previous[j - 1] + cost,  # replace a letter
                )
            )
        previous = current
    return previous[-1]


def similar_names(name, existing_names, max_distance=2):
    """
    Returns the existing names that differ from "name" by at most 2 letters,
    ignoring capital letters and Turkish characters. The exact same name is
    not returned, because that is a duplicate, not a "similar" name.
    """
    target = normalize(name)
    found = []
    for existing in existing_names:
        other = normalize(existing)
        if other == target:
            continue
        # Very short names would match almost everything, so I skip them.
        if min(len(other), len(target)) < 3:
            continue
        if edit_distance(target, other) <= max_distance:
            found.append(existing)
    return found


def same_name_exists(name, existing_names):
    target = normalize(name)
    return any(normalize(existing) == target for existing in existing_names)
