-- ============================================================================
-- Specify SQL operations supporting the PluggedIn application:
-- initial data population, data retrieval, and data maintenance.
--
-- Execution notes:
-- * Table definitions and integrity constraints are maintained in schema.sql.
--   Initialize the database with schema.sql before inserting demo data.
-- * Section 1 is a one-time example dataset for a new, empty database.
-- * Sections 2-5 are a query reference, NOT a sequential executable script.
--   Run individual statements with the indicated named parameters bound.
-- * For variable-length IN predicates, expand the placeholders to match the
--   number of IDs. Do not execute all alternatives indiscriminately.
-- * Opening hours, access, connector and payment eligibility are evaluated
--   by application logic using the records retrieved by these queries.
-- ============================================================================
PRAGMA foreign_keys = ON;

-- ============================================================================
-- 1. DATA POPULATION
--    Example data for organizations, drivers, vehicles, charging stations,
--    ports, operating schedules, and membership relationships.
--    Execute only on a newly initialized database without these IDs.
-- ============================================================================
INSERT INTO organization (organization_id, name, website)
VALUES (1, 'Demo Charging Company', NULL), (2, 'Demo Other Network', NULL);
INSERT INTO site_owner (organization_id, business_type)
VALUES (1, 'Demo charging site');
INSERT INTO operator (organization_id, support_phone)
VALUES (1, '000-000-0000');
INSERT INTO network (organization_id, payment_method)
VALUES (1, 'Membership or guest'), (2, 'Membership');
INSERT INTO connector_type (connector_type_id, name, max_power_kw)
VALUES (1, 'CCS1', NULL), (2, 'CHAdeMO', NULL);
INSERT INTO driver (driver_id, licence_number, name, carrier_name)
VALUES (1, 'DEMO-LIC-001', 'Mina', 'Demo Delivery'),
       (2, 'DEMO-LIC-002', 'Jin', NULL);
INSERT INTO vehicle
    (vehicle_id, vin, licence_plate, make, model, class, range_km, max_charge_kw)
VALUES (1, 'DEMO0000000000001', 'DEMO-01', 'Demo', 'Van', 'VAN', 250, 100.0);
INSERT INTO vehicle_accepts (vehicle_accepts_id, vehicle_id, connector_type_id)
VALUES (1, 1, 1);
INSERT INTO membership (membership_id, driver_id, network_id, start_date, end_date)
VALUES (1, 1, 1, '2026-01-01', NULL),
       (2, 2, 2, '2026-01-01', NULL);

INSERT INTO station
    (station_id, latitude, longitude, name, street, city, province,
     status, access_restriction, accepts_guest_payment,
     max_vehicle_class, has_truck_parking, owner_id, operator_id, network_id)
VALUES
    (1, 48.46, -123.31, 'Demo A', NULL, 'Victoria', 'BC', 'ACTIVE', 'public', 0, 'VAN', 0, 1, 1, 1),
    (2, 48.47, -123.32, 'Demo B', NULL, 'Victoria', 'BC', 'ACTIVE', 'public', 0, 'VAN', 0, 1, 1, 1),
    (3, 48.48, -123.33, 'Demo C', NULL, 'Victoria', 'BC', 'ACTIVE', 'public', 0, 'VAN', 0, 1, 1, 1),
    (4, 48.49, -123.34, 'Demo D', NULL, 'Victoria', 'BC', 'ACTIVE', 'public', 0, 'VAN', 0, 1, 1, 1),
    (5, 48.50, -123.35, 'Demo E', NULL, 'Victoria', 'BC', 'ACTIVE', 'public', 1, 'VAN', 0, 1, 1, 1);
INSERT INTO port
    (port_id, station_id, number, connector_type_id, power_kw, current_type, quantity)
VALUES (1, 1, 1, 1, 150.0, 'DC', 1),
       (2, 2, 1, 1, 150.0, 'DC', 1),
       (3, 3, 1, 2, 150.0, 'DC', 1),
       (4, 4, 1, 1, 150.0, 'DC', 1),
       (5, 5, 1, 1, 150.0, 'DC', 1);
