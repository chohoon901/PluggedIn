PRAGMA foreign_keys=ON;

-- =====================================================================
-- PluggedIn — logical (relational) schema, SQLite adaptation
-- Derived from the MVP acyclic ERD (Chen + crow's foot).
-- Key policy: every table has a generated surrogate ID as PRIMARY KEY;
--             the ERD key (natural key / partial key) is kept as a
--             NOT NULL UNIQUE alternate key (AK).
-- ISA subclasses share the superclass ID (PK = FK to organization).
-- =====================================================================

-- ---------------------------------------------------------------------
-- Organization hierarchy  (ISA: overlapping, total)
-- ---------------------------------------------------------------------
CREATE TABLE organization (
    organization_id   INTEGER PRIMARY KEY,
    name              VARCHAR(200) NOT NULL,
    website           VARCHAR(300),
    CONSTRAINT ak_organization_name UNIQUE (name)
);

-- Overlapping: one organization may appear in several subclass tables.
CREATE TABLE site_owner (
    organization_id   INTEGER NOT NULL PRIMARY KEY
                      REFERENCES organization (organization_id) ON DELETE CASCADE,
    business_type     VARCHAR(100)
) WITHOUT ROWID;

CREATE TABLE operator (
    organization_id   INTEGER NOT NULL PRIMARY KEY
                      REFERENCES organization (organization_id) ON DELETE CASCADE,
    support_phone     VARCHAR(30)
) WITHOUT ROWID;

CREATE TABLE network (
    organization_id   INTEGER NOT NULL PRIMARY KEY
                      REFERENCES organization (organization_id) ON DELETE CASCADE,
    payment_method    VARCHAR(200)
) WITHOUT ROWID;

-- ---------------------------------------------------------------------
-- Station  (OwnedBy 1:N, OperatedBy 1:N, ServedBy 0..1:N as FKs)
-- ---------------------------------------------------------------------
CREATE TABLE station (
    station_id            INTEGER PRIMARY KEY,
    latitude              NUMERIC(9,6) NOT NULL CHECK (latitude  BETWEEN -90  AND 90),
    longitude             NUMERIC(9,6) NOT NULL CHECK (longitude BETWEEN -180 AND 180),
    name                  VARCHAR(200),
    street                VARCHAR(200),          -- Address (composite) flattened
    city                  VARCHAR(100),
    province              VARCHAR(50),
    status                VARCHAR(50),
    access_restriction    VARCHAR(100),          -- e.g. public, fleet only, customers only
    accepts_guest_payment INTEGER NOT NULL DEFAULT 0 CHECK (accepts_guest_payment IN (0,1)),
    max_vehicle_class     VARCHAR(30),
    has_truck_parking     INTEGER NOT NULL DEFAULT 0 CHECK (has_truck_parking IN (0,1)),
    owner_id              INTEGER NOT NULL REFERENCES site_owner (organization_id),  -- OwnedBy  (1,1)
    operator_id           INTEGER NOT NULL REFERENCES operator   (organization_id),  -- OperatedBy (1,1)
    network_id            INTEGER          REFERENCES network    (organization_id),  -- ServedBy (0,1)
    CONSTRAINT ak_station_location UNIQUE (latitude, longitude)   -- ERD key: Location
);

-- ---------------------------------------------------------------------
-- Weak entities (identifying relationships Has / OpenDuring)
-- ---------------------------------------------------------------------
CREATE TABLE connector_type (
    connector_type_id INTEGER PRIMARY KEY,
    name              VARCHAR(100) NOT NULL,
    max_power_kw      NUMERIC(6,1) CHECK (max_power_kw > 0),
    CONSTRAINT ak_connector_type_name UNIQUE (name)
);

CREATE TABLE port (
    port_id           INTEGER PRIMARY KEY,
    station_id        INTEGER NOT NULL REFERENCES station (station_id) ON DELETE CASCADE,  -- Has
    number            SMALLINT NOT NULL CHECK (number > 0),                                -- partial key
    connector_type_id INTEGER NOT NULL REFERENCES connector_type (connector_type_id),      -- HasType (1,1)
    power_kw          NUMERIC(6,1) CHECK (power_kw > 0),
    current_type      VARCHAR(5)  CHECK (current_type IN ('AC', 'DC')),
    quantity          SMALLINT NOT NULL DEFAULT 1 CHECK (quantity > 0),
    CONSTRAINT ak_port UNIQUE (station_id, number)          -- owner key + partial key
);

CREATE TABLE operating_period (
    operating_period_id INTEGER PRIMARY KEY,
    station_id          INTEGER NOT NULL REFERENCES station (station_id) ON DELETE CASCADE,  -- OpenDuring
    day                 VARCHAR(3) NOT NULL
                        CHECK (day IN ('Mon','Tue','Wed','Thu','Fri','Sat','Sun')),        -- partial key
    open_time           TEXT NOT NULL,                                                       -- partial key
    close_time          TEXT NOT NULL,      -- 24:00 allowed for "until midnight"
    CONSTRAINT ak_operating_period UNIQUE (station_id, day, open_time),
    CONSTRAINT ck_operating_period_order CHECK (close_time > open_time),
    CONSTRAINT ck_open_clock CHECK (
      length(open_time)=8 AND
      open_time GLOB '[0-2][0-9]:[0-5][0-9]:[0-5][0-9]' AND open_time<'24:00:00'),
    CONSTRAINT ck_close_clock CHECK (
      close_time='24:00:00' OR (length(close_time)=8 AND
      close_time GLOB '[0-2][0-9]:[0-5][0-9]:[0-5][0-9]' AND close_time<'24:00:00'))
);

-- ---------------------------------------------------------------------
-- Adapter  (ConvertsFrom / ConvertsTo: each adapter has exactly one of each)
-- ---------------------------------------------------------------------
CREATE TABLE adapter (
    adapter_id             INTEGER PRIMARY KEY,
    model                  VARCHAR(100) NOT NULL,
    manufacturer           VARCHAR(100),
    max_power_kw           NUMERIC(6,1) CHECK (max_power_kw > 0),
    from_connector_type_id INTEGER NOT NULL REFERENCES connector_type (connector_type_id), -- ConvertsFrom (plug side)
    to_connector_type_id   INTEGER NOT NULL REFERENCES connector_type (connector_type_id), -- ConvertsTo  (inlet side)
    CONSTRAINT ak_adapter_model UNIQUE (model),
    CONSTRAINT ck_adapter_direction CHECK (from_connector_type_id <> to_connector_type_id)
);

-- ---------------------------------------------------------------------
-- Vehicle and Accepts (M:N)
-- ---------------------------------------------------------------------
CREATE TABLE vehicle (
    vehicle_id      INTEGER PRIMARY KEY,
    vin             CHAR(17) NOT NULL,
    licence_plate   VARCHAR(15),
    make            VARCHAR(50),
    model           VARCHAR(50),
    class           VARCHAR(30),
    range_km        INTEGER CHECK (range_km > 0),
    max_charge_kw   NUMERIC(6,1) CHECK (max_charge_kw > 0),
    CONSTRAINT ak_vehicle_vin UNIQUE (vin)
);

CREATE TABLE vehicle_accepts (
    vehicle_accepts_id INTEGER PRIMARY KEY,
    vehicle_id         INTEGER NOT NULL REFERENCES vehicle (vehicle_id) ON DELETE CASCADE,
    connector_type_id  INTEGER NOT NULL REFERENCES connector_type (connector_type_id),
    CONSTRAINT ak_vehicle_accepts UNIQUE (vehicle_id, connector_type_id)
);

-- ---------------------------------------------------------------------
-- Driver and MemberOf (M:N with attributes -> membership)
-- ---------------------------------------------------------------------
CREATE TABLE driver (
    driver_id       INTEGER PRIMARY KEY,
    licence_number  VARCHAR(30) NOT NULL,
    name            VARCHAR(100),
    carrier_name    VARCHAR(200),
    CONSTRAINT ak_driver_licence UNIQUE (licence_number)
);

CREATE TABLE membership (
    membership_id   INTEGER PRIMARY KEY,
    driver_id       INTEGER NOT NULL REFERENCES driver  (driver_id)       ON DELETE CASCADE,
    network_id      INTEGER NOT NULL REFERENCES network (organization_id) ON DELETE CASCADE,
    start_date      DATE NOT NULL,
    end_date        DATE,                                  -- NULL = still active
    CONSTRAINT ak_membership UNIQUE (driver_id, network_id, start_date),
    CONSTRAINT ck_membership_dates CHECK (end_date IS NULL OR end_date >= start_date)
);

-- ---------------------------------------------------------------------
-- Indexes on FK columns not already covered by a UNIQUE constraint
-- ---------------------------------------------------------------------
CREATE INDEX ix_station_owner      ON station (owner_id);
CREATE INDEX ix_station_operator   ON station (operator_id);
CREATE INDEX ix_station_network    ON station (network_id);
CREATE INDEX ix_port_connector     ON port (connector_type_id);
CREATE INDEX ix_adapter_from       ON adapter (from_connector_type_id);
CREATE INDEX ix_adapter_to         ON adapter (to_connector_type_id);
CREATE INDEX ix_accepts_connector  ON vehicle_accepts (connector_type_id);
CREATE INDEX ix_membership_network ON membership (network_id);

-- ---------------------------------------------------------------------
-- ISA "total": every organization must play at least one role.
-- Checked at COMMIT so the superclass row and its subclass row(s)
-- can be inserted in the same transaction.
