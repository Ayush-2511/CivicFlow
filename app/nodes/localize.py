"""Localization and Legal Terminology Glossary Node.

Provides mapping from legal jargon to plain spoken regional expressions.
"""

from typing import Dict

LANGUAGE_NAMES: Dict[str, str] = {
    "hi": "Hindi (हिंदी)",
    "en": "English",
    "mr": "Marathi (मराठी)",
    "ta": "Tamil (தமிழ்)",
    "te": "Telugu (తెలుగు)",
    "bn": "Bengali (বাংলা)",
    "gu": "Gujarati (ગુજરાતી)",
    "kn": "Kannada (ಕನ್ನಡ)",
    "ml": "Malayalam (മലയാളം)",
    "ur": "Urdu (اردو)",
}

# Plain-language glossary for dense Indian administrative and legal terms
LEGAL_GLOSSARY: Dict[str, Dict[str, str]] = {
    "hi": {
        "cultivable landholding": "खेती योग्य ज़मीन",
        "encumbrance": "क़र्ज़ या कानूनी विवाद",
        "beneficiary": "योजना का लाभ पाने वाला",
        "institutional landholder": "संस्थान या ट्रस्ट के नाम वाली ज़मीन",
        "sub-divisional magistrate": "एसडीएम (उप-जिलाधिकारी)",
        "direct benefit transfer": "सीधे बैंक खाते में पैसा",
        "revenue records": "ज़मीन के सरकारी कागज़ात (खतौनी/जमाबंदी)",
        "exclusion criteria": "पात्रता से बाहर होने के नियम",
        "annual turnover": "साल भर का कुल कारोबार",
    },
    "mr": {
        "cultivable landholding": "शेतीयोग्य जमीन",
        "encumbrance": "कर्ज किंवा वाद",
        "beneficiary": "योजनेचा लाभार्थी",
        "revenue records": "जमिनीचे सरकारी कागदपत्रे (७/१२ उतारा)",
        "direct benefit transfer": "थेट बँक खात्यात पैसे",
        "annual turnover": "वार्षिक उलाढाल",
    },
    "en": {
        "cultivable landholding": "farmland that can be cultivated",
        "encumbrance": "existing loans or legal disputes",
        "institutional landholder": "land registered under an organization or trust",
        "revenue records": "official land ownership documents",
        "direct benefit transfer": "money sent directly to your bank account",
        "annual turnover": "total yearly business sales",
    },
}


def get_language_name(code: str) -> str:
    """Return friendly name for an ISO language code."""
    return LANGUAGE_NAMES.get(code.lower().strip(), "English")


def get_legal_glossary(language: str) -> Dict[str, str]:
    """Retrieve simplified regional legal glossary for the target language."""
    lang = language.lower().strip()
    return LEGAL_GLOSSARY.get(lang, LEGAL_GLOSSARY["en"])

