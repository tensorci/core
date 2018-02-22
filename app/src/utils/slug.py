from slugify import Slugify

to_slug = Slugify(to_lower=True, separator='-', safe_chars='_')