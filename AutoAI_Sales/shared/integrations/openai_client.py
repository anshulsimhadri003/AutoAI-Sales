from __future__ import annotations

import logging

try:
    from openai import OpenAI
except Exception:  # pragma: no cover
    OpenAI = None

from shared.config.settings import get_settings

logger = logging.getLogger(__name__)


GENERIC_HELP_MESSAGES = {
    "what can you do",
    "how can you help",
    "how can you help me",
    "what services do you provide",
    "what do you do",
    "who are you",
    "help",
}
GREETING_MESSAGES = {"hi", "hello", "hey", "good morning", "good afternoon", "good evening"}
THANKS_MESSAGES = {"thanks", "thank you", "appreciate it", "thanks!", "thank you!"}


class OpenAIClient:
    def __init__(self):
        self.settings = get_settings()
        self.client = None
        if OpenAI and self.settings.enable_openai and self.settings.openai_api_key:
            self.client = OpenAI(api_key=self.settings.openai_api_key, timeout=self.settings.openai_timeout_seconds)

    def simple_text(self, prompt: str, max_output_tokens: int = 120) -> str:
        if not self.client:
            return ""
        try:
            response = self.client.responses.create(
                model=self.settings.openai_model,
                input=prompt,
                max_output_tokens=max_output_tokens,
            )
            return (response.output_text or "").strip()
        except Exception:
            logger.exception("OpenAI simple_text call failed")
            return ""

    def grounded_reply(self, context: dict) -> str:
        if not self.client:
            return self._grounded_fallback(context)
        try:
            response = self.client.responses.create(
                model=self.settings.openai_model,
                input=[
                    {
                        "role": "system",
                        "content": (
                            "You are a professional automotive dealership nurture agent. "
                            "Write a concise, helpful, human-sounding reply. "
                            "Ground the reply in the provided knowledge snippets, candidate responses, and message type. "
                            "Do not invent discounts, approvals, or unavailable inventory. "
                            "For greetings or generic capability questions, respond with a short overview of how you can help."
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            f"Dealership: {context['dealership_id']}\n"
                            f"Lead ID: {context['lead_id']}\n"
                            f"Intent label: {context.get('intent_label', 'general_help')}\n"
                            f"Urgency label: {context.get('urgency_label', 'Research Phase')}\n"
                            f"Message type: {context['message_type']}\n"
                            f"Customer message: {context['customer_message']}\n"
                            f"Knowledge snippets: {context.get('knowledge_snippets', [])}\n"
                            f"Candidate replies: {context['candidate_replies']}"
                        ),
                    },
                ],
                max_output_tokens=220,
            )
            text = (response.output_text or "").strip()
            return text or self._grounded_fallback(context)
        except Exception:
            logger.exception("OpenAI grounded_reply call failed, using fallback")
            return self._grounded_fallback(context)

    def _grounded_fallback(self, context: dict) -> str:
        message_type = context.get("message_type", "generic")
        intent_label = context.get("intent_label", "general_help")
        candidates = context.get("candidate_replies", [])
        snippets = context.get("knowledge_snippets", [])
        customer_message = (context.get("customer_message") or "").strip().lower()
        canonical_message = customer_message.rstrip("?.! ")

        if canonical_message in GREETING_MESSAGES or message_type == "greeting":
            return "Hi — I can help with vehicle availability, pricing, finance options, trade-ins, test drives, and appointments. What would you like help with today?"
        if canonical_message in THANKS_MESSAGES or message_type == "thanks":
            return "You're welcome. If you'd like, I can help with availability, pricing, finance options, or booking a test drive."
        if canonical_message in GENERIC_HELP_MESSAGES or message_type == "capability" or intent_label in {"capability", "general_help"}:
            return "I can help with vehicle availability, pricing, finance options, trade-ins, test drives, appointments, and dealership visits. Tell me what you'd like help with."
        if message_type == "opt_out":
            return "Understood — we will stop follow-up messages. If you need anything later, you can always reach out again."
        if message_type == "complex_question":
            return "Thanks for the detailed question. I am routing this to a sales specialist so you get an accurate response on all the points you raised."
        if message_type == "inventory_question":
            if snippets:
                return snippets[0]
            return "I can help check the latest availability and location for that vehicle. If you would like, I can also suggest similar available options."
        if message_type == "schedule_interest":
            return candidates[0] if candidates else "Absolutely — share your preferred day and time and I will help arrange the appointment."
        if message_type == "finance_question":
            return candidates[0] if candidates else "I can help with finance options and a quick pre-check. Let me know if you want monthly payment guidance or a callback."
        if intent_label == "trade_in":
            return candidates[0] if candidates else "I can help with the trade-in process and next steps. Share a few details about your current vehicle and I can guide you."
        if snippets:
            return snippets[0]
        return candidates[0] if candidates else "Thanks for your message. I can help with vehicle details, pricing, scheduling, or finance options. What would you like to do next?"
