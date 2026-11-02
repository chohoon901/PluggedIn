"""Shared pure input normalization for the original schema's fields."""
from .contracts.errors import InputError
from .value_objects.location import decimal_value
from dataclasses import fields
from decimal import Decimal


def validate_entity(entity, string_lengths: dict[str, int], required=()):
    for definition in fields(entity):
        if definition.type in (int, bool, Decimal) and getattr(entity, definition.name) is None:
            raise InputError(f'{definition.name}: enter a required value.', {definition.name: 'This field is required.'})
    for field, maximum in string_lengths.items():
        value = getattr(entity, field)
        if value is not None:
            if not isinstance(value, str):
                raise InputError(f'{field}: enter text.', {field: 'Enter text.'})
            value = value.strip() or None
        if (field in required and value is None) or (value is not None and len(value) > maximum):
            raise InputError(f'{field}: check whether a value is required and the {maximum}-character limit.', {field: f'Enter no more than {maximum} characters.'})
        object.__setattr__(entity, field, value)
    for field, value in vars(entity).items():
        if field.endswith('_id') and value is not None and (type(value) is not int or value <= 0):
            raise InputError(f'{field}: enter a positive integer.', {field: 'Enter a positive integer.'})
        if field in ('max_power_kw', 'power_kw', 'max_charge_kw') and value is not None:
            object.__setattr__(entity, field, decimal_value(value, field, positive=True, high=Decimal('99999.9')))
        if field in ('range_km', 'quantity', 'number') and value is not None and (type(value) is not int or value <= 0):
            raise InputError(f'{field}: enter a positive integer.', {field: 'Enter a positive integer.'})