INSERT INTO operating_period
    (operating_period_id, station_id, day, open_time, close_time)
VALUES
    (1,1,'Mon','00:00:00','24:00:00'),
    (2,1,'Tue','00:00:00','24:00:00'),
    (3,1,'Wed','00:00:00','24:00:00'),
    (4,1,'Thu','00:00:00','24:00:00'),
    (5,1,'Fri','00:00:00','24:00:00'),
    (6,1,'Sat','00:00:00','24:00:00'),
    (7,1,'Sun','00:00:00','24:00:00'),
    (8,2,'Mon','09:00:00','17:00:00'),
    (9,2,'Tue','09:00:00','17:00:00'),
    (10,2,'Wed','09:00:00','17:00:00'),
    (11,2,'Thu','09:00:00','17:00:00'),
    (12,2,'Fri','09:00:00','17:00:00'),
    (13,3,'Mon','00:00:00','24:00:00'),
    (14,3,'Tue','00:00:00','24:00:00'),
    (15,3,'Wed','00:00:00','24:00:00'),
    (16,3,'Thu','00:00:00','24:00:00'),
    (17,3,'Fri','00:00:00','24:00:00'),
    (18,3,'Sat','00:00:00','24:00:00'),
    (19,3,'Sun','00:00:00','24:00:00'),
    (20,5,'Mon','00:00:00','24:00:00'),
    (21,5,'Tue','00:00:00','24:00:00'),
    (22,5,'Wed','00:00:00','24:00:00'),
    (23,5,'Thu','00:00:00','24:00:00'),
    (24,5,'Fri','00:00:00','24:00:00'),
    (25,5,'Sat','00:00:00','24:00:00'),
    (26,5,'Sun','00:00:00','24:00:00');


-- ============================================================================
-- 2. DATA RETRIEVAL: DRIVERS, VEHICLES, AND MEMBERSHIPS
-- ============================================================================
-- 2.1 Retrieve a selected driver or list all drivers.
SELECT * FROM driver WHERE driver_id = :driver_id;
SELECT * FROM driver ORDER BY driver_id;

-- 2.2 Retrieve a vehicle and its accepted connector types.
SELECT * FROM vehicle WHERE vehicle_id = :vehicle_id;
SELECT * FROM vehicle ORDER BY vehicle_id;
SELECT vehicle_id FROM vehicle ORDER BY vehicle_id;
SELECT connector_type_id FROM vehicle_accepts
WHERE vehicle_id = :vehicle_id ORDER BY connector_type_id;

-- 2.3 Retrieve membership records, optionally for a selected driver.
SELECT * FROM membership WHERE membership_id = :membership_id;
SELECT * FROM membership ORDER BY membership_id;
SELECT * FROM membership WHERE driver_id = :driver_id ORDER BY membership_id;

-- 2.4 Stations with directly compatible connector types (exact connector ID match).
--     These reference queries do not perform the application's full compatibility
--     evaluation: connector aliases, current type, and other eligibility checks
--     are handled by application logic.
SELECT DISTINCT p.station_id
FROM port AS p
JOIN vehicle_accepts AS va
    ON p.connector_type_id = va.connector_type_id
WHERE va.vehicle_id = 1;

-- 2.5 Number of directly compatible port records per station.
--     COUNT(*) counts matched port rows, not physical connectors or SUM(quantity).
--     The unique vehicle/connector association prevents duplicate matches per port.
SELECT p.station_id, COUNT(*) AS compatible_port_count
FROM port AS p
JOIN vehicle_accepts AS va
    ON p.connector_type_id = va.connector_type_id
WHERE va.vehicle_id = 1
GROUP BY p.station_id;

