from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from threading import Lock

from services.appointment import AppointmentService
from services.embeddings import EmbeddingService
from services.intent import classify_intent
from services.llm_handler import LLMHandler
from services.sentiment import detect_emotion, tone_prefix
from services.triage import detect_urgency, map_department, mock_slots
from services.vector_store import VectorStore


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
        kb_path = Path(__file__).resolve().parent.parent / "data" / "knowledge_base.json"
        self.embedding_service = EmbeddingService("all-MiniLM-L6-v2")
        self.vector_store = VectorStore(str(kb_path), self.embedding_service)
        self.llm = LLMHandler()
        self.appointment_service = AppointmentService()
        self.analytics = Analytics()
        self.sessions: dict[str, list[dict[str, str]]] = {}
        self.profiles: dict[str, dict[str, str]] = {}
        self.confidence_threshold = float(os.getenv("CONFIDENCE_THRESHOLD", "0.7"))

    def _session_context(self, session_id: str) -> str:
        memory = self.sessions.get(session_id, [])[-5:]
        if not memory:
            return ""
        return "\n".join([f"{m['role']}: {m['content']}" for m in memory[-5:]])

    def _save_session_turn(self, session_id: str, user_message: str, bot_message: str) -> None:
        self.sessions.setdefault(session_id, [])
        self.sessions[session_id].append({"role": "user", "content": user_message})
        self.sessions[session_id].append({"role": "assistant", "content": bot_message})
        self.sessions[session_id] = self.sessions[session_id][-10:]

    @staticmethod
    def _extract_name(message: str) -> str | None:
        patterns = [
            r"\bmy name is ([a-zA-Z][a-zA-Z\s]{1,40})\b",
            r"\bthis is ([a-zA-Z][a-zA-Z\s]{1,40})\b",
        ]
        text = message.strip()
        for pattern in patterns:
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if match:
                candidate = match.group(1).strip(" .,!?")
                if len(candidate.split()) <= 3:
                    return " ".join([w.capitalize() for w in candidate.split()])
        return None

    @staticmethod
    def _is_name_only_message(message: str) -> bool:
        text = message.strip().lower()
        prefixes = ["my name is ", "this is "]
        return any(text.startswith(prefix) for prefix in prefixes)

    def _profile(self, session_id: str) -> dict[str, str]:
        return self.profiles.setdefault(session_id, {})

    @staticmethod
    def _is_slot_selection_message(message: str, slot: str | None) -> bool:
        if not slot:
            return False
        text = message.lower().strip()
        booking_terms = ["select", "choose", "confirm", "book", "reserve", "slot"]
        if any(term in text for term in booking_terms):
            return True
        return len(text.split()) <= 5

    @staticmethod
    def _extract_lab_values(message: str) -> dict[str, float]:
        patterns = {
            "hemoglobin": r"(?:hemoglobin|hb)\s*[:=]?\s*(\d+\.?\d*)",
            "fasting_glucose": r"(?:fasting sugar|fasting glucose|fbs)\s*[:=]?\s*(\d+\.?\d*)",
            "random_glucose": r"(?:random sugar|random glucose|rbs)\s*[:=]?\s*(\d+\.?\d*)",
        }
        found: dict[str, float] = {}
        text = message.lower()
        for key, pattern in patterns.items():
            match = re.search(pattern, text)
            if match:
                found[key] = float(match.group(1))
        return found

    @staticmethod
    def _lab_explanation(values: dict[str, float]) -> str:
        if not values:
            return ""
        parts: list[str] = []
        hb = values.get("hemoglobin")
        if hb is not None:
            if hb < 12.0:
                parts.append(f"Hemoglobin {hb} g/dL looks below common adult reference ranges.")
            else:
                parts.append(f"Hemoglobin {hb} g/dL appears within common adult reference ranges.")
        fasting = values.get("fasting_glucose")
        if fasting is not None:
            if fasting >= 126:
                parts.append(f"Fasting glucose {fasting} mg/dL is above typical normal range.")
            elif fasting >= 100:
                parts.append(f"Fasting glucose {fasting} mg/dL is mildly elevated.")
            else:
                parts.append(f"Fasting glucose {fasting} mg/dL is typically considered normal.")
        random_val = values.get("random_glucose")
        if random_val is not None:
            if random_val >= 200:
                parts.append(f"Random glucose {random_val} mg/dL is elevated.")
            else:
                parts.append(f"Random glucose {random_val} mg/dL is not markedly elevated.")
        return " ".join(parts)

    @staticmethod
    def _extract_body_terms(message: str) -> set[str]:
        body_terms = [
            "chest",
            "shoulder",
            "leg",
            "arm",
            "head",
            "back",
            "stomach",
            "abdomen",
            "throat",
            "ear",
            "eye",
            "knee",
        ]
        text = message.lower()
        return {term for term in body_terms if term in text}

    def _refine_symptom_retrieval(self, message: str, retrieved: list[dict]) -> list[dict]:
        query_terms = self._extract_body_terms(message)
        if not query_terms:
            return retrieved

        matched = [
            doc
            for doc in retrieved
            if any(term in doc["text"].lower() or term in doc["title"].lower() for term in query_terms)
        ]
        if matched:
            return matched

        # Guardrail: avoid chest-specific advice for non-chest symptom queries.
        text = message.lower()
        if "chest" not in text:
            filtered = [
                doc
                for doc in retrieved
                if "chest" not in doc["text"].lower() and "chest" not in doc["title"].lower()
            ]
            if filtered:
                return filtered

        return retrieved

    def handle_query(self, message: str, session_id: str) -> dict:
        intent = classify_intent(message)
        emotion = detect_emotion(message)
        urgency = detect_urgency(message)
        memory_context = self._session_context(session_id)
        profile = self._profile(session_id)
        booking_status = "none"
        booking_id = ""
        booked_slot = ""
        booked_department = ""

        extracted_name = self._extract_name(message)
        if extracted_name:
            profile["name"] = extracted_name

        if extracted_name and self._is_name_only_message(message):
            answer = (
                f"Nice to meet you, {extracted_name}. "
                "I can help with appointments, billing, lab reports, and symptom triage."
            )
            answer = f"{tone_prefix(emotion, urgency)}{answer}"
            self.analytics.update(resolved=True, emergency=False)
            self._save_session_turn(session_id=session_id, user_message=message, bot_message=answer)
            return {
                "answer": answer,
                "intent": "faq",
                "confidence": 1.0,
                "urgency": "low",
                "emotion": emotion,
                "resolved": True,
                "sources": [],
                "booking_status": "none",
                "booking_id": "",
                "booked_slot": "",
                "booked_department": "",
                "patient_name": extracted_name,
            }

        # Booking-first path for direct slot selection (clean response, no unrelated RAG context).
        slot_in_message = self.appointment_service.extract_slot(message)
        booking_pending = profile.get("booking_pending") == "1"
        slot_selection = self._is_slot_selection_message(message, slot_in_message)
        has_department_context = bool(profile.get("last_department"))
        if slot_selection and (booking_pending or has_department_context):
            department = profile.get("last_department") or map_department(message)
            booking = self.appointment_service.book(
                session_id=session_id,
                patient_name=profile.get("name", "Patient"),
                department=department,
                slot=slot_in_message or "",
            )
            booking_status = "confirmed" if booking["success"] else "failed"
            booking_id = str(booking["booking_id"] or "") if booking["success"] else ""
            booked_slot = str(booking["slot"] or "") if booking["success"] else ""
            booked_department = str(booking["department"] or department)
            profile["booking_pending"] = "0" if booking["success"] else "1"
            if booking["success"] and booking_id:
                profile["last_booking_id"] = booking_id

            personal_prefix = f"{profile['name']}, " if "name" in profile else ""
            answer = f"{personal_prefix}{tone_prefix(emotion, urgency)}{booking['message']}"
            self.analytics.update(resolved=booking["success"], emergency=False)
            self._save_session_turn(session_id=session_id, user_message=message, bot_message=answer)
            return {
                "answer": answer,
                "intent": "appointment",
                "confidence": 1.0 if booking["success"] else 0.4,
                "urgency": "low",
                "emotion": emotion,
                "resolved": bool(booking["success"]),
                "sources": [],
                "booking_status": booking_status,
                "booking_id": booking_id,
                "booked_slot": booked_slot,
                "booked_department": booked_department,
                "patient_name": profile.get("name", ""),
            }

        # Keep retrieval focused on the current query to avoid stale context bleed-over.
        retrieved = self.vector_store.search(message, top_k=3)
        if intent == "symptom":
            retrieved = self._refine_symptom_retrieval(message, retrieved)
        context_blocks = [f"[{d['title']}] {d['text']}" for d in retrieved]
        if memory_context:
            context_blocks.append(f"[Recent Conversation]\n{memory_context}")
        context = "\n".join(context_blocks)
        avg_similarity = sum(d["similarity"] for d in retrieved) / len(retrieved) if retrieved else 0.0

        answer = self.llm.generate(user_query=message, context=context)

        if intent == "appointment" or (intent == "symptom" and urgency != "high"):
            department = map_department(message)
            profile["last_department"] = department
            live_slots = self.appointment_service.get_available_slots(department)
            slots = ", ".join(live_slots if live_slots else mock_slots(department))
            answer += f"\nSuggested department: {department}. Available slots: {slots}."

        wants_booking = self.appointment_service.wants_booking(message)
        slot_in_message = self.appointment_service.extract_slot(message)
        booking_pending = profile.get("booking_pending") == "1"
        if slot_in_message and (intent == "appointment" or booking_pending):
            wants_booking = True
        if wants_booking:
            slot = slot_in_message
            department = profile.get("last_department") or map_department(message)
            profile["last_department"] = department
            if slot is None:
                available = self.appointment_service.get_available_slots(department)
                slot_msg = ", ".join(available if available else mock_slots(department))
                answer += (
                    f"\nTo confirm booking, please share one slot exactly as shown: {slot_msg}."
                )
                booking_status = "pending_slot"
                profile["booking_pending"] = "1"
            else:
                booking = self.appointment_service.book(
                    session_id=session_id,
                    patient_name=profile.get("name", "Patient"),
                    department=department,
                    slot=slot,
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

        if intent == "lab_report":
            values = self._extract_lab_values(message)
            lab_note = self._lab_explanation(values)
            if lab_note:
                answer += f"\n{lab_note}"

        if urgency == "high":
            answer += (
                "\nYour symptoms may need urgent attention. "
                "Please seek immediate in-person medical care or emergency services."
            )

        profile["last_intent"] = intent
        profile["last_seen"] = datetime.now().isoformat(timespec="seconds")

        personal_prefix = ""
        if "name" in profile:
            personal_prefix = f"{profile['name']}, "
        answer = f"{personal_prefix}{tone_prefix(emotion, urgency)}{answer}"

        insufficient_context = "could not find enough information" in answer.lower()
        resolved = bool((avg_similarity > self.confidence_threshold) and not insufficient_context)

        self.analytics.update(resolved=resolved, emergency=(urgency == "high"))
        self._save_session_turn(session_id=session_id, user_message=message, bot_message=answer)

        return {
            "answer": answer,
            "intent": intent,
            "confidence": round(avg_similarity, 3),
            "urgency": urgency,
            "emotion": emotion,
            "resolved": resolved,
            "sources": [doc["title"] for doc in retrieved],
            "booking_status": booking_status,
            "booking_id": booking_id,
            "booked_slot": booked_slot,
            "booked_department": booked_department,
            "patient_name": profile.get("name", ""),
        }

    def get_metrics(self) -> dict:
        return self.analytics.snapshot()


_PIPELINE: RAGPipeline | None = None


def get_rag_pipeline() -> RAGPipeline:
    global _PIPELINE
    if _PIPELINE is None:
        _PIPELINE = RAGPipeline()
    return _PIPELINE
