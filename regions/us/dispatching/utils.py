import re

def format_distance(seconds):
    if seconds == float('inf'):
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

def normalize_key(s):
    return re.sub(r'\s+', ' ', s.strip().casefold())

def canonical_personnel(s):
    s = re.sub(r'\([^)]*\)', '', s)
    s = s.casefold()
    s = re.sub(r'[^a-z0-9\s]', ' ', s)
    s = re.sub(r'\s+', ' ', s).strip()
    synonyms = {
        'swat personnel': 'swat personnel',
        'swat': 'swat personnel',
        's w a t personnel': 'swat personnel'
    }
    return synonyms.get(s, s)
