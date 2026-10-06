# PluggedIn

Figuring out whether a given driver can actually charge at a given station.

## Background

Canada has several open datasets listing public EV charging stations. Every one answers the same question — where the chargers are. None answer the question drivers actually have: whether *this* vehicle, held by *this* driver, arriving at *this* hour, can pull in and plug in.

The data isn't missing. The meaning is.

## The problems

**Connector names don't match.** The federal dataset writes `J1772COMBO`, every app writes "CCS", standards say "SAE Combo". Query one with another's vocabulary and you get zero rows — which looks like an empty result, not a mismatch. The `TESLA` value also covers both AC and DC, so the field can't tell you whether a station is fast.

**Access rules are prose.** `"9am-5pm M-F"` decides whether a station exists at all for a truck arriving at 2am. It's a string. Nothing can reason over it.

The cost: carriers who can't tell whether an electric van covers their route buy diesel instead.

## What it does

Given a vehicle, a driver's memberships, and a route, SPARQ returns the usable stations, the longest stretch with none, and what would close it — usually an adapter or one more membership.

"Usable" isn't a column. It's derived by walking from driver to memberships, across roaming agreements, into a network's stations, down to connector type, and back to what the vehicle accepts. No single record holds the answer, which is why this is a graph.

## Data

Stations from the NLR Alternative Fuel Stations API (`country=CA`), cross-checked against Open Charge Map and City of Vancouver open data.

## Status

Course project for CSC 501, University of Victoria. Scoped to BC and one or two highway corridors.
