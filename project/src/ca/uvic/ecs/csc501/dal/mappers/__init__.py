"""Explicit ORM-to-domain boundary; no live ORM instances leave repositories."""
from dataclasses import fields
from ca.uvic.ecs.csc501.cmn.value_objects.daily_time import DailyTime


def to_domain(entity_class, model):
    values = {field.name: getattr(model, field.name) for field in fields(entity_class)}
    if entity_class.__name__ == 'OperatingPeriod':
        for name in ('open_time', 'close_time'):
            values[name] = DailyTime.parse(values[name])
    return entity_class(**values)


def copy_to_model(entity, model):
    for field in fields(entity):
        if field.name.endswith('_id') and getattr(entity, field.name) is None:
            continue
        value = getattr(entity, field.name)
        setattr(model, field.name, str(value) if isinstance(value, DailyTime) else value)
    return model
