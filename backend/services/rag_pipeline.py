from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from threading import Lock

from services.appointment import AppointmentService
from services.intent import classify_intent
from services.llm_handler import LLMHandler
from services.sentiment import detect_emotion, tone_prefix
from services.triage import detect_urgency, map_department, mock_slots


@dataclass
class Analytics:
    total_queries: int = 0
    resolved_queries: int = 0
    unresolved_queries: int = 0
    emergency_cases_flagged: int = 0
    _lock: Lock = field(default_factory=Lock)

    def update(self, resolved: bool, emergency: bool) -> None:
        with self._lock:
            self.total_queries += 1
            if resolved:
                self.resolved_queries += 1
            else:
                self.unresolved_queries += 1
            if emergency:
                self.emergency_cases_flagged += 1

    def snapshot(self) -> dict:
        with self._lock:
            rate = 0.0
            if self.total_queries > 0:
                rate = (self.resolved_queries / self.total_queries) * 100
            return {
                "total_queries": self.total_queries,
                "resolved_queries": self.resolved_queries,
                "unresolved_queries": self.unresolved_queries,
                "resolution_rate": round(rate, 2),
                "emergency_cases_flagged": self.emergency_cases_flagged,
            }


class RAGPipeline:
    def __init__(self) -> None:
        self.llm = LLMHandler()
        self.appointment_service = AppointmentService()
        self.analytics = Analytics()
        self.sessions: dict[str, list[dict[str, str]]] = {}
        self.profiles: dict[str, dict[str, str]] = {}

    def _session_context(self, session_id: str) -> str:
        memory = self.sessions.get(session_id, [])[-8:]
        if not memory:
            return ""
        return "\n".join(f"{m['role']}: {m['content']}" for m in memory)

    def _save_session_turn(self, session_id: str, user_message: str, bot_message: str) -> None:
        self.sessions.setdefault(session_id, [])
        timestamp = datetime.now().isoformat(timespec="seconds")
        self.sessions[session_id].append({"role": "user", "content": user_message, "timestamp": timestamp})
        self.sessions[session_id].append(
            {"role": "assistant", "content": bot_message, "timestamp": timestamp}
        )
        self.sessions[session_id] = self.sessions[session_id][-40:]

    @staticmethod
    def _extract_name(message: str) -> str | None:
        patterns = [
            r"\bmy name is ([a-zA-Z][a-zA-Z\s]{1,40})\b",
            r"\bthis is ([a-zA-Z][a-zA-Z\s]{1,40})\b",
            r"\bi am ([a-zA-Z][a-zA-Z\s]{1,40})\b",
        ]
        for pattern in patterns:
            match = re.search(pattern, message.strip(), flags=re.IGNORECASE)
            if not match:
                continue
            candidate = match.group(1).strip(" .,!?")
            if len(candidate.split()) <= 3:
                return " ".join(word.capitalize() for word in candidate.split())
        return None

    @staticmethod
    def _is_name_only_message(message: str) -> bool:
        text = message.strip().lower()
        patterns = [
            r"^\s*my name is [a-zA-Z][a-zA-Z\s]{1,40}[.!]?\s*$",
            r"^\s*this is [a-zA-Z][a-zA-Z\s]{1,40}[.!]?\s*$",
            r"^\s*i am [a-zA-Z][a-zA-Z\s]{1,40}[.!]?\s*$",
        ]
        return any(re.fullmatch(pattern, text) for pattern in patterns)

    @staticmethod
    def _extract_lab_values(message: str) -> dict[str, float]:
        patterns = {
            "hemoglobin": r"(?:hemoglobin|hb)\s*[:=]?\s*(\d+\.?\d*)",
            "fasting_glucose": r"(?:fasting sugar|fasting glucose|fbs)\s*[:=]?\s*(\d+\.?\d*)",
            "random_glucose": r"(?:random sugar|random glucose|rbs)\s*[:=]?\s*(\d+\.?\d*)",
        }
        text = message.lower()
        values: dict[str, float] = {}
        for key, pattern in patterns.items():
            match = re.search(pattern, text)
            if match:
                values[key] = float(match.group(1))
        return values

    @staticmethod
    def _lab_explanation(values: dict[str, float]) -> str:
        if not values:
            return ""

        lines: list[str] = []
        hb = values.get("hemoglobin")
        if hb is not None:
            if hb < 12.0:
                lines.append(f"Hemoglobin is {hb} g/dL, which can be lower than common adult ranges.")
            else:
                lines.append(f"Hemoglobin is {hb} g/dL, which is often within common adult ranges.")

        fasting = values.get("fasting_glucose")
        if fasting is not None:
            if fasting >= 126:
                lines.append(f"Fasting glucose is {fasting} mg/dL, which is above the usual reference range.")
            elif fasting >= 100:
                lines.append(f"Fasting glucose is {fasting} mg/dL, which is mildly elevated.")
            else:
                lines.append(f"Fasting glucose is {fasting} mg/dL, which is usually considered normal.")

        random_value = values.get("random_glucose")
        if random_value is not None:
            if random_value >= 200:
                lines.append(f"Random glucose is {random_value} mg/dL, which is elevated.")
            else:
                lines.append(f"Random glucose is {random_value} mg/dL and is not markedly elevated.")

        return " ".join(lines)

    def _profile(self, session_id: str) -> dict[str, str]:
        return self.profiles.setdefault(session_id, {})

    @staticmethod
    def _is_slot_selection_message(message: str, slot: str | None) -> bool:
        if not slot:
            return False
        text = message.lower().strip()
        booking_terms = ["select", "choose", "confirm", "book", "reserve", "slot"]
        return any(term in text for term in booking_terms) or len(text.split()) <= 5

    @staticmethod
    def _booking_priority(urgency: str) -> tuple[str, int]:
        mapping = {
            "high": ("High", 3),
            "medium": ("Medium", 2),
            "low": ("Routine", 1),
        }
        return mapping.get(urgency, ("Routine", 1))

    def _compose_response(
        self,
        message: str,
        session_id: str,
        intent: str,
        urgency: str,
        emotion: str,
        profile: dict[str, str],
        offer_appointment_options: bool,
        include_name_greeting: bool,
    ) -> str:
        conversation_context = self._session_context(session_id)
        answer = self.llm.generate(
            user_query=message,
            conversation_context=conversation_context,
            patient_profile=profile,
            intent=intent,
            urgency=urgency,
            emotion=emotion,
        )

        if offer_appointment_options and urgency != "high":
            department = map_department(message)
            profile["last_department"] = department
            live_slots = self.appointment_service.get_available_slots(department)
            slots = ", ".join(live_slots if live_slots else mock_slots(department))
            answer += (
                f"\nRecommended department: {department}. "
                f"Available appointment slots today: {slots}."
            )

        if intent == "lab_report":
            lab_note = self._lab_explanation(self._extract_lab_values(message))
            if lab_note:
                answer += f"\n{lab_note}"

        if urgency == "high":
            answer += (
                "\nThis may need urgent medical attention. "
                "Please contact emergency services or go to the nearest emergency department now."
            )

        final_answer = f"{tone_prefix(emotion, urgency)}{answer}"
        if include_name_greeting and profile.get("name"):
            final_answer = f"Welcome, {profile['name']}. {final_answer}"
        return final_answer

    def handle_query(self, message: str, session_id: str) -> dict:
        intent = classify_intent(message)
        emotion = detect_emotion(message)
        urgency = detect_urgency(message)
        profile = self._profile(session_id)
        booking_status = "none"
        booking_id = ""
        booked_slot = ""
        booked_department = ""

        extracted_name = self._extract_name(message)
        is_new_name = bool(extracted_name and not profile.get("name"))
        if extracted_name:
            profile["name"] = extracted_name

        if extracted_name and self._is_name_only_message(message):
            answer = (
                f"Welcome, {extracted_name}. "
                "I am your hospital support assistant, and I can help with symptoms, appointments, billing questions, lab report discussions, and follow-up guidance."
            )
            answer = f"{tone_prefix(emotion, urgency)}{answer}"
            self.analytics.update(resolved=True, emergency=False)
            self._save_session_turn(session_id=session_id, user_message=message, bot_message=answer)
            return {
                "answer": answer,
                "intent": "faq",
                "confidence": 0.95,
                "urgency": "low",
                "emotion": emotion,
                "resolved": True,
                "sources": ["medical-llm-assistant"],
                "booking_status": "none",
                "booking_id": "",
                "booked_slot": "",
                "booked_department": "",
                "patient_name": extracted_name,
            }

        slot_in_message = self.appointment_service.extract_slot(message)
        booking_pending = profile.get("booking_pending") == "1"
        slot_selection = self._is_slot_selection_message(message, slot_in_message)
        wants_booking = self.appointment_service.wants_booking(message)
        has_department_context = bool(profile.get("last_department"))
        if slot_selection and (booking_pending or has_department_context):
            department = profile.get("last_department") or map_department(message)
            priority_label, priority_rank = self._booking_priority(urgency)
            booking = self.appointment_service.book(
                session_id=session_id,
                patient_name=profile.get("name", "Patient"),
                department=department,
                slot=slot_in_message or "",
                priority_label=priority_label,
                priority_rank=priority_rank,
            )
            booking_status = "confirmed" if booking["success"] else "failed"
            booking_id = str(booking["booking_id"] or "") if booking["success"] else ""
            booked_slot = str(booking["slot"] or "") if booking["success"] else ""
            booked_department = str(booking["department"] or department)
            profile["booking_pending"] = "0" if booking["success"] else "1"
            if booking["success"] and booking_id:
                profile["last_booking_id"] = booking_id

            answer = f"{tone_prefix(emotion, urgency)}{booking['message']}"
            self.analytics.update(resolved=booking["success"], emergency=False)
            self._save_session_turn(session_id=session_id, user_message=message, bot_message=answer)
            return {
                "answer": answer,
                "intent": "appointment",
                "confidence": 0.98 if booking["success"] else 0.45,
                "urgency": "low",
                "emotion": emotion,
                "resolved": bool(booking["success"]),
                "sources": ["appointment-service"],
                "booking_status": booking_status,
                "booking_id": booking_id,
                "booked_slot": booked_slot,
                "booked_department": booked_department,
                "patient_name": profile.get("name", ""),
            }

        answer = self._compose_response(
            message=message,
            session_id=session_id,
            intent=intent,
            urgency=urgency,
            emotion=emotion,
            profile=profile,
            offer_appointment_options=(intent == "appointment" or wants_booking or booking_pending),
            include_name_greeting=(is_new_name and not self._is_name_only_message(message)),
        )

        if slot_in_message and (intent == "appointment" or booking_pending):
            wants_booking = True

        if wants_booking:
            department = profile.get("last_department") or map_department(message)
            profile["last_department"] = department
            if slot_in_message is None:
                available = self.appointment_service.get_available_slots(department)
                slot_msg = ", ".join(available if available else mock_slots(department))
                answer += (
                    f"\nTo confirm the appointment, reply with one exact slot: {slot_msg}."
                )
                booking_status = "pending_slot"
                profile["booking_pending"] = "1"
            else:
                priority_label, priority_rank = self._booking_priority(urgency)
                booking = self.appointment_service.book(
                    session_id=session_id,
                    patient_name=profile.get("name", "Patient"),
                    department=department,
                    slot=slot_in_message,
                    priority_label=priority_label,
                    priority_rank=priority_rank,
                )
                answer += f"\n{booking['message']}"
                if booking["success"]:
                    booking_status = "confirmed"
                    booking_id = str(booking["booking_id"] or "")
                    booked_slot = str(booking["slot"] or "")
                    booked_department = str(booking["department"] or "")
                    profile["last_booking_id"] = booking_id
                    profile["booking_pending"] = "0"
                else:
                    booking_status = "failed"
                    profile["booking_pending"] = "1"

        profile["last_intent"] = intent
        profile["last_seen"] = datetime.now().isoformat(timespec="seconds")

        resolved = not answer.lower().startswith("i'm sorry, but i need a little more")
        confidence = 0.92 if urgency != "high" else 0.99

        self.analytics.update(resolved=resolved, emergency=(urgency == "high"))
        self._save_session_turn(session_id=session_id, user_message=message, bot_message=answer)

        return {
            "answer": answer,
            "intent": intent,
            "confidence": confidence,
            "urgency": urgency,
            "emotion": emotion,
            "resolved": resolved,
            "sources": ["medical-llm-assistant"],
            "booking_status": booking_status,
            "booking_id": booking_id,
            "booked_slot": booked_slot,
            "booked_department": booked_department,
            "patient_name": profile.get("name", ""),
        }

    def get_metrics(self) -> dict:
        return self.analytics.snapshot()

    def get_session_report_context(self, session_id: str) -> dict:
        return {
            "session_id": session_id,
            "profile": self.profiles.get(session_id, {}),
            "messages": self.sessions.get(session_id, []),
        }

    def get_doctor_dashboard_data(self) -> list[dict]:
        records: list[dict] = []
        for booking in self.appointment_service.list_bookings():
            session_id = str(booking.get("session_id", ""))
            profile = self.profiles.get(session_id, {})
            records.append(
                {
                    "booking_id": str(booking.get("booking_id", "")),
                    "session_id": session_id,
                    "patient_name": str(booking.get("patient_name", "Patient")),
                    "department": str(booking.get("department", "")),
                    "slot": str(booking.get("slot", "")),
                    "date": str(booking.get("date", "")),
                    "created_at": str(booking.get("created_at", "")),
                    "priority_label": str(booking.get("priority_label", "Routine")),
                    "priority_rank": int(booking.get("priority_rank", 1)),
                    "last_support_topic": str(profile.get("last_intent", "")),
                    "report_url": f"/chat/report/{session_id}",
                    "patient_summary": self._doctor_summary(session_id),
                }
            )
        return records

    def _doctor_summary(self, session_id: str) -> str:
        messages = self.sessions.get(session_id, [])
        user_messages = [msg.get("content", "").strip() for msg in messages if msg.get("role") == "user"]
        if not user_messages:
            return "Patient support conversation available."
        return user_messages[0][:140]


_PIPELINE: RAGPipeline | None = None


def get_rag_pipeline() -> RAGPipeline:
    global _PIPELINE
    if _PIPELINE is None:
        _PIPELINE = RAGPipeline()
    return _PIPELINE
