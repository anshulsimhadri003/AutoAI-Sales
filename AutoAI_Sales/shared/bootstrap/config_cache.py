from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from shared.utils.csv_loader import bool_from_str, int_from_str, load_csv


@dataclass(frozen=True)
class MessageTemplateConfig:
    template_id: str
    channel: str
    template_type: str
    intent_tag: str
    urgency_tag: str
    brand_tone: str
    text: str
    is_active: bool


@dataclass(frozen=True)
class NextBestActionRule:
    rule_id: str
    intent_label: str
    urgency_label: str
    vehicle_available: bool
    action: str
    priority: int


@dataclass(frozen=True)
class LeadStatusCode:
    status_code: str
    status_label: str
    category: str


class ConfigCache:
    def __init__(self) -> None:
        self.intent_prototypes = self._group_examples("intent_prototypes.csv")
        self.urgency_prototypes = self._group_examples("urgency_prototypes.csv")
        self.message_templates = self._load_message_templates()
        self.message_templates_by_id = {template.template_id: template for template in self.message_templates}
        self.next_best_action_rules = self._load_next_best_action_rules()
        self.lead_status_codes = self._load_lead_status_codes()
        self.knowledge_items = self._load_knowledge_items()

    def active_message_templates(
        self,
        *,
        intent_tag: str | None = None,
        urgency_tag: str | None = None,
        channel: str | None = None,
        template_type: str | None = None,
    ) -> list[MessageTemplateConfig]:
        templates = [template for template in self.message_templates if template.is_active]
        filtered = [
            template
            for template in templates
            if (not intent_tag or template.intent_tag == intent_tag)
            and (not urgency_tag or template.urgency_tag == urgency_tag)
            and (not channel or template.channel.lower() in {channel.lower(), "any"})
            and (not template_type or template.template_type == template_type)
        ]
        return filtered or templates

    def get_message_template(self, template_id: str | None) -> MessageTemplateConfig | None:
        if not template_id:
            return None
        return self.message_templates_by_id.get(template_id)

    def render_template_text(self, template: MessageTemplateConfig | None, **context: str | None) -> str:
        if template is None:
            return ""
        values = {
            "vehicle": context.get("vehicle") or "the vehicle",
            "dealership_name": context.get("dealership_name") or "the dealership",
            "appointment_time": context.get("appointment_time") or "your preferred time",
        }
        try:
            return template.text.format(**values)
        except KeyError:
            return template.text

    def resolve_next_best_action(
        self,
        *,
        intent_label: str,
        urgency_label: str,
        vehicle_available: bool,
    ) -> NextBestActionRule | None:
        exact = [
            rule
            for rule in self.next_best_action_rules
            if rule.intent_label == intent_label
            and rule.urgency_label == urgency_label
            and rule.vehicle_available == vehicle_available
        ]
        if exact:
            return exact[0]

        partial = [
            rule
            for rule in self.next_best_action_rules
            if rule.intent_label == intent_label and rule.vehicle_available == vehicle_available
        ]
        if partial:
            return partial[0]

        fallback = [rule for rule in self.next_best_action_rules if rule.intent_label == intent_label]
        return fallback[0] if fallback else None

    def _group_examples(self, filename: str) -> dict[str, list[str]]:
        grouped: dict[str, list[str]] = {}
        for row in load_csv(filename):
            label = row.get("label", "")
            text = row.get("example_text", "")
            if not label or not text:
                continue
            grouped.setdefault(label, []).append(text)
        return grouped

    def _load_message_templates(self) -> list[MessageTemplateConfig]:
        templates = []
        for row in load_csv("message_templates.csv"):
            template_id = row.get("template_id", "")
            if not template_id:
                continue
            templates.append(
                MessageTemplateConfig(
                    template_id=template_id,
                    channel=row.get("channel", "email"),
                    template_type=row.get("template_type", "reply"),
                    intent_tag=row.get("intent_tag", ""),
                    urgency_tag=row.get("urgency_tag", ""),
                    brand_tone=row.get("brand_tone", ""),
                    text=row.get("text", ""),
                    is_active=bool_from_str(row.get("is_active"), default=True),
                )
            )
        return templates

    def _load_knowledge_items(self) -> list[dict[str, str]]:
        items: list[dict[str, str]] = []
        for row in load_csv("faq_knowledge.csv"):
            text = row.get("text", "")
            if not text:
                continue
            items.append(
                {
                    "knowledge_id": row.get("knowledge_id", ""),
                    "intent_tag": row.get("intent_tag", "general_help"),
                    "title": row.get("title", ""),
                    "text": text,
                }
            )
        return items

    def _load_next_best_action_rules(self) -> list[NextBestActionRule]:
        rules = []
        for row in load_csv("next_best_action_rules.csv"):
            action = row.get("action", "")
            if not action:
                continue
            rules.append(
                NextBestActionRule(
                    rule_id=row.get("rule_id", ""),
                    intent_label=row.get("intent_label", ""),
                    urgency_label=row.get("urgency_label", ""),
                    vehicle_available=bool_from_str(row.get("vehicle_available"), default=True),
                    action=action,
                    priority=int_from_str(row.get("priority"), default=99),
                )
            )
        return sorted(rules, key=lambda rule: (rule.priority, rule.rule_id))

    def _load_lead_status_codes(self) -> dict[str, LeadStatusCode]:
        codes: dict[str, LeadStatusCode] = {}
        for row in load_csv("lead_status_codes.csv"):
            status_code = row.get("status_code", "")
            if not status_code:
                continue
            codes[status_code] = LeadStatusCode(
                status_code=status_code,
                status_label=row.get("status_label", ""),
                category=row.get("category", ""),
            )
        return codes


@lru_cache(maxsize=1)
def get_config_cache() -> ConfigCache:
    return ConfigCache()
