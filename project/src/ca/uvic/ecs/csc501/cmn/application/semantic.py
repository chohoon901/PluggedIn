"""Validate charging search inputs and read the matching graph results."""

import re
from decimal import Decimal

from ..contracts.errors import InputError
from ..contracts.semantic import AdapterCandidate, HighPowerPort, SemanticRepository, SemanticVehicle


_DECIMAL_INPUT = re.compile(r'(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)')


class SemanticService:
    def __init__(self, repository: SemanticRepository):
        self.repository = repository

    def fast_chargers(self, min_power_kw: str) -> list[HighPowerPort]:
        value = min_power_kw.strip()
        if len(value) > 20 or not _DECIMAL_INPUT.fullmatch(value):
            message = 'Enter a minimum power of 0 kW or higher.'
            raise InputError(message, {'min_power_kw': message})
        return self.repository.fast_chargers(Decimal(value))

    def vehicles(self) -> list[SemanticVehicle]:
        return self.repository.vehicles()

    def adapter_candidates(
        self, vehicle_iri: str, vehicles: list[SemanticVehicle],
    ) -> list[AdapterCandidate]:
        if not any(vehicle.iri == vehicle_iri for vehicle in vehicles):
            message = 'Select a vehicle from the list.'
            raise InputError(message, {'vehicle_iri': message})
        return self.repository.adapter_candidates(vehicle_iri)
