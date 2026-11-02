"""Pure domain behavior: invalid inputs must never reach persistence."""
import unittest
from datetime import date, datetime
from decimal import Decimal
from importlib import import_module


class DomainTests(unittest.TestCase):
    def module(self, name):
        try:
            return import_module('ca.uvic.ecs.csc501.cmn.' + name)
        except ModuleNotFoundError:
            self.fail('Required domain module has not been implemented: ' + name)

    def test_daily_time_preserves_midnight_and_rejects_invalid_clock(self):
        DailyTime = self.module('value_objects.daily_time').DailyTime
        self.assertEqual(str(DailyTime.parse('24:00:00')), '24:00:00')
        self.assertEqual(DailyTime.parse('09:15:30').seconds, 33330)
        for value in ('24:00:01', '25:00:00', '9:00:00', '12:60:00'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                DailyTime.parse(value)

    def test_operating_period_is_open_inclusive_and_close_exclusive(self):
        DailyTime = self.module('value_objects.daily_time').DailyTime
        Period = self.module('operating_period').OperatingPeriod
        period = Period(None, 1, 'Mon', DailyTime.parse('09:00:00'), DailyTime.parse('17:00:00'))
        self.assertTrue(period.contains(datetime(2026, 10, 26, 9)))
        self.assertFalse(period.contains(datetime(2026, 10, 26, 17)))
        self.assertFalse(period.contains(datetime(2026, 10, 27, 9)))
        for start, end in (('24:00:00', '24:00:00'), ('17:00:00', '09:00:00')):
            with self.assertRaises(ValueError):
                Period(None, 1, 'Mon', DailyTime.parse(start), DailyTime.parse(end))

    def test_membership_includes_both_boundary_dates(self):
        Membership = self.module('membership').Membership
        m = Membership(None, 1, 2, date(2026, 10, 26), date(2026, 10, 27))
        self.assertTrue(m.is_active_on(date(2026, 10, 26)))
        self.assertTrue(m.is_active_on(date(2026, 10, 27)))
        self.assertFalse(m.is_active_on(date(2026, 10, 28)))
        with self.assertRaises(ValueError):
            Membership(None, 1, 2, date(2026, 10, 27), date(2026, 10, 26))

    def test_driver_normalizes_and_limits_real_input(self):
        Driver = self.module('driver').Driver
        driver = Driver(None, '  DEMO  ', '  ', ' Carrier ')
        self.assertEqual(driver.licence_number, 'DEMO')
        self.assertIsNone(driver.name)
        self.assertEqual(driver.carrier_name, 'Carrier')
        for licence in (' ', 'x' * 31):
            with self.assertRaises(ValueError):
                Driver(None, licence)

    def test_vehicle_rejects_invalid_vin_and_normalizes_power(self):
        Vehicle = self.module('vehicle').Vehicle
        vehicle = Vehicle(None, 'DEMO0000000000001', max_charge_kw=Decimal('100.04'))
        self.assertEqual(vehicle.max_charge_kw, Decimal('100.0'))
        for fields in ({'vin': 'short'}, {'vin': 'x' * 17, 'range_km': 0},
                       {'vin': 'x' * 17, 'max_charge_kw': Decimal('-1')}):
            with self.assertRaises(ValueError):
                Vehicle(None, **fields)

    def test_location_rejects_out_of_bounds_and_quantizes(self):
        Location = self.module('value_objects.location').Location
        self.assertEqual(Location(Decimal('48.1234567'), Decimal('-123')).latitude, Decimal('48.123457'))
        for lat, lon in (('91', '0'), ('0', '-181'), ('NaN', '0')):
            with self.assertRaises(ValueError):
                Location(Decimal(lat), Decimal(lon))

    def test_required_foreign_ids_and_port_quantity_cannot_be_none(self):
        Port = self.module('port').Port
        SiteOwner = self.module('site_owner').SiteOwner
        for factory in (lambda: Port(None, None, 1, 1), lambda: Port(None, 1, 1, None),
                        lambda: Port(None, 1, 1, 1, quantity=None), lambda: SiteOwner(None)):
            with self.assertRaises(ValueError):
                factory()

    def test_decimal_power_accepts_exact_schema_maximum(self):
        Vehicle = self.module('vehicle').Vehicle
        self.assertEqual(Vehicle(None, 'x'*17, max_charge_kw=Decimal('99999.9')).max_charge_kw, Decimal('99999.9'))
        for value in ('100000', 'Infinity', 'NaN', '0.01'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                Vehicle(None, 'x'*17, max_charge_kw=Decimal(value))

    def test_port_current_and_adapter_direction_enforce_schema_constraints(self):
        Port = self.module('port').Port
        Adapter = self.module('adapter').Adapter
        with self.assertRaises(ValueError):
            Port(None, 1, 1, 1, current_type='XX')
        with self.assertRaises(ValueError):
            Adapter(None, 'model', None, None, 1, 1)
        with self.assertRaises(ValueError):
            Port(None, 1, 0, 1)

    def test_repository_protocols_import_without_executing_database_code(self):
        module = self.module('contracts.repositories')
        self.assertTrue(module.UnitOfWork._is_protocol)


if __name__ == '__main__':
    unittest.main()
