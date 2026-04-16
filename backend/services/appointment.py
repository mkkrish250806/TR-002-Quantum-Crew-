from __future__ import annotations

import re
from datetime import datetime
from itertools import count


BOOKING_KEYWORDS = [
    "book",
    "confirm",
    "reserve",
    "schedule",
    "take this slot",
    "slot",
    "choose",
    "i'll choose",
    "ill choose",
    "select",
]
TIME_PATTERN = re.compile(r"\b(\d{1,2})(?::(\d{2}))?\s*(am|pm)\b", re.IGNORECASE)


class AppointmentService:
    def __init__(self) -> None:
        self._id_counter = count(1001)
        self._bookings: list[dict] = []
        self._base_slots = {
            "Cardiology": ["10:30 AM", "12:00 PM", "4:30 PM"],
            "Pulmonology": ["9:30 AM", "2:00 PM", "6:00 PM"],
            "General Medicine": ["9:00 AM", "1:30 PM", "5:00 PM"],
            "Internal Medicine": ["11:00 AM", "3:00 PM", "6:30 PM"],
            "Orthopedics": ["10:15 AM", "1:45 PM", "5:15 PM"],
            "Dermatology": ["10:00 AM", "1:00 PM", "4:00 PM"],
            "Neurology": ["11:30 AM", "2:30 PM", "5:30 PM"],
        }

    def get_available_slots(self, department: str) -> list[str]:
        booked_slots = {
            b["slot"] for b in self._bookings if b["department"] == department and b["date"] == self._today()
        }
        return [s for s in self._base_slots.get(department, []) if s not in booked_slots]

    @staticmethod
    def wants_booking(message: str) -> bool:
        text = message.lower()
        return any(kw in text for kw in BOOKING_KEYWORDS)

    @staticmethod
    def extract_slot(message: str) -> str | None:
        match = TIME_PATTERN.search(message)
        if not match:
            return None
        hour = int(match.group(1))
        minute = int(match.group(2) or "0")
        meridiem = match.group(3).upper()
        return f"{hour}:{minute:02d} {meridiem}"

    def book(self, session_id: str, patient_name: str, department: str, slot: str) -> dict:
        available = self.get_available_slots(department)
        if slot not in available:
            return {
                "success": False,
                "message": f"Slot {slot} is no longer available for {department}. Please choose another slot.",
                "booking_id": None,
                "slot": None,
                "department": department,
            }

        booking_id = f"APT-{next(self._id_counter)}"
        record = {
            "booking_id": booking_id,
            "session_id": session_id,
            "patient_name": patient_name or "Patient",
            "department": department,
            "slot": slot,
            "date": self._today(),
            "created_at": datetime.now().isoformat(timespec="seconds"),
        }
        self._bookings.append(record)
        return {
            "success": True,
            "message": (
                f"Your appointment is confirmed for {department} at {slot} today. "
                f"Booking ID: {booking_id}."
            ),
            "booking_id": booking_id,
            "slot": slot,
            "department": department,
        }

    @staticmethod
    def _today() -> str:
        return datetime.now().strftime("%Y-%m-%d")
