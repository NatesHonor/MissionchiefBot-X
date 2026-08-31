import re


def format_distance(seconds):
    if seconds == float("inf"):
        return "unknown"
    if seconds < 60:
        return f"{seconds} sec"
    if seconds < 3600:
        mins = seconds // 60
        secs = seconds % 60
        return f"{mins} min {secs} sec"
    hrs = seconds // 3600
    mins = (seconds % 3600) // 60
    return f"{hrs} hr {mins} min"


def normalize_key(value):
    return re.sub(r"\s+", " ", value.strip().casefold())


def canonical_personnel(value):
    value = re.sub(r"\([^)]*\)", "", value).casefold()
    value = re.sub(r"[^a-z0-9\s]", " ", value)
    value = re.sub(r"\s+", " ", value).strip()
    return {
        "swat personnel": "swat personnel",
        "swat": "swat personnel",
        "s w a t personnel": "swat personnel",
    }.get(value, value)
