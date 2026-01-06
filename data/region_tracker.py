from data.config_settings import get_region

_url = None

def setup_region():
    global _url
    region = get_region().lower()

    urls = {
        "us": "https://www.missionchief.com/",
        "uk": "https://www.missionchief.co.uk/",
        "aus": "https://www.missionchief-australia.com/",
        "ger": "https://www.leitstellenspiel.de/",
        "nld": "https://www.meldkamerspel.com/",
    }

    try:
        _url = urls[region]
    except KeyError:
        raise ValueError(f"Unknown region: {region}")

def get_url():
    if _url is None:
        raise RuntimeError("URL not set. Call setup_region() first.")
    return _url
