# NLR vehicle-class access and package organization

This implements the user's request to interpret NLR vehicle classes without changing stored data or schema.

## Source and comparison

NLR/AFDC `maximum_vehicle_class` defines LD as passenger vehicles (Class 1-2), MD as medium-duty (Class 3-6), and HD as heavy-duty (Class 7-8). It describes maximum physical access, not station capacity or every other access condition.

Source: https://afdc.energy.gov/data_download/alt_fuel_stations_format

`cmn/enums/vehicle_class.py` defines LD, MD, HD and UNKNOWN, ranked LD < MD < HD. Public access plus a known vehicle class within the facility maximum passes access for LD vehicles. MD/HD retain the existing truck-clearance review: a maximum or truck-parking flag alone does not prove bay clearance. A vehicle above the maximum fails. Missing/unrecognized values remain UNKNOWN. ALL is retained only as an explicitly recorded legacy station allowance.

Legacy CAR is interpreted as LD; MEDIUM_TRUCK as MD; HEAVY_TRUCK as HD. VAN is a body style, not a verified NLR class, and remains UNKNOWN. Interpretation does not rewrite saved values. Original values stay visible and can be saved unchanged. The form suggests LD/MD/HD for new or explicitly corrected entries; users must verify their actual vehicle class.

Both JSON and SSR vehicle CRUD accept NLR codes. Evaluation evidence includes the raw and interpreted values. No database migration or importer rerun is required. Restart the server to load changed application code.

## Layout

- `cmn/domain/`: the 12 domain entities present at the start of this change, plus entity validation.
- `cmn/domain/value_objects/`: Location and DailyTime.
- `cmn/enums/`: ConnectorFamily, VehicleClass, CheckStatus, OverallStatus and ReasonCode.
- `cmn/contracts/`: snapshots, repository contracts, errors and evaluation result dataclasses. Evaluation enums are re-exported from their former contract module for compatibility, but defined only in enums.
- `cmn/application/` and `cmn/services/`: use cases and pure evaluation logic.

Prior user commit 3f331c9 removed the Adapter domain class. This change preserves that removal; the adapter ORM/table and 13-table/65-column schema are unchanged. All application imports and architecture tests use the new packages.

## Existing data

The sample retains its original CAR vehicles and 7 LD / 13 missing facility maxima. Under the new interpretation, 3 public LD facilities pass access for CAR profiles. Other facilities need review for missing maxima or restricted eligibility. Connector, payment and opening checks still independently affect the final status.

The old synthetic demo stores VAN for vehicle and facility limits. It is no longer a verified LD example: A/B/E become NEEDS_REVIEW where access is unknown; definite failures still take precedence. Neither the seed script nor its stored data is changed. Known-pass unit scenarios explicitly use LD in temporary fixtures.
