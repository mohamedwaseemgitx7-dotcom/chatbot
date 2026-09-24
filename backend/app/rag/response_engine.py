"""
Controlled response engine: fixed templates per language + excerpts of verified records.
Nothing here generates free text, so the bot cannot invent doses, treatments or scheme rules.
"""
from typing import Dict, List, Optional

TEMPLATES: Dict[str, Dict[str, str]] = {
    "out_of_domain": {
        "english": "Sorry, I can help only with agriculture and farming-related questions.",
        "tamil": "மன்னிக்கவும், விவசாயம் தொடர்பான கேள்விகளுக்கு மட்டுமே என்னால் உதவ முடியும்.",
        "tanglish": "Sorry, vivasayam sambandhamana kelvigalukku mattum thaan ennala help panna mudiyum.",
    },
    "greeting": {
        "english": "Hello! I'm FarmerAssist. Ask me about crop pests, diseases, fertilizer or irrigation. You can also send a photo of an affected leaf.",
        "tamil": "வணக்கம்! நான் FarmerAssist. பயிர் பூச்சி, நோய், உரம், பாசனம் பற்றி கேளுங்கள். பாதிக்கப்பட்ட இலையின் புகைப்படத்தையும் அனுப்பலாம்.",
        "tanglish": "Vanakkam! Naan FarmerAssist. Payir poochi, noi, uram, thanni paaichal pathi kelunga. Paadhikkapatta ilai photo kooda anuppalaam.",
    },
    "thanks": {
        "english": "You're welcome! Wishing you a good harvest.",
        "tamil": "மகிழ்ச்சி! நல்ல விளைச்சல் கிடைக்க வாழ்த்துகள்.",
        "tanglish": "Santhosham! Nalla vilaichal kidaikka vaazhthukkal.",
    },
    "clarify": {
        "english": "I'm not sure I understood. Please tell me the crop name and describe the problem (for example: \"paddy leaves are turning yellow\").",
        "tamil": "உங்கள் கேள்வி எனக்குச் சரியாகப் புரியவில்லை. பயிரின் பெயரையும் பிரச்சனையையும் சொல்லுங்கள் (உதாரணம்: \"நெல் இலை மஞ்சளாகிறது\").",
        "tanglish": "Unga kelvi enakku sariyaa puriyala. Payir peyar-um problem-um sollunga (udhaaranam: \"nel ilai manjala iruku\").",
    },
    "need_crop": {
        "english": "Which crop is this about? Please tell me the crop name so I can give the right information.",
        "tamil": "இது எந்தப் பயிருக்கான கேள்வி? சரியான தகவல் தர பயிரின் பெயரைச் சொல்லுங்கள்.",
        "tanglish": "Idhu endha payiruku? Sariyaana information thara payir peyar sollunga.",
    },
    "no_knowledge": {
        "english": "I don't have enough verified information to answer that safely. Please provide more details or consult your local agricultural officer.",
        "tamil": "இதற்குப் பாதுகாப்பாகப் பதில் சொல்லப் போதுமான சரிபார்க்கப்பட்ட தகவல் என்னிடம் இல்லை. மேலும் விவரங்களைச் சொல்லுங்கள் அல்லது உங்கள் பகுதி வேளாண் அலுவலரை அணுகவும்.",
        "tanglish": "Idhukku safe-aa badhil solla thevaiyaana verified information ennidam illa. Innum konjam details sollunga, illana unga area agriculture officer-a paarunga.",
    },
    "market_price": {
        "english": "I don't have live market prices. Please check your nearest regulated market or the official Agmarknet portal: https://agmarknet.gov.in",
        "tamil": "நேரடி சந்தை விலை என்னிடம் இல்லை. அருகிலுள்ள ஒழுங்குமுறை விற்பனைக் கூடத்தில் அல்லது அரசின் Agmarknet இணையதளத்தில் பார்க்கவும்: https://agmarknet.gov.in",
        "tanglish": "Live market price ennidam illa. Pakkathula irukka regulated market-la illa govt Agmarknet website-la paarunga: https://agmarknet.gov.in",
    },
    "weather": {
        "english": "I can't give live weather forecasts. Please check the district agro-weather advisory before spraying or irrigating: https://agritech.tnau.ac.in/agrometeorologicaladvisory/agro_meteorological_advisory_eng.html",
        "tamil": "நேரடி வானிலை முன்னறிவிப்பு என்னால் தர முடியாது. மருந்து தெளிப்பதற்கு அல்லது பாசனத்துக்கு முன் மாவட்ட வேளாண் வானிலை ஆலோசனையைப் பார்க்கவும்: https://agritech.tnau.ac.in/agrometeorologicaladvisory/agro_meteorological_advisory_eng.html",
        "tanglish": "Live weather forecast ennala thara mudiyadhu. Marundhu adikkaradhukku illa thanni paaicharadhukku munnadi district agro-weather advisory paarunga: https://agritech.tnau.ac.in/agrometeorologicaladvisory/agro_meteorological_advisory_eng.html",
    },
    "scheme": {
        "english": "For scheme eligibility and benefits, please use the official sources:\n- PM-KISAN: https://pmkisan.gov.in\n- Crop insurance (PMFBY): https://pmfby.gov.in\n- Tamil Nadu Agriculture Department: https://www.tnagrisnet.tn.gov.in\nYour local agriculture office can also help you apply.",
        "tamil": "திட்டத் தகுதி மற்றும் பலன்களுக்கு அரசின் அதிகாரப்பூர்வ இணையதளங்களைப் பார்க்கவும்:\n- PM-KISAN: https://pmkisan.gov.in\n- பயிர்க் காப்பீடு (PMFBY): https://pmfby.gov.in\n- தமிழ்நாடு வேளாண்மைத் துறை: https://www.tnagrisnet.tn.gov.in\nவிண்ணப்பிக்க உங்கள் பகுதி வேளாண் அலுவலகமும் உதவும்.",
        "tanglish": "Scheme eligibility and benefits-ku official website-la paarunga:\n- PM-KISAN: https://pmkisan.gov.in\n- Crop insurance (PMFBY): https://pmfby.gov.in\n- Tamil Nadu Agriculture Department: https://www.tnagrisnet.tn.gov.in\nApply panna unga area agriculture office-um help pannuvanga.",
    },
    "image_upload_help": {
        "english": "Tap the photo button next to the message box, choose a clear, close photo of one affected leaf, then press \"Analyze photo\".",
        "tamil": "செய்திப் பெட்டிக்கு அருகிலுள்ள புகைப்பட பொத்தானை அழுத்தி, பாதிக்கப்பட்ட ஒரு இலையின் தெளிவான அருகாமைப் படத்தைத் தேர்ந்தெடுத்து, \"Analyze photo\" அழுத்தவும்.",
        "tanglish": "Message box pakkathula irukka photo button-a press panni, paadhikkapatta oru ilai-oda clear-aana close photo select panni, \"Analyze photo\" press pannunga.",
    },
    "answer_intro": {
        "english": "From the {publisher} — {title}:",
        "tamil": "{title} — {publisher} தரும் தகவல்:",
        "tanglish": "{title} pathi {publisher} solradhu:",
    },
    "english_only": {
        "english": "",
        "tamil": "(இந்தத் தகவல் தற்போது ஆங்கிலத்தில் மட்டுமே உள்ளது.)",
        "tanglish": "",
    },
    "chemical_safety": {
        "english": "Before using any chemical, confirm the product and dose with your local agriculture officer and follow the label.",
        "tamil": "எந்த ரசாயனத்தையும் பயன்படுத்தும் முன், அதன் பெயரையும் அளவையும் உங்கள் பகுதி வேளாண் அலுவலரிடம் உறுதி செய்து, லேபிள் வழிமுறைகளைப் பின்பற்றவும்.",
        "tanglish": "Edhavadhu marundhu/chemical use pannradhukku munnadi, adhoda peyar-um alavu-um unga agriculture officer kitta confirm panni, label-la irukkura maari use pannunga.",
    },
}

