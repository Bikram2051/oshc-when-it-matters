"""Static Journey Coach interface strings.

Hindi strings are a draft and require human language review before the
Week 9 Hindi-review task can be marked complete.
"""

STRINGS = {
    "en": {
        "language": "Language",
        "caption": "One useful idea before you need it | English demo lessons",
        "offline_error": "Start this prototype in offline mode before practising.",
        "source_error": "The saved lesson sources could not be verified. Restore the frozen guide first.",
        "guide_note": (
            "Based on the Medibank OSHC Member Guide, effective May 2026. "
            "These lessons explain general information, not your entitlement to benefits."
        ),
        "start_again": "Start again",
        "choose_moment": "Choose a moment",
        "next_step": "Your next step: ",
        "quick_practice": "Quick practice",
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
        "offline_error": "अभ्यास करने से पहले इस प्रोटोटाइप को ऑफ़लाइन मोड में शुरू करें।",
        "source_error": "सहेजे गए पाठ स्रोत सत्यापित नहीं हो सके। पहले सुरक्षित गाइड को पुनर्स्थापित करें।",
        "guide_note": (
            "यह सामग्री मई 2026 से प्रभावी Medibank OSHC Member Guide पर आधारित है। "
            "ये पाठ सामान्य जानकारी समझाते हैं, आपके लाभ की पात्रता तय नहीं करते।"
        ),
        "start_again": "फिर से शुरू करें",
        "choose_moment": "एक समय चुनें",
        "next_step": "आपका अगला कदम: ",
        "quick_practice": "त्वरित अभ्यास",
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


def get_strings(language: str) -> dict[str, str]:
    """Return the selected static interface strings."""
    return STRINGS.get(language, STRINGS["en"])
