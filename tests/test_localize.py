"""Unit tests for localization helpers and legal glossary."""

from app.nodes.localize import get_language_name, get_legal_glossary


def test_get_language_name():
    assert "Hindi" in get_language_name("hi")
    assert "Marathi" in get_language_name("mr")
    assert "Tamil" in get_language_name("ta")
    assert get_language_name("en") == "English"
    assert get_language_name("unknown_code") == "English"


def test_get_legal_glossary():
    hindi_glossary = get_legal_glossary("hi")
    assert "cultivable landholding" in hindi_glossary
    assert "खेती योग्य ज़मीन" in hindi_glossary["cultivable landholding"]

    marathi_glossary = get_legal_glossary("mr")
    assert "cultivable landholding" in marathi_glossary
    assert "शेतीयोग्य जमीन" in marathi_glossary["cultivable landholding"]

    # Fallback to English
    fallback_glossary = get_legal_glossary("unknown")
    assert "cultivable landholding" in fallback_glossary

