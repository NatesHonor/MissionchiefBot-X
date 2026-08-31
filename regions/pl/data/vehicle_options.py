"""Vehicle alternatives for the Polish Operator Ratunkowy deployment."""

from core.vehicle_mapping import get_vehicle_options_from_map


VEHICLE_OPTIONS = {
    "firetruck": ["Samochód gaśniczy", "Samochody gaśnicze", "GBA", "GCBA", "GBA-Rt", "GCBA-Rt", "Samochód ratowniczo-gaśniczy"],
    "firetrucks": ["Samochód gaśniczy", "Samochody gaśnicze", "GBA", "GCBA", "GBA-Rt", "GCBA-Rt"],
    "platform truck": ["Drabina mechaniczna", "SD", "SCD", "Drabina"],
    "battalion chief unit": ["Samochód szefa brygady", "Samochód operacyjny", "Samochód dowódcy"],
    "heavy rescue vehicles": ["Samochód ratownictwa technicznego", "Ciężki samochód ratowniczo-gaśniczy", "SCRd"],
    "hazmat vehicles": ["Samochód ratownictwa chemicznego", "RChem", "SPGaz"],
    "mobile command vehicles": ["Samochód dowodzenia i łączności", "SDiŁ", "Ruchome stanowisko dowodzenia", "RSD"],
    "mobile air vehicles": ["Samolot gaśniczy", "Dromader", "Jednostka powietrzna"],
    "ambulance": ["Ambulans", "Ambulans T", "Karetka", "ZRM", "Zespół ratownictwa medycznego"],
    "ems chief": ["Ambulans lekarza", "Samochód lekarza", "Karetka specjalistyczna"],
    "ems mobile command unit": ["Ambulans dowodzenia", "Ruchome stanowisko dowodzenia"],
    "ems mobile command units": ["Ambulans dowodzenia", "Ruchome stanowisko dowodzenia"],
    "patrol car": ["Radiowóz", "Samochód terenowy", "Furgonetka policyjna", "Radiowóz WRD"],
    "police car": ["Radiowóz", "Samochód terenowy", "Furgonetka policyjna"],
    "police supervisor": ["Samochód dowódcy policji", "Radiowóz dowódcy"],
    "police helicopter": ["Śmigłowiec policyjny", "Helikopter policyjny"],
    "k-9 unit": ["Samochód przewodnika psa", "Pies służbowy"],
    "swat armoured vehicles": ["Pojazd OPP", "Furgonetka OPP", "Van OPP"],
    "wrecker": ["Samochód ratownictwa drogowego", "Pojazd pomocy drogowej"],
    "flatbed carrier": ["Samochód ratownictwa drogowego", "Pojazd pomocy drogowej"],
    "water tanker": ["Cysterna gaśnicza", "Cysterna z wodą", "GCBA"],
    "light boat": ["Łódź ratownicza", "Łódź"],
    "large rescue boat": ["Łódź ratownicza", "Łódź"],
    "prisoner transport van": ["Więźniarka", "Mała więźniarka", "Duża więźniarka", "Furgonetka policyjna", "Van OPP"],
    "police bus": ["Autobus policyjny"]
}


def get_vehicle_options(vehicle_type):
    return get_vehicle_options_from_map(VEHICLE_OPTIONS, vehicle_type)
