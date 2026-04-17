from __future__ import annotations

from datetime import datetime
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas

from services.llm_handler import LLMHandler


class ReportGenerator:
    def __init__(self) -> None:
        self.llm = LLMHandler()

    def build_pdf(self, session_payload: dict) -> bytes:
        profile = session_payload.get("profile", {})
        messages = session_payload.get("messages", [])
        session_id = session_payload.get("session_id", "unknown-session")
        conversation_text = self._conversation_text(messages)
        summary = self.llm.summarize_for_report(
            conversation_context=conversation_text,
            patient_profile=profile,
        )

        buffer = BytesIO()
        pdf = canvas.Canvas(buffer, pagesize=A4)
        width, height = A4
        margin = 16 * mm
        content_width = width - (margin * 2)
        y = height - margin

        def ensure_space(required_height: float) -> None:
            nonlocal y
            if y - required_height < margin:
                pdf.showPage()
                self._draw_page_background(pdf, width, height)
                y = height - margin

        self._draw_page_background(pdf, width, height)
        pdf.setTitle(f"Hospital Patient Support Report - {session_id}")

        header_height = 34 * mm
        ensure_space(header_height)
        self._draw_header(pdf, margin, y - header_height, content_width, header_height, session_id)
        y -= header_height + 8 * mm

        patient_lines = self._patient_lines(profile)
        patient_height = self._estimate_card_height(patient_lines, content_width, body_size=10.5, title_gap=18)
        ensure_space(patient_height)
        self._draw_card(
            pdf,
            x=margin,
            y_bottom=y - patient_height,
            width=content_width,
            height=patient_height,
            title="Patient Information",
            lines=patient_lines,
            title_color=colors.HexColor("#0f3b57"),
        )
        y -= patient_height + 6 * mm

        summary_sections = self._summary_sections(summary, messages, profile)
        summary_height = self._estimate_summary_height(summary_sections, content_width)
        ensure_space(summary_height)
        self._draw_summary_card(
            pdf,
            x=margin,
            y_bottom=y - summary_height,
            width=content_width,
            height=summary_height,
            title="Clinical Support Summary",
            sections=summary_sections,
        )

        pdf.save()
        buffer.seek(0)
        return buffer.getvalue()

    def _draw_page_background(self, pdf: canvas.Canvas, width: float, height: float) -> None:
        pdf.setFillColor(colors.HexColor("#f7fbff"))
        pdf.rect(0, 0, width, height, fill=1, stroke=0)
        pdf.setStrokeColor(colors.HexColor("#d6e4f0"))
        pdf.setLineWidth(1)
        pdf.rect(10 * mm, 10 * mm, width - 20 * mm, height - 20 * mm, fill=0, stroke=1)

    def _draw_header(
        self,
        pdf: canvas.Canvas,
        x: float,
        y_bottom: float,
        width: float,
        height: float,
        session_id: str,
    ) -> None:
        pdf.setFillColor(colors.HexColor("#10324a"))
        pdf.roundRect(x, y_bottom, width, height, 10, fill=1, stroke=0)

        pdf.setFillColor(colors.white)
        pdf.setFont("Helvetica-Bold", 18)
        pdf.drawString(x + 10 * mm, y_bottom + height - 11 * mm, "MediAssist Hospital Support Report")

        pdf.setFont("Helvetica", 10.5)
        pdf.drawString(
            x + 10 * mm,
            y_bottom + height - 18 * mm,
            f"Generated On: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        )
        pdf.drawString(x + 10 * mm, y_bottom + height - 24 * mm, f"Session Reference: {session_id}")

    def _draw_card(
        self,
        pdf: canvas.Canvas,
        x: float,
        y_bottom: float,
        width: float,
        height: float,
        title: str,
        lines: list[str],
        title_color,
    ) -> None:
        pdf.setFillColor(colors.white)
        pdf.setStrokeColor(colors.HexColor("#c8d9e8"))
        pdf.setLineWidth(1)
        pdf.roundRect(x, y_bottom, width, height, 8, fill=1, stroke=1)

        title_y = y_bottom + height - 11 * mm
        pdf.setFillColor(title_color)
        pdf.setFont("Helvetica-Bold", 13)
        pdf.drawString(x + 8 * mm, title_y, title)

        current_y = title_y - 7 * mm
        for line in lines:
            wrapped = self._wrap_text(line, width - 16 * mm, "Helvetica", 10.5)
            pdf.setFillColor(colors.HexColor("#22313f"))
            pdf.setFont("Helvetica", 10.5)
            for wrapped_line in wrapped:
                pdf.drawString(x + 8 * mm, current_y, wrapped_line)
                current_y -= 5.3 * mm

    def _draw_summary_card(
        self,
        pdf: canvas.Canvas,
        x: float,
        y_bottom: float,
        width: float,
        height: float,
        title: str,
        sections: list[tuple[str, list[str]]],
    ) -> None:
        pdf.setFillColor(colors.white)
        pdf.setStrokeColor(colors.HexColor("#c8d9e8"))
        pdf.setLineWidth(1)
        pdf.roundRect(x, y_bottom, width, height, 8, fill=1, stroke=1)

        title_y = y_bottom + height - 11 * mm
        pdf.setFillColor(colors.HexColor("#0f3b57"))
        pdf.setFont("Helvetica-Bold", 13)
        pdf.drawString(x + 8 * mm, title_y, title)

        current_y = title_y - 8 * mm
        for heading, body_lines in sections:
            pdf.setFillColor(colors.HexColor("#176087"))
            pdf.setFont("Helvetica-Bold", 11)
            pdf.drawString(x + 8 * mm, current_y, heading)
            current_y -= 6 * mm

            pdf.setFillColor(colors.HexColor("#22313f"))
            pdf.setFont("Helvetica", 10.5)
            for line in body_lines:
                wrapped = self._wrap_text(line, width - 18 * mm, "Helvetica", 10.5)
                for wrapped_line in wrapped:
                    pdf.drawString(x + 10 * mm, current_y, wrapped_line)
                    current_y -= 5.3 * mm
            current_y -= 2 * mm

    @staticmethod
    def _format_label(key: str) -> str:
        mapping = {
            "name": "Patient Name",
            "last_intent": "Last Support Topic",
            "last_seen": "Last Interaction Time",
            "last_department": "Last Suggested Department",
            "last_booking_id": "Last Booking ID",
            "booking_pending": "Booking Pending",
        }
        return mapping.get(key, key.replace("_", " ").title())

    def _patient_lines(self, profile: dict) -> list[str]:
        if not profile:
            return ["No patient profile details captured."]

        lines: list[str] = []
        for key, value in profile.items():
            if not value:
                continue
            lines.append(f"{self._format_label(key)}: {value}")
        return lines or ["No patient profile details captured."]

    @staticmethod
    def _conversation_text(messages: list[dict[str, str]]) -> str:
        if not messages:
            return "No conversation available."
        return "\n".join(
            f"{message.get('role', 'unknown')}: {message.get('content', '').strip()}"
            for message in messages
        )

    @staticmethod
    def _clean_summary(summary: str) -> list[str]:
        cleaned_lines: list[str] = []
        for raw_line in summary.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            line = line.replace("**", "")
            if line.startswith("- "):
                line = line[2:]
            cleaned_lines.append(line)
        return cleaned_lines

    def _summary_sections(
        self,
        summary: str,
        messages: list[dict[str, str]],
        profile: dict[str, str],
    ) -> list[tuple[str, list[str]]]:
        cleaned = self._clean_summary(summary)
        sections: list[tuple[str, list[str]]] = []
        current_heading = "Summary"
        current_body: list[str] = []

        for line in cleaned:
            if line.endswith(":"):
                if current_body:
                    sections.append((current_heading, current_body))
                current_heading = line[:-1]
                current_body = []
            else:
                current_body.append(line)

        if current_body:
            sections.append((current_heading, current_body))

        merged = {heading: body[:] for heading, body in sections}
        reported_symptoms = self._reported_symptom_lines(messages, profile)
        if reported_symptoms:
            existing = merged.get("Reported Symptoms", [])
            if self._is_generic_symptom_section(existing):
                merged["Reported Symptoms"] = reported_symptoms
            elif existing:
                merged["Reported Symptoms"] = existing + reported_symptoms

        if not merged:
            return [("Summary", ["No summary details available."])]

        preferred_order = [
            "Patient Name",
            "Reported Symptoms",
            "ICD-10 Differential",
            "Clinical Conclusion",
            "Recommended Next Steps",
            "Summary",
        ]
        ordered_sections: list[tuple[str, list[str]]] = []
        for heading in preferred_order:
            body = merged.pop(heading, None)
            if body:
                ordered_sections.append((heading, body))
        for heading, body in merged.items():
            if body:
                ordered_sections.append((heading, body))
        return ordered_sections

    def _reported_symptom_lines(
        self,
        messages: list[dict[str, str]],
        profile: dict[str, str],
    ) -> list[str]:
        patient_name = str(profile.get("name", "")).strip().lower()
        symptom_texts: list[str] = []

        for message in messages:
            if message.get("role") != "user":
                continue
            content = " ".join(str(message.get("content", "")).strip().split())
            if not content:
                continue
            lowered = content.lower()
            if patient_name and lowered in {f"i am {patient_name}", f"my name is {patient_name}", patient_name}:
                continue
            if self._is_booking_message(lowered):
                continue
            symptom_texts.append(content)

        if not symptom_texts:
            return []

        bullet_lines: list[str] = []
        for text in symptom_texts[:4]:
            bullet_lines.append(f"Patient reported: {text}")
        return bullet_lines

    @staticmethod
    def _is_generic_symptom_section(lines: list[str]) -> bool:
        if not lines:
            return True
        generic_markers = (
            "symptoms were discussed during the chat",
            "should be reviewed with the conversation history",
            "not specified",
            "no symptom details available",
        )
        joined = " ".join(lines).lower()
        return any(marker in joined for marker in generic_markers)

    @staticmethod
    def _is_booking_message(message: str) -> bool:
        booking_markers = (
            "book",
            "booking",
            "appointment",
            "slot",
            "confirm",
            "schedule",
            "reserve",
        )
        return any(marker in message for marker in booking_markers)

    def _estimate_card_height(
        self,
        lines: list[str],
        width: float,
        body_size: float = 10.5,
        title_gap: float = 18,
    ) -> float:
        total_lines = 0
        for line in lines:
            total_lines += max(1, len(self._wrap_text(line, width - 16 * mm, "Helvetica", body_size)))
        return max(30 * mm, (title_gap + (total_lines * 5.3 * mm) + 8 * mm))

    def _estimate_summary_height(self, sections: list[tuple[str, list[str]]], width: float) -> float:
        total = 16 * mm
        for heading, body_lines in sections:
            total += 7 * mm
            for line in body_lines:
                wrapped = self._wrap_text(line, width - 18 * mm, "Helvetica", 10.5)
                total += max(1, len(wrapped)) * 5.3 * mm
            total += 2 * mm
        return max(55 * mm, total)

    @staticmethod
    def _wrap_text(text: str, max_width: float, font: str, size: float) -> list[str]:
        words = text.split()
        if not words:
            return [""]

        lines: list[str] = []
        current = words[0]
        for word in words[1:]:
            candidate = f"{current} {word}"
            if stringWidth(candidate, font, size) <= max_width:
                current = candidate
            else:
                lines.append(current)
                current = word
        lines.append(current)
        return lines
