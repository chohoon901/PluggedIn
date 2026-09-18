# Can I Plug?

Figuring out whether a given driver can actually charge at a given station.

## Background

Canada has several open datasets listing public EV charging stations. Every one answers the same question — where the chargers are. None answer the question drivers actually have: whether *this* vehicle, held by *this* driver, arriving at *this* hour, can pull in and plug in.

The data isn't missing. The meaning is.

## The problems

**Connector names don't match.** The federal dataset writes `J1772COMBO`, every app writes "CCS", standards say "SAE Combo". Query one with another's vocabulary and you get zero rows — which looks like an empty result, not a mismatch. The `TESLA` value also covers both AC and DC, so the field can't tell you whether a station is fast.

**Roaming agreements aren't published.** Whether a FLO card opens a ChargePoint station is a fact about two networks, not either station, so it doesn't fit in a station table. We haven't found it in any dataset — and it's often what decides usability.

**Access rules are prose.** `"9am-5pm M-F"` decides whether a station exists at all for a truck arriving at 2am. It's a string. Nothing can reason over it.

The cost: carriers who can't tell whether an electric van covers their route buy diesel instead.

## What it does

Given a vehicle, a driver's memberships, and a route, SPARQ returns the usable stations, the longest stretch with none, and what would close it — usually an adapter or one more membership.

"Usable" isn't a column. It's derived by walking from driver to memberships, across roaming agreements, into a network's stations, down to connector type, and back to what the vehicle accepts. No single record holds the answer, which is why this is a graph.

## Stack

Python for ingest and reconciliation. PostgreSQL for the relational stage, mostly as a comparison baseline. RDFLib to generate triples, loaded into a triple store (Fuseki or GraphDB, undecided) for SPARQL.

Ontology authored in Protégé, kept inside OWL 2 RL — we need `owl:sameAs`, inverse properties, and property chains, and RL keeps reasoning tractable. Terms align to OCPI where it covers the concept.

## Data

Stations from the NLR Alternative Fuel Stations API (`country=CA`), cross-checked against Open Charge Map and City of Vancouver open data. Road context from Open511-DriveBC.

Roaming agreements are curated by hand from network sites and the OCPI registry. BC has roughly ten networks, so this is tractable, but it's manual — we record source and date for every assertion.

## Status

Course project for CSC 501, University of Victoria. Scoped to BC and one or two highway corridors.
