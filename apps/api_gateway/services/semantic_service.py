from __future__ import annotations

from functools import lru_cache

from shared.bootstrap.config_cache import get_config_cache
from shared.integrations.embedding_client import EmbeddingClient
from apps.api_gateway.services.hybrid_search import HybridDocument, HybridSearchIndex


MESSAGE_TYPE_PROTOTYPES = {
    "opt_out": [
        "Stop messaging me",
        "Unsubscribe me from your updates",
        "Do not contact me again",
        "Remove me from your list",
    ],
    "schedule_interest": [
        "I want to come tomorrow for a test drive",
        "Can you book an appointment for this weekend",
        "Please schedule a visit",
        "I want the next available test drive slot",
    ],
    "finance_question": [
        "What is the EMI",
        "Can I get finance approval",
        "Tell me about loan options",
        "What would the monthly payment be",
    ],
    "inventory_question": [
        "Is the car still available",
        "Where is the vehicle located",
        "Has this car been sold",
        "Do you still have this in stock",
    ],
    "complex_question": [
        "Compare this model with another one and explain resale, safety, and maintenance",
        "I have multiple questions about pricing, exchange, booking, and documents",
        "Can you walk me through warranty, trade in, taxes, and fees",
    ],
    "objection": [
        "This is outside my budget",
        "I am not convinced yet",
        "The price is too high for me",
        "I need to think about it",
    ],
    "greeting": ["Hi", "Hello", "Hey there", "Good morning", "Good afternoon"],
    "capability": [
        "What can you do",
        "How can you help me",
        "What services do you provide",
        "Who are you",
        "Help",
    ],
    "thanks": ["Thanks", "Thank you", "Appreciate it", "Thanks for the information"],
    "acknowledgement": ["Okay sounds good", "Got it", "Understood", "That works"],
    "generic": ["Please share more details", "Can you tell me more", "I need some information", "Can you assist me"],
}

INTENT_THRESHOLDS = {"default": 0.36, "capability": 0.32, "greeting": 0.32}
URGENCY_THRESHOLD = 0.30
MESSAGE_TYPE_THRESHOLD = 0.34


