"""Static Journey Coach interface strings.

Only interface chrome is translated. Lesson points, scenarios, answers and source
excerpts stay in the English of the verified guide, so no translated sentence can
change what a source-grounded lesson says. There is no runtime machine translation.

Hindi strings were drafted by Minhaj Rahman (Week 9) and reviewed by Bikram
Bhattarai, a fluent Hindi reader, on 30 October 2026. Any change to them needs the
same review. The Hindi caption states that lessons remain in English.
"""

STRINGS = {
    "en": {
        "language": "Language",
        "caption": "Learn one idea. Try a scenario. Leave with a practical next step.",
        "source_error": "The saved lesson sources could not be verified. Restore the frozen guide first.",
        "guide_note": (
            "Based on the Medibank OSHC Member Guide, effective May 2026. "
            "General education in English, rather than a decision about your benefits."
        ),
        "start_again": "Start again",
        "choose_moment": "Choose your moment",
        "next_step": "Your next step: ",
        "check_answer": "Check my answer",
        "correct": "Correct. ",
        "try_again": "Try again. ",
        "read_original": "Read the original page in Navigator",
        "read_source": "Read the source excerpt",
        "publisher_note": (
            "The publisher link may show a newer edition. "
            "Navigator displays the saved guide."
        ),
    },
    "hi": {
        "language": "भाषा",
        "caption": "ज़रूरत से पहले एक उपयोगी जानकारी | अंग्रेज़ी डेमो पाठ",
        "source_error": "सहेजे गए पाठ स्रोत सत्यापित नहीं हो सके। पहले सुरक्षित गाइड को पुनर्स्थापित करें।",
        "guide_note": (
            "यह सामग्री मई 2026 से प्रभावी Medibank OSHC Member Guide पर आधारित है। "
            "ये पाठ सामान्य जानकारी समझाते हैं, आपके लाभ की पात्रता तय नहीं करते।"
        ),
        "start_again": "फिर से शुरू करें",
        "choose_moment": "एक समय चुनें",
        "next_step": "आपका अगला कदम: ",
        "check_answer": "मेरा उत्तर जाँचें",
        "correct": "सही। ",
        "try_again": "फिर कोशिश करें। ",
        "read_original": "Navigator में मूल पेज पढ़ें",
        "read_source": "स्रोत अंश पढ़ें",
        "publisher_note": (
            "प्रकाशक के लिंक पर नया संस्करण दिखाई दे सकता है। "
            "Navigator सहेजा गया गाइड दिखाता है।"
        ),
    },
}

LANGUAGE_LABELS = {"en": "English", "hi": "हिन्दी"}


def get_strings(language: str) -> dict[str, str]:
    """Return the selected static interface strings, falling back to English."""
    return STRINGS.get(language, STRINGS["en"])
