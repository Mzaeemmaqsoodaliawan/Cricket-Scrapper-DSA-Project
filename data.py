
import csv
import os

COLUMNS = [
    ("Match ID", "str"),
    ("Date", "str"),            
    ("Match Type", "str"),
    ("Gender", "str"),
    ("Event", "str"),
    ("Venue", "str"),
    ("City", "str"),
    ("Team 1", "str"),
    ("Team 2", "str"),
    ("Toss Winner", "str"),
    ("Toss Decision", "str"),
    ("Winner", "str"),
    ("Margin", "int"),
    ("Margin Type", "str"),
    ("Player of Match", "str"),
    ("Season", "str"),
    ("Overs", "int"),
]
HEADERS = [c[0] for c in COLUMNS]
TYPES = [c[1] for c in COLUMNS]
CSV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cricket_matches.csv")


def convert(value, ctype):
    """Convert a raw value to the column type (bad values become 0 / 0.0 / '')."""
    if ctype == "str":
        return str(value).strip()
    try:
        return int(float(value)) if ctype == "int" else float(value)
    except (ValueError, TypeError):
        return 0 if ctype == "int" else 0.0


class DataStore:
    """Holds all rows in memory and keeps cricket_matches.csv in sync."""

    def __init__(self, path=None):
        self.path = path or CSV_PATH
        self.rows = []
        self.load()

    def load(self):
        self.rows = []
        if not os.path.exists(self.path):
            return
        with open(self.path, newline="", encoding="utf-8") as f:
            reader = csv.reader(f)
            next(reader, None)  # header
            for rec in reader:
                if len(rec) == len(COLUMNS):
                    self.rows.append([convert(v, t) for v, t in zip(rec, TYPES)])

    def save(self):
        """Rewrite the whole file (used after add / edit / delete)."""
        tmp = self.path + ".tmp"
        with open(tmp, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(HEADERS)
            w.writerows(self.rows)
        os.replace(tmp, self.path)

    def append(self, new_rows):
        """Append scraped rows to memory and to the CSV (cheap, used while scraping)."""
        has_header = os.path.exists(self.path) and os.path.getsize(self.path) > 0
        with open(self.path, "a", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            if not has_header:
                w.writerow(HEADERS)
            w.writerows(new_rows)
        self.rows.extend(new_rows)

    def keys(self):
        return {r[0] for r in self.rows}