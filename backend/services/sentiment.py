from __future__ import annotations


ANXIOUS_TERMS = ["worried", "anxious", "scared", "panic", "nervous", "urgent"]
FRUSTRATED_TERMS = ["angry", "frustrated", "upset", "annoyed", "terrible", "bad service"]
POSITIVE_TERMS = ["thanks", "thank you", "great", "good", "helpful", "relieved"]


def detect_emotion(message: str) -> str:
    text = message.lower()
    anxious_hits = sum(1 for term in ANXIOUS_TERMS if term in text)
    frustrated_hits = sum(1 for term in FRUSTRATED_TERMS if term in text)
    positive_hits = sum(1 for term in POSITIVE_TERMS if term in text)

    if anxious_hits > frustrated_hits and anxious_hits > 0:
        return "anxious"
    if frustrated_hits > 0:
        return "frustrated"
    if positive_hits > 0:
        return "positive"
    return "neutral"


def tone_prefix(emotion: str, urgency: str = "low") -> str:
    if urgency == "high":
        return "I am taking this seriously and I will guide you right away. "
    if emotion == "anxious":
        return "I understand this can feel stressful. "
    if emotion == "frustrated":
        return "I hear your frustration, and I want to help quickly. "
    if emotion == "positive":
        return "Glad to hear from you. "
    return ""