class SemanticService:
    def __init__(self):
        self.embedder = EmbeddingClient()
        self.config = get_config_cache()
        self.intent_index = self._build_label_index(self.config.intent_prototypes, "intent")
        self.urgency_index = self._build_label_index(self.config.urgency_prototypes, "urgency")
        self.message_type_index = self._build_label_index(MESSAGE_TYPE_PROTOTYPES, "message_type")
        self.reply_templates = self._build_reply_template_items()
        self.reply_index = HybridSearchIndex("reply_templates", self.reply_templates, embedding_client=self.embedder)
        self.knowledge_items = self._build_knowledge_items()
        self.knowledge_index = HybridSearchIndex("knowledge", self.knowledge_items, embedding_client=self.embedder)
        self.pair_index = HybridSearchIndex("pairwise", [], embedding_client=self.embedder)

    def classify_intent(self, message: str, vehicle_interest: str = "") -> tuple[str, float]:
        normalized = (message or "").strip().lower()
        if normalized in {"hi", "hello", "hey", "good morning", "good afternoon", "good evening"}:
            return "greeting", 1.0
        if normalized in {"what can you do", "how can you help", "how can you help me", "what services do you provide", "what do you do", "who are you", "help"}:
            return "capability", 1.0
        if any(token in normalized for token in ["finance", "financing", "loan", "payment", "monthly", "emi", "apr", "pre-approve", "pre approve"]):
            return "finance", 0.95
        if any(token in normalized for token in ["test drive", "book a drive", "schedule a drive", "drive the", "appointment", "visit the showroom", "come by"]):
            return "test_drive", 0.93
        if any(token in normalized for token in ["available", "in stock", "still have", "sold already", "on the lot", "is it there"]):
            return "availability", 0.92
        if any(token in normalized for token in ["trade in", "trade-in", "trade my", "exchange my"]):
            return "trade_in", 0.92
        if any(token in normalized for token in ["price", "pricing", "quote", "out the door", "out-the-door", "discount"]):
            return "pricing", 0.90
        label, score = self.best_label(f"{message} {vehicle_interest}".strip(), "intent")
        threshold = INTENT_THRESHOLDS.get(label, INTENT_THRESHOLDS["default"])
        if score < threshold:
            return "general_help", round(score, 4)
        return label, score

    def classify_urgency(self, message: str) -> tuple[str, float]:
        normalized = (message or "").strip().lower()
        if any(token in normalized for token in ["today", "right now", "asap", "as soon as possible", "immediately"]):
            return "Immediate", 0.95
        if any(token in normalized for token in ["this week", "tomorrow", "this weekend", "next few days", "soon"]):
            return "Short-Term", 0.9
        if any(token in normalized for token in ["leave a deposit", "ready to buy", "move forward", "serious about buying", "purchase now"]):
            return "High_Intent", 0.92
        if any(token in normalized for token in ["stop messaging", "unsubscribe", "do not contact", "opt out", "remove me from your list"]):
            return "Opt_Out", 0.98
        if any(token in normalized for token in ["manager", "frustrating", "complicated", "specialist", "immediate attention"]):
            return "Escalation", 0.88
        label, score = self.best_label(message, "urgency")
        if score < URGENCY_THRESHOLD:
            return "Research Phase", round(score, 4)
        return label, score

    def classify_message_type(self, message: str) -> tuple[str, float]:
        normalized = (message or "").strip().lower()
        if normalized in {"hi", "hello", "hey", "good morning", "good afternoon", "good evening"}:
            return "greeting", 1.0
        if normalized in {"help", "what can you do", "how can you help", "how can you help me", "who are you", "what do you do"}:
            return "capability", 1.0
        if normalized in {"thanks", "thank you", "appreciate it"}:
            return "thanks", 1.0
        if any(token in normalized for token in ["stop messaging", "unsubscribe", "do not contact", "opt out"]):
            return "opt_out", 0.98
        if any(token in normalized for token in ["schedule", "appointment", "test drive", "come by", "visit"]):
            return "schedule_interest", 0.94
        if any(token in normalized for token in ["finance", "financing", "loan", "payment", "monthly", "emi", "apr"]):
            return "finance_question", 0.94
        if any(token in normalized for token in ["available", "in stock", "sold", "located", "on the lot"]):
            return "inventory_question", 0.92
        if any(token in normalized for token in ["too high", "not convinced", "think about it", "better deal", "worried about the payment"]):
            return "objection", 0.9
        label, score = self.best_label(message, "message_type")
        if score < MESSAGE_TYPE_THRESHOLD:
            return "generic", round(score, 4)
        return label, score

    def choose_next_action(
        self,
        message: str,
        vehicle_interest: str,
        temperature: str,
        inventory_available: bool,
        *,
        intent_label: str | None = None,
        urgency_label: str | None = None,
    ) -> tuple[str, float]:
        intent_label = intent_label or self.classify_intent(message, vehicle_interest)[0]
        urgency_label = urgency_label or self.classify_urgency(message)[0]
        rule = self.config.resolve_next_best_action(
            intent_label=intent_label,
            urgency_label=urgency_label,
            vehicle_available=inventory_available,
        )
        if rule:
            return rule.action, round(1.0 / max(rule.priority, 1), 4)
        if intent_label == "finance":
            return "Offer financing pre-check", 0.65
        if intent_label == "trade_in":
            return "Request trade-in details", 0.60
        if intent_label == "test_drive":
            return ("Schedule test drive" if inventory_available else "Recommend alternative vehicles"), 0.62
        if intent_label == "availability":
            return ("Send availability update" if inventory_available else "Recommend alternative vehicles"), 0.58
        if intent_label in {"capability", "general_help", "greeting"}:
            return "Share dealership services overview", 0.55
        if temperature == "Hot":
            return "Confirm dealership visit", 0.50
        return "Send vehicle video", 0.40

    def retrieve_reply_templates(
        self,
        message: str,
        *,
        top_k: int = 3,
        intent_tag: str | None = None,
        urgency_tag: str | None = None,
        channel: str | None = None,
        preferred_template_id: str | None = None,
        render_context: dict[str, str | None] | None = None,
        template_type: str | None = "reply",
    ) -> list[dict]:
        render_context = render_context or {}
        results = self.reply_index.search(message, top_k=max(top_k * 4, 12))
        selected: list[dict] = []
        for result in results:
            metadata = result["metadata"]
            if template_type and metadata["template_type"] != template_type:
                continue
            if intent_tag and metadata["intent_tag"] not in {intent_tag, "general_help", "general"}:
                continue
            if channel and metadata["channel"].lower() not in {channel.lower(), "any"}:
                continue
            if urgency_tag and metadata["urgency_tag"] not in {urgency_tag, "Any", "general", "research phase"}:
                # do not fully exclude urgency mismatches; just keep searching
                pass
            payload = self._render_template_item(metadata, render_context)
            payload["score"] = result["score"]
            if preferred_template_id and payload["key"] == preferred_template_id:
                payload["score"] += 0.20
            if intent_tag and payload["intent_tag"] == intent_tag:
                payload["score"] += 0.10
            if urgency_tag and payload["urgency_tag"] == urgency_tag:
                payload["score"] += 0.05
            selected.append(payload)
        selected.sort(key=lambda item: item["score"], reverse=True)
        deduped: list[dict] = []
        seen: set[str] = set()
        for item in selected:
            if item["key"] in seen:
                continue
            seen.add(item["key"])
            deduped.append(item)
            if len(deduped) >= top_k:
                break
        return deduped

    def retrieve_knowledge(self, message: str, *, top_k: int = 3, intent_tag: str | None = None) -> list[dict]:
        results = self.knowledge_index.search(message, top_k=max(top_k * 3, 9))
        selected: list[dict] = []
        for result in results:
            metadata = dict(result["metadata"])
            if intent_tag and metadata.get("intent_tag") not in {intent_tag, "general_help", "general"}:
                continue
            metadata["score"] = result["score"]
            if intent_tag and metadata.get("intent_tag") == intent_tag:
                metadata["score"] += 0.08
            selected.append(metadata)
        selected.sort(key=lambda item: item["score"], reverse=True)
        return selected[:top_k]

    def profile_similarity(self, text: str, profile_text: str) -> float:
        return round(self.pair_index.pair_score(text, profile_text), 4)

    def vehicle_similarity(self, text: str, vehicle_text: str) -> float:
        return round(self.pair_index.pair_score(text, vehicle_text), 4)

    def best_label(self, text: str, label_set: str) -> tuple[str, float]:
        index = {
            "intent": self.intent_index,
            "urgency": self.urgency_index,
            "message_type": self.message_type_index,
        }.get(label_set)
        if not index:
            return "", 0.0
        results = index.search(text, top_k=1)
        if not results:
            return "", 0.0
        result = results[0]
        return result["metadata"]["label"], round(result["score"], 4)

    def _build_label_index(self, mapping: dict[str, list[str]], name: str) -> HybridSearchIndex:
        docs: list[HybridDocument] = []
        for label, examples in mapping.items():
            for idx, example in enumerate(examples):
                docs.append(
                    HybridDocument(
                        doc_id=f"{name}:{label}:{idx}",
                        text=example,
                        metadata={"label": label},
                    )
                )
        return HybridSearchIndex(name, docs, embedding_client=self.embedder)

    def _build_reply_template_items(self) -> list[HybridDocument]:
        docs: list[HybridDocument] = []
        for template in self.config.active_message_templates():
            docs.append(
                HybridDocument(
                    doc_id=template.template_id,
                    text=template.text,
                    metadata={
                        "key": template.template_id,
                        "channel": template.channel,
                        "template_type": template.template_type,
                        "intent_tag": template.intent_tag,
                        "urgency_tag": template.urgency_tag,
                        "brand_tone": template.brand_tone,
                        "text": template.text,
                    },
                )
            )
        return docs

    def _build_knowledge_items(self) -> list[HybridDocument]:
        docs: list[HybridDocument] = []
        for item in self.config.knowledge_items:
            docs.append(
                HybridDocument(
                    doc_id=item["knowledge_id"],
                    text=item["text"],
                    metadata=item,
                )
            )
        return docs

    def _render_template_item(self, item: dict, render_context: dict[str, str | None]) -> dict:
        template = self.config.get_message_template(item["key"])
        payload = dict(item)
        if template:
            payload["text"] = self.config.render_template_text(template, **render_context)
        return payload


@lru_cache
def get_semantic_service() -> SemanticService:
    return SemanticService()
