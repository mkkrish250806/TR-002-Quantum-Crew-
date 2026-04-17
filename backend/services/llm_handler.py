from __future__ import annotations

import os
from typing import Literal

import httpx
from dotenv import load_dotenv

load_dotenv()


class LLMHandler:
    def __init__(self) -> None:
        self.provider: Literal["gemini", "claude", "groq"] = os.getenv("LLM_PROVIDER", "gemini").lower()  # type: ignore[assignment]
        self.gemini_model = os.getenv("GEMINI_MODEL", os.getenv("MEDICAL_LLM_MODEL", "gemini-2.0-flash"))
        self.claude_model = os.getenv(
            "CLAUDE_MODEL",
            os.getenv("MEDICAL_LLM_MODEL", "claude-3-5-haiku-latest"),
        )
        self.groq_model = os.getenv(
            "GROQ_MODEL",
            os.getenv("MEDICAL_LLM_MODEL", "llama-3.3-70b-versatile"),
        )
        self.max_tokens = int(os.getenv("LLM_MAX_TOKENS", "700"))

    def generate(
        self,
        user_query: str,
        conversation_context: str,
        patient_profile: dict[str, str],
        intent: str,
        urgency: str,
        emotion: str,
        icd_matches: list[dict] | None = None,
    ) -> str:
        prompt = self._build_prompt(
            user_query=user_query,
            conversation_context=conversation_context,
            patient_profile=patient_profile,
            intent=intent,
            urgency=urgency,
            emotion=emotion,
            icd_matches=icd_matches,
        )

        if self.provider == "claude":
            return self._call_claude(prompt, intent, urgency)
        if self.provider == "groq":
            return self._call_groq(prompt, intent, urgency)
        return self._call_gemini(prompt, intent, urgency)

    def generate_disease_prediction(
        self,
        known_symptoms: list[str],
        icd_matches: list[dict],
        patient_profile: dict[str, str],
        urgency: str,
    ) -> str:
        """Generate structured ICD-based disease prediction."""
        if not icd_matches:
            return "Insufficient symptom data to generate a disease prediction at this time."

        icd_block = self._format_icd_matches(icd_matches)

        prompt = f"""You are a clinical decision support AI assisting hospital triage staff.
Based on the patient's reported symptoms and ICD-10 matched conditions below, produce a structured disease prediction.

Rules:
- Do NOT claim to diagnose. Use phrases like "consistent with", "may indicate", "possible", "likely".
- Reference ICD-10 codes explicitly in your response.
- Rank predictions from most to least likely based on symptom overlap score.
- Include a confidence level: High (>70% match), Moderate (40-70%), Low (<40%).
- If urgency is high, add a clear emergency note at the top.
- End with recommended specialist department.
- Keep the response under 200 words.

Patient symptoms: {", ".join(known_symptoms) or "Not specified"}
Urgency level: {urgency}
Patient profile:
{self._format_profile(patient_profile)}

ICD-10 Matched Conditions:
{icd_block}

Output format:
🔍 Disease Prediction Summary
[If urgent: ⚠️ URGENT: ...]

1. [Disease Name] (ICD-10: [code]) — [High/Moderate/Low] Confidence
   Matched symptoms: [list]
   Assessment: [1 sentence]

2. ...

🏥 Recommended Department: [department]
📋 Note: This is a clinical support tool. A licensed physician must confirm any diagnosis.
"""
        if self.provider == "claude":
            return self._call_claude(prompt, "disease_prediction", urgency)
        if self.provider == "groq":
            return self._call_groq(prompt, "disease_prediction", urgency)
        return self._call_gemini(prompt, "disease_prediction", urgency)

    def summarize_for_report(
        self,
        conversation_context: str,
        patient_profile: dict[str, str],
        icd_matches: list[dict] | None = None,
    ) -> str:
        icd_section = ""
        if icd_matches:
            icd_section = f"\nICD-10 Matched Conditions:\n{self._format_icd_matches(icd_matches)}"

        prompt = f"""You are preparing a structured doctor-style patient summary from a hospital chatbot conversation.
Do not diagnose. Do not invent missing facts.
Use plain, professional clinical wording.
Include ICD-10 codes where conditions are referenced.
Return only these exact headings, each on its own line with no markdown symbols:
Patient Name:
Reported Symptoms:
ICD-10 Differential:
Clinical Conclusion:
Recommended Next Steps:

Patient profile:
{self._format_profile(patient_profile)}
{icd_section}

Conversation:
{conversation_context}
""".strip()

        if self.provider == "claude":
            return self._call_claude(prompt, "report", "low")
        if self.provider == "groq":
            return self._call_groq(prompt, "report", "low")
        return self._call_gemini(prompt, "report", "low")

    def generate_triage_question(
        self,
        user_message: str,
        known_symptoms: list[str],
        possible_conditions: list[str],
        conversation_context: str,
        suggested_questions: list[str],
        urgency: str,
        icd_matches: list[dict] | None = None,
    ) -> str:
        icd_detail = ""
        if icd_matches:
            top = icd_matches[0]
            missing = top.get("missing_symptoms", [])
            if missing:
                icd_detail = f"\nTop ICD-10 match missing symptoms: {', '.join(missing[:3])}"

        prompt = f"""You are a medical symptom collection assistant at hospital triage.
Your job is to ask one follow-up question at a time based on ICD-10 matched conditions.

Strict rules:
- Do not diagnose or claim the patient has a disease.
- Ask exactly one question.
- Prioritize asking about missing symptoms from the top ICD-10 matched condition.
- Focus on missing symptom details, duration, severity, type, or associated symptoms.
- Sound like a hospital triage nurse.
- If symptoms seem urgent, keep the question short and safety-aware.

Known symptoms: {", ".join(known_symptoms) or "None yet"}

ICD-10 conditions under review:
{", ".join(possible_conditions) or "General symptom review"}
{icd_detail}

Recent conversation:
{conversation_context or "No previous context."}

Latest patient message:
{user_message}

Suggested next questions:
{chr(10).join(f"- {question}" for question in suggested_questions)}

Urgency: {urgency}
""".strip()

        if self.provider == "claude":
            answer = self._call_claude(prompt, "symptom_triage", urgency)
        elif self.provider == "groq":
            answer = self._call_groq(prompt, "symptom_triage", urgency)
        else:
            answer = self._call_gemini(prompt, "symptom_triage", urgency)

        cleaned = " ".join(answer.split())
        if cleaned and cleaned.endswith("?"):
            return cleaned
        if cleaned:
            return f"{cleaned.rstrip('.')}?"
        return suggested_questions[0] if suggested_questions else "How long have you been having these symptoms?"

    @staticmethod
    def _format_icd_matches(icd_matches: list[dict]) -> str:
        lines = []
        for i, match in enumerate(icd_matches[:3], 1):
            score = match.get("score", 0)
            if score >= 0.7:
                confidence = "High"
            elif score >= 0.4:
                confidence = "Moderate"
            else:
                confidence = "Low"
            lines.append(
                f"{i}. {match.get('disease', 'Unknown')} (ICD-10: {match.get('code', 'N/A')}) "
                f"[{confidence} Confidence, score: {score}]\n"
                f"   Matched: {', '.join(match.get('matched_symptoms', []))}\n"
                f"   Missing: {', '.join(match.get('missing_symptoms', [])[:3]) or 'None'}\n"
                f"   Department: {match.get('department', 'General Medicine')}"
            )
        return "\n".join(lines)

    @staticmethod
    def _format_profile(patient_profile: dict[str, str]) -> str:
        if not patient_profile:
            return "No patient profile details captured."
        return "\n".join(f"- {key.replace('_', ' ').title()}: {value}" for key, value in patient_profile.items())

    def _build_prompt(
        self,
        user_query: str,
        conversation_context: str,
        patient_profile: dict[str, str],
        intent: str,
        urgency: str,
        emotion: str,
        icd_matches: list[dict] | None = None,
    ) -> str:
        icd_section = ""
        if icd_matches:
            icd_section = f"""
ICD-10 Clinical Context:
{self._format_icd_matches(icd_matches)}

When responding about symptoms or health concerns:
- Reference the relevant ICD-10 codes and conditions above.
- Provide disease prediction guidance based on symptom overlap.
- Use phrases like "consistent with", "may indicate", "possible".
- Mention the confidence level (High/Moderate/Low) for each condition.
"""

        return f"""You are MediAssist, an AI hospital support assistant powered by ICD-10 clinical knowledge.
Your tone should feel like a calm hospital front-desk and clinical support team member.

Rules:
- Use medically appropriate, reassuring, and professional hospital wording.
- Do not claim to be a doctor and do not provide a definitive diagnosis.
- Reference ICD-10 codes when discussing possible conditions (e.g., "ICD-10: J06.9 - Acute upper respiratory infection").
- When symptoms are discussed, provide structured disease prediction based on ICD-10 matches.
- If symptoms sound urgent, clearly tell the patient to seek immediate in-person care.
- Help with appointments, billing, lab report explanation, patient intake details, and next steps.
- If information is missing, ask one focused follow-up question instead of making assumptions.
- Keep responses concise, organized, and patient-friendly.
- Use the patient's name only occasionally and naturally.
- Do not begin every reply with the patient's name or with a greeting.
- When appropriate, briefly mention the likely hospital department or service area.
- When useful, end with one clear next action for the patient.
{icd_section}
Conversation intent: {intent}
Urgency: {urgency}
Detected emotion: {emotion}

Patient profile:
{self._format_profile(patient_profile)}

Recent conversation:
{conversation_context or "No recent context available."}

Latest user message:
{user_query}
""".strip()

    def _call_gemini(self, prompt: str, intent: str, urgency: str) -> str:
        api_key = (os.getenv("GEMINI_API_KEY") or "").strip().strip("'\"")
        if not api_key:
            print("Gemini API key is missing. Falling back to template response.")
            return self._fallback_response(intent, urgency)

        try:
            import google.generativeai as genai

            genai.configure(api_key=api_key)
            model = genai.GenerativeModel(self.gemini_model)
            response = model.generate_content(
                prompt,
                generation_config={"temperature": 0.2, "max_output_tokens": self.max_tokens},
            )
            text = (response.text or "").strip()
            return text if text else self._fallback_response(intent, urgency)
        except Exception as exc:
            print(f"Gemini generation failed: {exc}")
            return self._fallback_response(intent, urgency)

    def _call_claude(self, prompt: str, intent: str, urgency: str) -> str:
        api_key = (os.getenv("ANTHROPIC_API_KEY") or "").strip().strip("'\"")
        if not api_key:
            print("Anthropic API key is missing. Falling back to template response.")
            return self._fallback_response(intent, urgency)

        try:
            from anthropic import Anthropic

            client = Anthropic(api_key=api_key)
            message = client.messages.create(
                model=self.claude_model,
                max_tokens=self.max_tokens,
                temperature=0.2,
                messages=[{"role": "user", "content": prompt}],
            )
            answer = "".join(getattr(block, "text", "") for block in message.content).strip()
            return answer if answer else self._fallback_response(intent, urgency)
        except Exception as exc:
            print(f"Claude generation failed: {exc}")
            return self._fallback_response(intent, urgency)

    def _call_groq(self, prompt: str, intent: str, urgency: str) -> str:
        api_key = (os.getenv("GROQ_API_KEY") or "").strip().strip("'\"")
        if not api_key:
            print("Groq API key is missing. Falling back to template response.")
            return self._fallback_response(intent, urgency)

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.groq_model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
            "max_tokens": self.max_tokens,
        }

        try:
            response = httpx.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=30.0,
            )
            response.raise_for_status()
            data = response.json()
            choices = data.get("choices", [])
            if not choices:
                return self._fallback_response(intent, urgency)
            answer = (
                choices[0].get("message", {}).get("content", "").strip()
                if isinstance(choices[0], dict)
                else ""
            )
            return answer if answer else self._fallback_response(intent, urgency)
        except Exception as exc:
            print(f"Groq generation failed: {exc}")
            return self._fallback_response(intent, urgency)

    @staticmethod
    def _fallback_response(intent: str, urgency: str) -> str:
        if urgency == "high":
            return (
                "Your symptoms could be serious. Please seek urgent in-person medical care or contact emergency services right away."
            )
        if intent == "disease_prediction":
            return (
                "Based on the reported symptoms, a clinical assessment is recommended. "
                "Please consult a physician for an ICD-10 based diagnosis."
            )
        if intent == "appointment":
            return (
                "I can help arrange your hospital appointment. "
                "Please tell me your preferred department, date, or time slot."
            )
        if intent == "lab_report":
            return (
                "I can help explain the report in general terms. "
                "Please share the test name and value, and I will summarize what it usually means."
            )
        if intent == "billing":
            return (
                "I can help with hospital billing support. "
                "Please share the charge, invoice, or payment issue you want reviewed."
            )
        if intent == "report":
            return (
                "Patient Name:\nPatient\n"
                "Reported Symptoms:\nSymptoms were discussed during the chat and should be reviewed with the conversation history.\n"
                "ICD-10 Differential:\nRequires physician review.\n"
                "Clinical Conclusion:\nThis summary reflects reported symptoms only and is not a confirmed diagnosis.\n"
                "Recommended Next Steps:\nArrange doctor review, continue symptom monitoring, and seek urgent care if symptoms worsen."
            )
        if intent == "symptom_triage":
            return "How long have you been having these symptoms?"
        return (
            "To help you properly, please share your main symptom or support request and how long it has been happening."
        )
