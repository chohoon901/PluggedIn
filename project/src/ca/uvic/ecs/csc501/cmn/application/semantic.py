"""Read the charging query results and validate the selected graph vehicle."""

from ..contracts.errors import InputError
from ..contracts.semantic import AdapterCandidate, HighPowerPort, SemanticRepository, SemanticVehicle


class SemanticService:
    def __init__(self, repository: SemanticRepository):
        self.repository = repository

    def fast_chargers(self) -> list[HighPowerPort]:
        return self.repository.fast_chargers()

    def vehicles(self) -> list[SemanticVehicle]:
        return self.repository.vehicles()

    def adapter_candidates(
        self, vehicle_iri: str, vehicles: list[SemanticVehicle],
    ) -> list[AdapterCandidate]:
        if not any(vehicle.iri == vehicle_iri for vehicle in vehicles):
            message = 'Select a vehicle from the list.'
            raise InputError(message, {'vehicle_iri': message})
        return self.repository.adapter_candidates(vehicle_iri)
