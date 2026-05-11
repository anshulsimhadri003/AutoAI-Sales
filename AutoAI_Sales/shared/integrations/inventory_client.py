from __future__ import annotations

from sqlalchemy.orm import Session

from apps.api_gateway.services.semantic_service import get_semantic_service
from shared.models.models import VehicleInventory


class InventoryClient:
    def __init__(self, db: Session):
        self.db = db
        self.semantic = get_semantic_service()

    def get_vehicle(self, dealership_id: str, vehicle_id: str) -> VehicleInventory | None:
        return (
            self.db.query(VehicleInventory)
            .filter(
                VehicleInventory.dealership_id == dealership_id,
                VehicleInventory.public_id == vehicle_id,
            )
            .first()
        )

    def get_vehicle_state(self, dealership_id: str, vehicle_id: str) -> dict:
        vehicle = self.get_vehicle(dealership_id, vehicle_id)
        if not vehicle:
            return {
                "available": False,
                "test_drive_available": False,
                "location": "Unknown",
                "status": "missing",
                "vehicle": None,
            }
        return {
            "available": vehicle.status == "available",
            "test_drive_available": vehicle.status == "available" and vehicle.available_for_test_drive,
            "location": vehicle.location,
            "status": vehicle.status,
            "vehicle": vehicle,
        }

    def is_vehicle_available(self, dealership_id: str, vehicle_id: str) -> bool:
        return self.get_vehicle_state(dealership_id, vehicle_id)["available"]

    def recommend_alternatives(self, dealership_id: str, query_text: str, exclude_vehicle_id: str | None = None, top_k: int = 3):
        vehicles = (
            self.db.query(VehicleInventory)
            .filter(
                VehicleInventory.dealership_id == dealership_id,
                VehicleInventory.status == "available",
            )
            .all()
        )
        ranked = []
        for vehicle in vehicles:
            if exclude_vehicle_id and vehicle.public_id == exclude_vehicle_id:
                continue
            profile = (
                f"{vehicle.year} {vehicle.make_model} {vehicle.trim} {vehicle.body_type} "
                f"{vehicle.fuel_type} {vehicle.transmission} {vehicle.color} "
                f"{vehicle.price_band} {vehicle.price} {vehicle.description}"
            )
            score = self.semantic.vehicle_similarity(query_text, profile)
            ranked.append((score, vehicle))
        ranked.sort(key=lambda item: item[0], reverse=True)
        return [vehicle for _, vehicle in ranked[:top_k]]
