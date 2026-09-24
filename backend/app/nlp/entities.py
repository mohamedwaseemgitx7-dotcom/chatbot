"""
Crop detection in English, Tamil and Tanglish (including common spelling variants).
"""
import re
from typing import Optional

from app.nlp.normalizer import clean_text

# crop → names a farmer might type. Order matters only for readability; longest match wins.
CROP_NAMES = {
    "paddy": ["paddy", "rice", "nel", "nellu", "nelu", "nella", "nellu", "arisi", "நெல்", "நெல்லு", "அரிசி"],
    "tomato": ["tomato", "tomatoes", "thakkali", "thakali", "takkali", "தக்காளி"],
    "chilli": ["chilli", "chili", "chillies", "milagai", "milaga", "molagai", "molaga", "மிளகாய்"],
    "banana": ["banana", "vazhai", "vaazhai", "valai", "vaalai", "வாழை"],
    "coconut": ["coconut", "thennai", "thenai", "thengai", "தென்னை", "தேங்காய்"],
    "sugarcane": ["sugarcane", "sugar cane", "karumbu", "karumbu", "கரும்பு"],
    "groundnut": ["groundnut", "ground nut", "peanut", "kadalai", "nilakadalai", "verkadalai", "நிலக்கடலை", "வேர்க்கடலை", "கடலை"],
    "cotton": ["cotton", "paruthi", "parutthi", "பருத்தி"],
    "maize": ["maize", "corn", "makkacholam", "makka cholam", "cholam", "மக்காச்சோளம்"],
    "brinjal": ["brinjal", "eggplant", "kathari", "kathirikai", "kathrikai", "katharikai", "கத்தரி", "கத்திரிக்காய்"],
    "onion": ["onion", "vengayam", "vengaayam", "வெங்காயம்"],
    "drumstick": ["drumstick", "moringa", "murungai", "murunga", "முருங்கை"],
    "turmeric": ["turmeric", "மஞ்சள் கிழங்கு"],
    "blackgram": ["blackgram", "black gram", "urad", "urd", "ulundhu", "ulundu", "உளுந்து"],
    "greengram": ["greengram", "green gram", "moong", "mung", "pasipayaru", "paasi payaru", "pachai payaru", "பாசிப்பயறு", "பச்சைப்பயறு"],
}

_PATTERNS = sorted(((name, crop) for crop, names in CROP_NAMES.items() for name in names), key=lambda p: -len(p[0]))


def detect_crop(text: str, english: str = "") -> Optional[str]:
    haystack = f" {clean_text(text)} {clean_text(english)} "
    for name, crop in _PATTERNS:
        if any("஀" <= ch <= "௿" for ch in name):
            if name in haystack:  # Tamil words carry case endings: prefix match is enough
                return crop
        elif re.search(rf"(?<![a-z]){re.escape(name)}(?:la|ku|kku|le|ukku|oda|s)?(?![a-z])", haystack):
            return crop
    return None
