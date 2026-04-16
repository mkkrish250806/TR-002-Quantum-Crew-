from __future__ import annotations


HIGH_URGENCY = [
    "chest pain",
    "chest hurts",
    "chest hurt",
    "chest ache",
    "chest tightness",
    "shortness of breath",
    "breathing issue",
    "difficulty breathing",
    "severe bleeding",
    "unconscious",
]

MEDIUM_URGENCY = [
    "fever",
    "persistent cough",
    "dizziness",
    "vomiting",
    "fatigue",
]

SYMPTOM_DEPARTMENT = {
    "chest pain": "Cardiology",
    "chest hurts": "Cardiology",
    "chest hurt": "Cardiology",
    "breathing": "Pulmonology",
    "cough": "Pulmonology",
    "shoulder pain": "Orthopedics",
    "shoulder hurts": "Orthopedics",
    "leg pain": "Orthopedics",
    "leg hurts": "Orthopedics",
    "fever": "General Medicine",
    "fatigue": "General Medicine",
    "weakness": "Internal Medicine",
    "skin rash": "Dermatology",
    "headache": "Neurology",
}


def detect_urgency(message: str) -> str:
    text = message.lower()
    if any(term in text for term in HIGH_URGENCY):
        return "high"
    if any(term in text for term in MEDIUM_URGENCY):
        return "medium"
    return "low"


def map_department(message: str) -> str:
    text = message.lower()
    for symptom, dept in SYMPTOM_DEPARTMENT.items():
        if symptom in text:
            return dept
    return "General Medicine"


def mock_slots(department: str) -> list[str]:
    base_slots = {
        "Cardiology": ["10:30 AM", "12:00 PM", "4:30 PM"],
        "Pulmonology": ["9:30 AM", "2:00 PM", "6:00 PM"],
        "General Medicine": ["9:00 AM", "1:30 PM", "5:00 PM"],
        "Internal Medicine": ["11:00 AM", "3:00 PM", "6:30 PM"],
        "Orthopedics": ["10:15 AM", "1:45 PM", "5:15 PM"],
        "Dermatology": ["10:00 AM", "1:00 PM", "4:00 PM"],
        "Neurology": ["11:30 AM", "2:30 PM", "5:30 PM"],
    }
    return base_slots.get(department, ["9:00 AM", "12:30 PM", "4:30 PM"])