SCHEME_INTENTS = {"government_scheme", "pm_kisan", "crop_insurance", "subsidy"}
CHEMICAL_TOPICS = {"pest", "disease", "protection", "nutrient"}
MAX_EXCERPT = 900


def template(name: str, language: str, **values) -> str:
    text = TEMPLATES[name].get(language) or TEMPLATES[name]["english"]
    return text.format(**values) if values else text


def excerpt(content: str, limit: int = MAX_EXCERPT) -> str:
    """Cuts at a sentence or line boundary so an instruction is never chopped mid-way."""
    content = content.strip()
    if len(content) <= limit:
        return content
    window = content[:limit]
    cut = max(window.rfind("\n"), window.rfind(". "))
    return (window[: cut + 1] if cut > limit * 0.5 else window.rsplit(" ", 1)[0]).rstrip() + " …"


def compose_answer(records: List[dict], language: str, tamil_versions: Optional[Dict[str, dict]] = None) -> str:
    """Intro line + verbatim excerpts of 1–2 verified records (+ chemical safety note when relevant)."""
    parts: List[str] = []
    used_english_in_tamil = False
    for record in records[:2]:
        shown = record
        if language == "tamil" and tamil_versions and record.get("pair_id") in tamil_versions:
            shown = tamil_versions[record["pair_id"]]
        elif language == "tamil":
            used_english_in_tamil = True
        parts.append(template("answer_intro", language, publisher=shown.get("publisher", "TNAU Agritech Portal"),
                              title=f"**{shown['title']}**"))
        parts.append(excerpt(shown["content"]))
    if used_english_in_tamil:
        parts.append(template("english_only", language))
    if any(r.get("topic") in CHEMICAL_TOPICS for r in records[:2]):
        parts.append("⚠️ " + template("chemical_safety", language))
    return "\n\n".join(p for p in parts if p)


def sources_of(records: List[dict]) -> List[dict]:
    seen, sources = set(), []
    for r in records[:2]:
        if r.get("source_url") and r["source_url"] not in seen:
            seen.add(r["source_url"])
            sources.append({
                "title": r.get("title", ""),
                "url": r["source_url"],
                "publisher": r.get("publisher", "TNAU Agritech Portal"),
                "retrieved_at": r.get("retrieved_at"),
                "verification_status": r.get("verification_status"),
            })
    return sources



def generate_controlled_response(intent: str, retrieved_docs: list, language: str) -> str:
    """Kept for callers of the old API."""
    return compose_answer(retrieved_docs, language) if retrieved_docs else template("no_knowledge", language)