-- ============================================================================
-- 3. DATA RETRIEVAL: CHARGING STATIONS AND REFERENCE CATALOGS
-- ============================================================================
-- 3.1 Retrieve station IDs, station details, ports and operating hours.
--     The port and schedule queries are evaluated for each selected station.
SELECT station_id FROM station ORDER BY station_id;
SELECT * FROM station WHERE station_id = :station_id;
SELECT * FROM port WHERE station_id = :station_id ORDER BY port_id;
SELECT * FROM operating_period WHERE station_id = :station_id
ORDER BY operating_period_id;

-- 3.2 Resolve connector types used by the retrieved ports.
--     Expand the IN list to cover the unique connector IDs.
SELECT * FROM connector_type
WHERE connector_type_id IN (:connector_id_1, :connector_id_2)
ORDER BY connector_type_id;

-- 3.3 Resolve the organizations associated with a station.
--     IDs can refer to an owner, operator or network.
SELECT * FROM organization
WHERE organization_id IN (:organization_id_1, :organization_id_2, :organization_id_3)
ORDER BY organization_id;

-- 3.4 Retrieve the available connector catalog and charging networks.
SELECT * FROM connector_type ORDER BY connector_type_id;
SELECT o.* FROM organization AS o
JOIN network AS n ON n.organization_id = o.organization_id
ORDER BY o.organization_id;

-- 3.5 Retrieve organization records for profile/reference management.
SELECT * FROM organization WHERE organization_id = :organization_id;
SELECT * FROM organization ORDER BY organization_id;

-- ============================================================================
-- 4. DATA INSERTION AND MODIFICATION
--    Parameters are supplied by the relevant application form or workflow.
-- ============================================================================
-- 4.1 Driver profile.
INSERT INTO driver (licence_number, name, carrier_name)
VALUES (:licence_number, :name, :carrier_name);
UPDATE driver SET licence_number = :licence_number,
                  name = :name, carrier_name = :carrier_name
WHERE driver_id = :driver_id;

-- 4.2 Vehicle profile.
INSERT INTO vehicle (vin, licence_plate, make, model, class, range_km, max_charge_kw)
VALUES (:vin, :licence_plate, :make, :model, :vehicle_class, :range_km, :max_charge_kw);
UPDATE vehicle SET vin = :vin, licence_plate = :licence_plate,
                   make = :make, model = :model, class = :vehicle_class,
                   range_km = :range_km, max_charge_kw = :max_charge_kw
WHERE vehicle_id = :vehicle_id;

-- 4.3 Vehicle-to-connector associations.
--     For updates, delete old associations and insert the selected connector
--     IDs in a single transaction; repeat INSERT for each selected connector.
DELETE FROM vehicle_accepts WHERE vehicle_id = :vehicle_id;
INSERT INTO vehicle_accepts (vehicle_id, connector_type_id)
VALUES (:vehicle_id, :connector_type_id);

-- 4.4 Driver network membership.
INSERT INTO membership (driver_id, network_id, start_date, end_date)
VALUES (:driver_id, :network_id, :start_date, :end_date);
UPDATE membership SET driver_id = :driver_id, network_id = :network_id,
                      start_date = :start_date, end_date = :end_date
WHERE membership_id = :membership_id;

-- 4.5 Organization profile (reference-data maintenance).
INSERT INTO organization (name, website) VALUES (:name, :website);
UPDATE organization SET name = :name, website = :website
WHERE organization_id = :organization_id;

-- ============================================================================
-- 5. DATA DELETION
--    Execute only for an explicitly selected record, subject to foreign-key
--    constraints and the configured cascade rules.
-- ============================================================================
DELETE FROM driver WHERE driver_id = :driver_id;
DELETE FROM vehicle WHERE vehicle_id = :vehicle_id;
DELETE FROM membership WHERE membership_id = :membership_id;
DELETE FROM organization WHERE organization_id = :organization_id;

-- ============================================================================
-- 6. DESIGN BOUNDARY
--    The application combines station, port, operating-period, connector,
--    organization, driver, vehicle and membership data to evaluate:
--    operating-hour availability, access eligibility, connector compatibility,
--    and payment eligibility. Those decision rules are application logic,
--    not additional SQL predicates in this query specification.
-- ============================================================================
