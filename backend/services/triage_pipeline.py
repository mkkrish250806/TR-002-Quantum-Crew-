from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from threading import Lock

from services.appointment import AppointmentService
from services.icd_triage import ICDTriageEngine
from services.llm_handler import LLMHandler


@dataclass
class Analytics:
    total_queries: int = 0
    emergency_cases_flagged: int = 0
    follow_up_questions_asked: int = 0
    _lock: Lock = field(default_factory=Lock)

    def record(self, urgency: str) -> None:
        with self._lock:
            self.total_queries += 1
            self.follow_up_questions_asked += 1
            if urgency == "high":
                self.emergency_cases_flagged += 1

    def snapshot(self) -> dict:
        with self._lock:
            return {
                "total_queries": self.total_queries,
                "resolved_queries": 0,
                "unresolved_queries": self.total_queries,
                "resolution_rate": 0,
                "emergency_cases_flagged": self.emergency_cases_flagged,
                "follow_up_questions_asked": self.follow_up_questions_asked,
            }


class TriagePipeline:
    def __init__(self) -> None:
        self.engine = ICDTriageEngine()
        self.llm = LLMHandler()
        self.appointment_service = AppointmentService()
        self.analytics = Analytics()
        self.sessions: dict[str, list[dict[str, str]]] = {}
        self.profiles: dict[str, dict[str, str]] = {}

    def _profile(self, session_id: str) -> dict[str, str]:
        return self.profiles.setdefault(
            session_id,
            {
                "triage_stage": "intake",
                "asked_questions": "",
                "collected_symptoms": "",
                "possible_conditions": "",
                "question_count": "0",
                "booking_pending": "0",
                "booking_prompted": "0",
            },
        )

    def _append_messages(self, session_id: str, user_message: str, assistant_message: str) -> None:
        history = self.sessions.setdefault(session_id, [])
        timestamp = datetime.now().isoformat(timespec="seconds")
        history.append({"role": "user", "content": user_message, "timestamp": timestamp})
        history.append({"role": "assistant", "content": assistant_message, "timestamp": timestamp})
        self.sessions[session_id] = history[-60:]

    @staticmethod
    def _stored_list_to_set(value: str) -> set[str]:
        if not value:
            return set()
        try:
            data = json.loads(value)
        except json.JSONDecodeError:
            return set()
        if not isinstance(data, list):
            return set()
        return {str(item).strip() for item in data if str(item).strip()}

    @staticmethod
    def _set_to_stored_list(values: set[str]) -> str:
        return json.dumps(sorted(values))

    @staticmethod
    def _normalize_name(value: str) -> str:
        return " ".join(word.capitalize() for word in value.strip().split()[:3])

    @staticmethod
    def _extract_name(message: str, existing_name: str = "") -> str | None:
        if existing_name.strip():
            explicit_match = re.search(
                r"\b(?:my name is|i am|this is)\s+([a-zA-Z][a-zA-Z\s]{1,40})",
                message,
                re.IGNORECASE,
            )
            if not explicit_match:
                return None
            candidate = explicit_match.group(1).strip()
            return TriagePipeline._normalize_name(candidate)

        match = re.search(r"\b(?:my name is|i am|this is)\s+([a-zA-Z][a-zA-Z\s]{1,40})", message, re.IGNORECASE)
        if match:
            candidate = match.group(1).strip()
            return TriagePipeline._normalize_name(candidate)

        cleaned = re.sub(r"\s+", " ", message.strip())
        if not re.fullmatch(r"[A-Za-z]+(?:\s+[A-Za-z]+){0,2}", cleaned):
            return None

        blocked_words = {
            "i",
            "have",
            "had",
            "fever",
            "cough",
            "pain",
            "help",
            "need",
            "appointment",
            "book",
            "mild",
            "severe",
            "moderate",
            "symptom",
            "symptoms",
            "doctor",
            "hospital",
        }
        parts = cleaned.lower().split()
        if any(part in blocked_words for part in parts):
            return None
        return TriagePipeline._normalize_name(cleaned)

    def handle_query(self, message: str, session_id: str, history: list[dict[str, str]] | None = None) -> dict:
        profile = self._profile(session_id)
        previous_questions = self._stored_list_to_set(profile.get("asked_questions", ""))
        known_symptoms = self._stored_list_to_set(profile.get("collected_symptoms", ""))
        existing_facts = {
            key: value
            for key, value in profile.items()
            if key in {"duration", "severity", "cough_type"} and value
        }

        extracted_name = self._extract_name(message, profile.get("name", ""))
        if extracted_name:
            profile["name"] = extracted_name
        patient_name = profile.get("name", "").strip()

        if not patient_name:
            answer = "Welcome to MediAssist. I am here to help you. Please enter your name to continue."
            self._append_messages(session_id, message, answer)
            return {
                "answer": answer,
                "next_question": answer,
                "intent": "patient_intake",
                "confidence": 0.99,
                "urgency": "low",
                "emotion": "clinical",
                "resolved": False,
                "sources": ["patient-intake"],
                "booking_status": "none",
                "booking_id": "",
                "booked_slot": "",
                "booked_department": "",
                "patient_name": "",
                "possible_conditions": [],
            }

        if extracted_name and not self.engine.extract_symptoms(message):
            answer = (
                f"Welcome, {patient_name}. What kind of help can I do for you today? "
                "You can tell me about your symptoms, health problem, or if you need an appointment."
            )
            self._append_messages(session_id, message, answer)
            return {
                "answer": answer,
                "next_question": "What kind of help can I do for you today?",
                "intent": "patient_intake",
                "confidence": 0.98,
                "urgency": "low",
                "emotion": "clinical",
                "resolved": False,
                "sources": ["patient-intake"],
                "booking_status": "none",
                "booking_id": "",
                "booked_slot": "",
                "booked_department": "",
                "patient_name": patient_name,
                "possible_conditions": [],
            }

        extracted_symptoms = self.engine.extract_symptoms(message, history=history)
        known_symptoms.update(extracted_symptoms)
        facts = self.engine.extract_clinical_facts(message)
        existing_facts.update(facts)

        if not known_symptoms:
            answer = f"Thank you, {patient_name}. What is the main symptom or health problem you are having right now?"
            self._append_messages(session_id, message, answer)
            return {
                "answer": answer,
                "next_question": answer,
                "intent": "patient_intake",
                "confidence": 0.95,
                "urgency": "low",
                "emotion": "clinical",
                "resolved": False,
                "sources": ["patient-intake"],
                "booking_status": "none",
                "booking_id": "",
                "booked_slot": "",
                "booked_department": "",
                "patient_name": patient_name,
                "possible_conditions": [],
            }

        matches = self.engine.rank_conditions(known_symptoms)
        possible_conditions = [f"{match.disease} ({match.code})" for match in matches]
        urgency = self.engine.detect_urgency(known_symptoms, existing_facts)
        question_count = int(profile.get("question_count", "0") or "0")
        slot_in_message = self.appointment_service.extract_slot(message)
        wants_booking = self.appointment_service.wants_booking(message)
        booking_pending = profile.get("booking_pending") == "1"

        if booking_pending and slot_in_message:
            department = profile.get("last_department", matches[0].department if matches else "General Medicine")
            priority_label = "Urgent" if urgency == "high" else "Routine"
            priority_rank = 3 if urgency == "high" else 1
            booking = self.appointment_service.book(
                session_id=session_id,
                patient_name=patient_name,
                department=department,
                slot=slot_in_message,
                priority_label=priority_label,
                priority_rank=priority_rank,
            )
            answer = booking["message"]
            profile["booking_pending"] = "0" if booking["success"] else "1"
            if booking["success"]:
                profile["last_booking_id"] = str(booking["booking_id"] or "")
                profile["booked_slot"] = str(booking["slot"] or "")
                profile["last_department"] = str(booking["department"] or department)
            self._append_messages(session_id, message, answer)
            return {
                "answer": answer,
                "next_question": "Is there anything else you want to mention before your appointment?",
                "intent": "appointment",
                "confidence": 0.98 if booking["success"] else 0.5,
                "urgency": urgency,
                "emotion": "clinical",
                "resolved": bool(booking["success"]),
                "sources": ["appointment-service"],
                "booking_status": "confirmed" if booking["success"] else "failed",
                "booking_id": str(booking["booking_id"] or ""),
                "booked_slot": str(booking["slot"] or ""),
                "booked_department": str(booking["department"] or department),
                "patient_name": patient_name,
                "possible_conditions": possible_conditions,
            }

        if wants_booking:
            department = profile.get("last_department", matches[0].department if matches else "General Medicine")
            slots = self.appointment_service.get_available_slots(department)
            slot_text = ", ".join(slots) if slots else "No slots are available right now."
            answer = (
                f"{patient_name}, I can help book an appointment in {department}. "
                f"Available slots today: {slot_text}. "
                "Reply with the exact time slot to confirm."
            )
            profile["booking_pending"] = "1"
            profile["last_department"] = department
            self._append_messages(session_id, message, answer)
            return {
                "answer": answer,
                "next_question": "Reply with the exact time slot to confirm your appointment.",
                "intent": "appointment",
                "confidence": 0.96,
                "urgency": urgency,
                "emotion": "clinical",
                "resolved": False,
                "sources": ["appointment-service"],
                "booking_status": "pending_slot",
                "booking_id": "",
                "booked_slot": "",
                "booked_department": department,
                "patient_name": patient_name,
                "possible_conditions": possible_conditions,
            }

        # Serialize ICD matches for LLM consumption
        icd_matches_payload = [
            {
                "code": m.code,
                "disease": m.disease,
                "department": m.department,
                "score": m.score,
                "matched_symptoms": m.matched_symptoms,
                "missing_symptoms": m.missing_symptoms,
            }
            for m in matches
        ]

        next_question_seed = self.engine.next_question_candidates(matches, previous_questions, existing_facts)
        next_question = self.llm.generate_triage_question(
            user_message=message,
            known_symptoms=sorted(known_symptoms),
            possible_conditions=possible_conditions,
            conversation_context=self._session_context(session_id),
            suggested_questions=next_question_seed,
            urgency=urgency,
            icd_matches=icd_matches_payload,
        )
        previous_questions.add(next_question)
        question_count += 1

        # Generate disease prediction after 2+ questions or if urgency is high
        disease_prediction = ""
        if (question_count >= 2 or urgency == "high") and matches:
            disease_prediction = self.llm.generate_disease_prediction(
                known_symptoms=sorted(known_symptoms),
                icd_matches=icd_matches_payload,
                patient_profile=profile,
                urgency=urgency,
            )

        answer = next_question
        if disease_prediction:
            answer += f"\n\n{disease_prediction}"
        else:
            answer += f"\n\nPossible conditions being explored: {', '.join(possible_conditions) if possible_conditions else 'General symptom review'}."
        answer += f"\n{self.engine.safety_note(urgency)}"

        should_offer_booking = (
            (urgency == "high" or question_count >= 3)
            and profile.get("booking_prompted") != "1"
            and profile.get("last_booking_id", "") == ""
        )
        if should_offer_booking:
            department = matches[0].department if matches else "General Medicine"
            slots = self.appointment_service.get_available_slots(department)
            if slots:
                answer += (
                    f"\n\nIf you want a doctor appointment, I can arrange one in {department}. "
                    f"Available slots today: {', '.join(slots)}. Reply with the exact slot time or say book appointment."
                )
                profile["booking_prompted"] = "1"
                profile["booking_pending"] = "1"
                profile["last_department"] = department

        profile["collected_symptoms"] = self._set_to_stored_list(known_symptoms)
        profile["asked_questions"] = self._set_to_stored_list(previous_questions)
        profile["possible_conditions"] = ", ".join(possible_conditions)
        profile["triage_stage"] = "follow_up"
        profile["last_intent"] = "symptom_triage"
        profile["last_seen"] = datetime.now().isoformat(timespec="seconds")
        profile["question_count"] = str(question_count)
        profile["urgency"] = urgency
        if matches:
            profile["last_department"] = matches[0].department
        for key, value in existing_facts.items():
            profile[key] = value

        self.analytics.record(urgency)
        self._append_messages(session_id, message, answer)

        return {
            "answer": answer,
            "next_question": next_question,
            "intent": "symptom_triage",
            "confidence": round(matches[0].score if matches else 0.35, 2),
            "urgency": urgency,
            "emotion": "clinical",
            "resolved": False,
            "sources": [f"ICD-10: {match.code}" for match in matches] or ["ICD-10 symptom engine"],
            "booking_status": "none",
            "booking_id": "",
            "booked_slot": "",
            "booked_department": profile.get("last_department", ""),
            "patient_name": patient_name,
            "possible_conditions": possible_conditions,
            "disease_prediction": disease_prediction,
            "icd_matches": icd_matches_payload,
        }

    def _session_context(self, session_id: str) -> str:
        memory = self.sessions.get(session_id, [])[-8:]
        if not memory:
            return ""
        return "\n".join(f"{item['role']}: {item['content']}" for item in memory)

    def get_metrics(self) -> dict:
        return self.analytics.snapshot()

    def get_session_report_context(self, session_id: str) -> dict:
        return {
            "session_id": session_id,
            "profile": self.profiles.get(session_id, {}),
            "messages": self.sessions.get(session_id, []),
        }

    def get_doctor_dashboard_data(self) -> list[dict]:
        dashboard: list[dict] = []

        bookings = self.appointment_service.list_bookings()
        if bookings:
            records: list[dict] = []
            for booking in bookings:
                session_id = str(booking.get("session_id", ""))
                profile = self.profiles.get(session_id, {})
                records.append(
                    {
                        "booking_id": str(booking.get("booking_id", "")),
                        "session_id": session_id,
                        "patient_name": str(booking.get("patient_name", profile.get("name", "Patient"))),
                        "department": str(booking.get("department", profile.get("last_department", "General Medicine"))),
                        "slot": str(booking.get("slot", "")),
                        "date": str(booking.get("date", "")),
                        "created_at": str(booking.get("created_at", profile.get("last_seen", ""))),
                        "priority_label": str(booking.get("priority_label", "Routine")),
                        "priority_rank": int(booking.get("priority_rank", 1)),
                        "last_support_topic": "symptom_triage",
                        "report_url": f"/chat/report/{session_id}",
                        "patient_summary": self._doctor_summary(profile),
                    }
                )
            return records

        for session_id, profile in self.profiles.items():
            if profile.get("name"):
                dashboard.append(
                    {
                        "booking_id": str(profile.get("last_booking_id", "")),
                        "session_id": session_id,
                        "patient_name": profile.get("name", "Patient"),
                        "department": profile.get("last_department", "General Medicine"),
                        "slot": profile.get("booked_slot", ""),
                        "date": datetime.now().strftime("%Y-%m-%d"),
                        "created_at": profile.get("last_seen", ""),
                        "priority_label": "Urgent" if profile.get("urgency") == "high" else "Routine",
                        "priority_rank": 3 if profile.get("urgency") == "high" else 1,
                        "last_support_topic": "symptom_triage",
                        "report_url": f"/chat/report/{session_id}",
                        "patient_summary": self._doctor_summary(profile),
                    }
                )
        return dashboard

    @staticmethod
    def _doctor_summary(profile: dict[str, str]) -> str:
        symptoms = profile.get("collected_symptoms", "")
        parsed_symptoms: list[str] = []
        if symptoms:
            try:
                data = json.loads(symptoms)
                if isinstance(data, list):
                    parsed_symptoms = [str(item).replace("_", " ") for item in data if str(item).strip()]
            except json.JSONDecodeError:
                parsed_symptoms = []

        symptom_text = ", ".join(parsed_symptoms[:6]) if parsed_symptoms else "symptoms under review"
        possible_conditions = profile.get("possible_conditions", "")
        if possible_conditions:
            return f"Reported symptoms: {symptom_text}. Triage conclusion under review: {possible_conditions}."
        return f"Reported symptoms: {symptom_text}. Doctor review recommended."


_PIPELINE: TriagePipeline | None = None


def get_triage_pipeline() -> TriagePipeline:
    global _PIPELINE
    if _PIPELINE is None:
        _PIPELINE = TriagePipeline()
    return _PIPELINE
