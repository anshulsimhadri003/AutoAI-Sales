from __future__ import annotations

from sqlalchemy.orm import Session

from apps.api_gateway.services.semantic_service import get_semantic_service
from shared.models.models import SalesRep


class RoutingService:
    def __init__(self, db: Session):
        self.db = db
        self.semantic = get_semantic_service()

    def assign_rep(self, dealership_id: str, *, message: str, vehicle_interest: str, location: str, score: int, reserve: bool = True):
        reps = (
            self.db.query(SalesRep)
            .filter(SalesRep.dealership_id == dealership_id)
            .order_by(SalesRep.workload.asc(), SalesRep.name.asc())
            .all()
        )
        if not reps:
            return None

        query_text = f"{vehicle_interest}. {message}".strip()
        preferred_language = self._infer_language(message)
        ranked = []
        for rep in reps:
            specialty = self.semantic.profile_similarity(query_text, rep.profile_text or " ")
            location_score = 1.0 if location and rep.location.lower() == location.lower() else 0.65
            language_score = self._language_score(rep, preferred_language)
            priority = min(score / 100.0, 1.0)
            at_capacity = rep.max_active_leads > 0 and rep.workload >= rep.max_active_leads
            availability = 1.0 if rep.is_available and not at_capacity else 0.2 if rep.is_available else 0.05
            workload_penalty = min(rep.workload / max(rep.max_active_leads or 20, 1), 1.25)
            capacity_score = 1.0 - min(rep.workload / max(rep.max_active_leads or 20, 1), 1.0)
            total = (
                (0.40 * specialty)
                + (0.18 * location_score)
                + (0.15 * priority)
                + (0.10 * availability)
                + (0.09 * language_score)
                + (0.08 * capacity_score)
                - (0.10 * workload_penalty)
            )
            ranked.append((total, rep))
        ranked.sort(key=lambda item: item[0], reverse=True)
        best_rep = ranked[0][1]
        if reserve:
            best_rep.workload += 1
            self.db.commit()
            self.db.refresh(best_rep)
        return best_rep

    def _infer_language(self, message: str) -> str:
        lowered = (message or "").lower()
        if any(token in lowered for token in ["espanol", "español", "spanish"]):
            return "Spanish"
        if any(token in lowered for token in ["portugues", "portuguese"]):
            return "Portuguese"
        return "English"

    def _language_score(self, rep: SalesRep, preferred_language: str) -> float:
        languages = {language.lower() for language in (rep.languages or [])}
        if preferred_language.lower() in languages:
            return 1.0
        if "english" in languages:
            return 0.7
        return 0.4
