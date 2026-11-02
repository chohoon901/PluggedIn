from dataclasses import replace
from datetime import datetime, date, timezone
from decimal import Decimal
from itertools import product
from importlib import import_module
import unittest


class EvaluationTests(unittest.TestCase):
    def setUp(self):
        try:
            self.service = import_module('ca.uvic.ecs.csc501.cmn.services.evaluation')
        except ModuleNotFoundError:
            self.fail('Pure station evaluation has not been implemented')
        from ca.uvic.ecs.csc501.cmn.contracts.models import StationSnapshot, StationMetadata, VehicleSnapshot
        from ca.uvic.ecs.csc501.cmn.station import Station
        from ca.uvic.ecs.csc501.cmn.vehicle import Vehicle
        from ca.uvic.ecs.csc501.cmn.connector_type import ConnectorType
        from ca.uvic.ecs.csc501.cmn.port import Port
        from ca.uvic.ecs.csc501.cmn.operating_period import OperatingPeriod
        from ca.uvic.ecs.csc501.cmn.membership import Membership
        from ca.uvic.ecs.csc501.cmn.value_objects.daily_time import DailyTime
        self.Membership, self.Port, self.Period, self.Time = Membership, Port, OperatingPeriod, DailyTime
        station = Station(1, Decimal('48.46'), Decimal('-123.31'), 'Test', None, 'Victoria', 'BC', 'ACTIVE', 'public', False, 'VAN', False, 1, 1, 1)
        self.station = StationSnapshot(station, (Port(1, 1, 1, 1, Decimal('150'), 'DC', 1),),
            tuple(OperatingPeriod(i+1, 1, day, DailyTime(0), DailyTime(86400)) for i, day in enumerate(('Mon','Tue','Wed','Thu','Fri','Sat','Sun'))),
            (ConnectorType(1, 'CCS1'), ConnectorType(2, 'CHAdeMO'), ConnectorType(3, 'NACS'), ConnectorType(4, 'J1772')), (),
            StationMetadata('America/Vancouver', 'COMPLETE', 'COMPLETE', 'COMPLETE'))
        self.vehicle = VehicleSnapshot(Vehicle(1, 'DEMO0000000000001', vehicle_class='VAN', max_charge_kw=Decimal('100')), (1,))
        self.memberships = [Membership(1, 1, 1, date(2026, 1, 1))]
        self.arrival = datetime(2026, 10, 26, 19, tzinfo=timezone.utc)

    def evaluate(self, station=None, vehicle=None, memberships=None, arrival=None, driver_id=1):
        return self.service.evaluate_station(station or self.station, vehicle or self.vehicle,
            self.memberships if memberships is None else memberships, arrival or self.arrival, driver_id=driver_id)

    def changed_station(self, **fields):
        return replace(self.station, station=replace(self.station.station, **fields))

    def test_all_81_and_combinations_preserve_failure_then_uncertainty(self):
        for statuses in product(('PASS','FAIL','UNKNOWN'), repeat=4):
            expected = 'UNAVAILABLE' if 'FAIL' in statuses else 'NEEDS_REVIEW' if 'UNKNOWN' in statuses else 'AVAILABLE'
            with self.subTest(statuses=statuses):
                self.assertEqual(self.service.aggregate_checks(statuses), expected)

    def test_known_direct_port_membership_and_hours_are_available(self):
        result = self.evaluate()
        self.assertEqual(result.overall_status, 'AVAILABLE')
        self.assertEqual(result.compatible_port_ids, (1,))
        self.assertEqual(result.selected_port_id, 1)
        self.assertEqual(result.power_limit_kw, Decimal('100'))
        self.assertEqual(set(result.checks), {'opening','access','connector','payment'})
        self.assertTrue(all(check.reasons and check.evidence for check in result.checks.values()))

    def test_opening_and_closing_boundaries_use_station_local_clock(self):
        station = replace(self.station, operating_periods=(self.Period(1, 1, 'Mon', self.Time.parse('09:00:00'), self.Time.parse('17:00:00')),))
        self.assertEqual(self.evaluate(station=station, arrival=datetime(2026,10,26,16,tzinfo=timezone.utc)).checks['opening'].status,'PASS')
        self.assertEqual(self.evaluate(station=station, arrival=datetime(2026,10,27,0,tzinfo=timezone.utc)).checks['opening'].status,'FAIL')

    def test_split_overnight_sunday_reaches_monday_without_inventing_hours(self):
        station = replace(self.station, operating_periods=(self.Period(1,1,'Sun',self.Time(79200),self.Time(86400)),self.Period(2,1,'Mon',self.Time(0),self.Time(21600))))
        self.assertEqual(self.evaluate(station=station,arrival=datetime(2026,10,26,12,tzinfo=timezone.utc)).checks['opening'].status,'PASS')
        self.assertEqual(self.evaluate(station=station,arrival=datetime(2026,10,26,13,tzinfo=timezone.utc)).checks['opening'].status,'FAIL')

    def test_partial_or_missing_hours_remain_unknown(self):
        for completeness in ('UNKNOWN','PARTIAL'):
            station = replace(self.station,metadata=replace(self.station.metadata,hours_completeness=completeness))
            self.assertEqual(self.evaluate(station=station).checks['opening'].status,'UNKNOWN')
        self.assertEqual(self.evaluate(station=replace(self.station,operating_periods=())).checks['opening'].status,'UNKNOWN')

    def test_unknown_facility_is_fail_when_complete_schedule_is_closed(self):
        station = replace(self.changed_station(status='UNKNOWN'), operating_periods=(self.Period(1,1,'Tue',self.Time(0),self.Time(86400)),))
        self.assertEqual(self.evaluate(station=station).checks['opening'].status,'FAIL')
        self.assertEqual(self.evaluate(station=self.changed_station(status='UNKNOWN')).checks['opening'].status,'UNKNOWN')
        self.assertEqual(self.evaluate(station=self.changed_station(status='INACTIVE')).checks['opening'].status,'FAIL')
        for status in ('PLANNED','TEMPORARILY_CLOSED',None):
            self.assertEqual(self.evaluate(station=self.changed_station(status=status)).checks['opening'].status,'UNKNOWN')

    def test_missing_or_invalid_timezone_yields_unknown(self):
        for zone in (None,'Invalid/Zone'):
            station = replace(self.station,metadata=replace(self.station.metadata,timezone=zone))
            self.assertEqual(self.evaluate(station=station).checks['opening'].status,'UNKNOWN')

    def test_naive_arrival_is_rejected(self):
        with self.assertRaises(ValueError):
            self.evaluate(arrival=datetime(2026,10,26,12))

    def test_local_conversion_overflow_keeps_supported_instant_and_unknown_checks(self):
        for arrival, zone in ((datetime.min.replace(tzinfo=timezone.utc), 'America/Vancouver'),
                              (datetime.max.replace(tzinfo=timezone.utc), 'Pacific/Auckland')):
            with self.subTest(arrival=arrival, zone=zone):
                station = replace(self.station, metadata=replace(self.station.metadata, timezone=zone))
                result = self.evaluate(station=station, arrival=arrival)
                self.assertEqual(result.arrival_at, arrival)
                self.assertEqual(result.overall_status, 'NEEDS_REVIEW')
                self.assertEqual(result.checks['opening'].status, 'UNKNOWN')
                self.assertEqual(result.checks['payment'].status, 'UNKNOWN')
                self.assertIsNone(result.checks['opening'].evidence['local_arrival_at'])
                self.assertIsNone(result.checks['payment'].evidence['local_arrival_date'])

    def test_access_restriction_normalization_and_unknown_conditions(self):
        self.assertEqual(self.evaluate(station=self.changed_station(access_restriction=' PUBLIC ')).checks['access'].status,'PASS')
        for restriction in ('no public access','closed to public'):
            self.assertEqual(self.evaluate(station=self.changed_station(access_restriction=restriction)).checks['access'].status,'FAIL')
        for restriction in ('customers only','fleet only','private',None,'staff approval'):
            self.assertEqual(self.evaluate(station=self.changed_station(access_restriction=restriction)).checks['access'].status,'UNKNOWN')

    def test_vehicle_size_excess_fails_and_truck_parking_cannot_prove_clearance(self):
        self.assertEqual(self.evaluate(station=self.changed_station(max_vehicle_class='CAR')).checks['access'].status,'FAIL')
        truck = replace(self.vehicle,vehicle=replace(self.vehicle.vehicle,vehicle_class='HEAVY_TRUCK'))
        result = self.evaluate(station=self.changed_station(max_vehicle_class='ALL',has_truck_parking=True),vehicle=truck)
        self.assertEqual(result.checks['access'].status,'UNKNOWN')
        self.assertIn('TRUCK_CLEARANCE_UNKNOWN',[r.code for r in result.checks['access'].reasons])

    def test_unknown_vehicle_or_facility_class_requires_review(self):
        self.assertEqual(self.evaluate(station=self.changed_station(max_vehicle_class=None)).checks['access'].status,'UNKNOWN')
        vehicle = replace(self.vehicle,vehicle=replace(self.vehicle.vehicle,vehicle_class='unrecognized'))
        self.assertEqual(self.evaluate(vehicle=vehicle).checks['access'].status,'UNKNOWN')

    def test_complete_mismatching_port_fails_direct_connection(self):
        port = replace(self.station.ports[0],connector_type_id=2)
        self.assertEqual(self.evaluate(station=replace(self.station,ports=(port,))).checks['connector'].status,'FAIL')

    def test_unverified_current_nacs_and_empty_vehicle_acceptance_are_unknown(self):
        for connector,current,accepted in ((1,None,(1,)),(1,'AC',(1,)),(3,'DC',(3,))):
            port = replace(self.station.ports[0],connector_type_id=connector,current_type=current)
            result = self.evaluate(station=replace(self.station,ports=(port,)),vehicle=replace(self.vehicle,accepted_connector_ids=accepted))
            self.assertEqual(result.checks['connector'].status,'UNKNOWN')
        self.assertEqual(self.evaluate(vehicle=replace(self.vehicle,accepted_connector_ids=())).checks['connector'].status,'UNKNOWN')

    def test_j1772_ac_and_chademo_dc_are_verified_direct_connections(self):
        for connector,current in ((2,'DC'),(4,'AC')):
            port = replace(self.station.ports[0],connector_type_id=connector,current_type=current)
            result = self.evaluate(station=replace(self.station,ports=(port,)),vehicle=replace(self.vehicle,accepted_connector_ids=(connector,)))
            self.assertEqual(result.overall_status,'AVAILABLE')

    def test_partial_ports_leave_unknown_candidate_but_keep_common_failure(self):
        port = replace(self.station.ports[0],connector_type_id=2)
        station = replace(self.station,ports=(port,),metadata=replace(self.station.metadata,ports_completeness='PARTIAL'))
        self.assertEqual(self.evaluate(station=station).overall_status,'NEEDS_REVIEW')
        station = replace(station,station=replace(station.station,access_restriction='no public access'))
        self.assertEqual(self.evaluate(station=station).overall_status,'UNAVAILABLE')
        self.assertEqual(self.evaluate(station=replace(self.station,ports=())).overall_status,'NEEDS_REVIEW')

    def test_known_good_port_wins_or_and_power_order_is_deterministic(self):
        ports = (replace(self.station.ports[0],port_id=3,power_kw=None),replace(self.station.ports[0],port_id=2),self.station.ports[0],replace(self.station.ports[0],port_id=4,connector_type_id=2,power_kw=Decimal('350')))
        result = self.evaluate(station=replace(self.station,ports=ports))
        self.assertEqual(result.overall_status,'AVAILABLE')
        self.assertEqual(result.selected_port_id,1)
        self.assertEqual(result.compatible_port_ids,(1,2,3))

    def test_unknown_power_does_not_change_compatibility(self):
        vehicle = replace(self.vehicle,vehicle=replace(self.vehicle.vehicle,max_charge_kw=None))
        result = self.evaluate(vehicle=vehicle)
        self.assertEqual(result.overall_status,'AVAILABLE')
        self.assertIsNone(result.power_limit_kw)
        self.assertIn('POWER_UNKNOWN',[reason.code for reason in result.warnings])

    def test_membership_uses_local_date_both_boundaries_and_selected_driver(self):
        membership = self.Membership(2,1,1,date(2026,10,26),date(2026,10,26))
        self.assertEqual(self.evaluate(memberships=[membership],arrival=datetime(2026,10,27,5,tzinfo=timezone.utc)).checks['payment'].status,'PASS')
        self.assertEqual(self.evaluate(memberships=[membership],arrival=datetime(2026,10,27,19,tzinfo=timezone.utc)).checks['payment'].status,'FAIL')
        self.assertEqual(self.evaluate(memberships=[membership],driver_id=2).checks['payment'].status,'FAIL')

    def test_other_network_does_not_pay_and_guest_does(self):
        other = replace(self.memberships[0],network_id=2)
        self.assertEqual(self.evaluate(memberships=[other]).checks['payment'].status,'FAIL')
        self.assertEqual(self.evaluate(station=self.changed_station(accepts_guest_payment=True,network_id=None),memberships=[]).checks['payment'].status,'PASS')
        self.assertEqual(self.evaluate(station=self.changed_station(network_id=None),memberships=[]).checks['payment'].status,'UNKNOWN')

    def test_unconfirmed_bool_cannot_claim_guest_payment(self):
        station = replace(self.changed_station(accepts_guest_payment=True),metadata=replace(self.station.metadata,unconfirmed_fields=('accepts_guest_payment',)))
        self.assertEqual(self.evaluate(station=station,memberships=[]).checks['payment'].status,'UNKNOWN')
        self.assertEqual(self.evaluate(station=station).checks['payment'].status,'PASS')

    def test_current_timezone_rules_keep_vancouver_at_minus_seven_after_october(self):
        for month, day in ((11,1),(12,1)):
            result = self.evaluate(arrival=datetime(2026,month,day,19,tzinfo=timezone.utc))
            self.assertTrue(result.checks['opening'].evidence['local_arrival_at'].endswith('-07:00'))

    def test_empty_ports_do_not_erase_known_facility_closure(self):
        station = replace(self.changed_station(status='INACTIVE'),ports=())
        self.assertEqual(self.evaluate(station=station).overall_status,'UNAVAILABLE')

    def test_common_failure_keeps_verified_connector_on_representative_port(self):
        mismatching = replace(self.station.ports[0],port_id=2,connector_type_id=2,power_kw=Decimal('350'))
        station = replace(self.changed_station(status='INACTIVE'),ports=(mismatching,self.station.ports[0]))
        result = self.evaluate(station=station)
        self.assertEqual(result.overall_status,'UNAVAILABLE')
        self.assertEqual(result.checks['connector'].status,'PASS')
        self.assertEqual(result.selected_port_id,1)
        self.assertEqual(result.compatible_port_ids,(1,))

    def test_unconfirmed_port_quantity_is_warned_without_affecting_connection(self):
        station = replace(self.station,metadata=replace(self.station.metadata,unconfirmed_fields=('quantity',)))
        result = self.evaluate(station=station)
        self.assertEqual(result.overall_status,'AVAILABLE')
        self.assertIn('PORTS_UNKNOWN',[reason.code for reason in result.warnings])


if __name__ == '__main__':
    unittest.main()
