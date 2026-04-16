from __future__ import annotations


INTENT_KEYWORDS: dict[str, list[str]] = {
    "symptom": [
        "pain",
        "hurt",
        "hurts",
        "ache",
        "aching",
        "fever",
        "cough",
        "weakness",
        "fatigue",
        "breathing",
        "bleeding",
        "dizzy",
        "vomit",
        "nausea",
    ],
    "appointment": [
        "appointment",
        "reschedule",
        "slot",
        "doctor",
        "book",
        "visit",
        "department",
    ],
    "lab_report": [
        "lab",
        "report",
        "hemoglobin",
        "hb",
        "sugar",
        "glucose",
        "result",
        "test value",
    ],
    "billing": [
        "bill",
        "payment",
        "refund",
        "invoice",
        "insurance",
        "charge",
        "copay",
    ],
    "faq": ["hours", "policy", "parking", "cafeteria", "visitor", "support", "help"],
}


def classify_intent(message: str) -> str:
    text = message.lower()
    scores: dict[str, int] = {}

    for intent, keywords in INTENT_KEYWORDS.items():
        scores[intent] = sum(1 for kw in keywords if kw in text)

    best_intent = max(scores, key=scores.get)
    if scores[best_intent] == 0:
        return "faq"
    return best_intent
