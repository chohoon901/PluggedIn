# Run after loading the sample20 RDF into the named graph below. In Conductor
# Interactive SQL, put SPARQL before this update and end it with a semicolon.
# Connector families follow cmn/enums/connector_family.py for the sample's raw names.
# On 2026-11-19, Tesla Canada's location 13658 listed 16 Superchargers at 2710 Kaslo St
# with an advertised maximum of 250 kW for the charging group. Ford Canada's SKU
# VRK9Z10E826A lists NACS DC charging into a CCS1 vehicle inlet.
# Prism Engineering reports two 50 kW DC chargers at Norgate Park from its
# installation project. The sample lists CCS1 and CHAdeMO at the site.
# The other catalog entries use A2Z EV's Stellar Pro and Legacy (CCS1 variant)
# specifications and Tesla Canada's SAE J1772 adapter specifications.
PREFIX plug: <https://github.com/chohoon901/PluggedIn/ontology/>
PREFIX migration: <https://github.com/chohoon901/PluggedIn/migration/>
PREFIX station: <https://github.com/chohoon901/PluggedIn/data/sample20/Station/>
PREFIX port: <https://github.com/chohoon901/PluggedIn/data/sample20/Port/>
PREFIX connector: <https://github.com/chohoon901/PluggedIn/data/sample20/ConnectorType/>
PREFIX catalog: <https://github.com/chohoon901/PluggedIn/data/catalog/Adapter/>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

INSERT {
  GRAPH <https://github.com/chohoon901/PluggedIn/graph/> {
    ?connector migration:connectorFamily ?family .

    ?kasloPort migration:operatorPublishedPowerKw 250.0 ;
      migration:powerEvidenceSource <https://www.tesla.com/en_CA/findus/location/supercharger/13658> ;
      migration:powerEvidenceScope "Charging group maximum advertised by operator" ;
      migration:powerEvidenceCheckedOn "2026-11-19"^^xsd:date .

    ?norgatePort migration:installedChargerPowerKw 50.0 ;
      migration:powerEvidenceSource <https://www.prismengineering.com/projects/district-of-north-vancouver-ev-design-and-implementation/> ;
      migration:powerEvidenceScope "Installed DC charger rating" ;
      migration:powerEvidenceCheckedOn "2026-11-20"^^xsd:date .

    ?adapter a plug:Adapter ;
      plug:adapterModel ?model ;
      plug:manufacturer ?manufacturer ;
      plug:fromConnector ?from ;
      plug:toConnector ?to ;
      migration:adapterCurrentType ?currentType ;
      migration:adapterEvidence ?evidence .
  }
}
WHERE {
  {
    VALUES (?connector ?rawName ?family) {
      (connector:1 "J1772" "J1772"^^xsd:string)
      (connector:2 "J1772COMBO" "CCS1"^^xsd:string)
      (connector:3 "TESLA" "NACS"^^xsd:string)
      (connector:4 "Tesla (Model S/X)" "NACS"^^xsd:string)
      (connector:5 "CCS (Type 1)" "CCS1"^^xsd:string)
      (connector:6 "NACS / Tesla Supercharger" "NACS"^^xsd:string)
      (connector:7 "CHADEMO" "CHADEMO"^^xsd:string)
      (connector:8 "CHAdeMO" "CHADEMO"^^xsd:string)
      (connector:9 "Type 1 (J1772)" "J1772"^^xsd:string)
    }
    GRAPH <https://github.com/chohoon901/PluggedIn/graph/> {
      ?connector a plug:ConnectorType ; plug:connectorName ?name .
    }
    FILTER (STR(?name) = ?rawName)
  }
  UNION
  {
    GRAPH <https://github.com/chohoon901/PluggedIn/graph/> {
      station:4 a plug:Station ;
        plug:street ?street ; plug:city ?city ; plug:hasPort ?kasloPort .
      ?kasloPort a plug:Port ; plug:currentType ?current ; plug:hasConnectorType connector:6 .
      FILTER (?kasloPort = port:9 && STR(?street) = "2710 Kaslo St" &&
              STR(?city) = "Vancouver" && STR(?current) = "DC")
    }
  }
  UNION
  {
    VALUES (?norgatePort ?norgateConnector) {
      (port:12 connector:8)
      (port:13 connector:5)
    }
    GRAPH <https://github.com/chohoon901/PluggedIn/graph/> {
      station:7 a plug:Station ;
        plug:street ?norgateStreet ; plug:city ?norgateCity ; plug:hasPort ?norgatePort .
      ?norgatePort a plug:Port ; plug:currentType ?norgateCurrent ;
        plug:hasConnectorType ?norgateConnector .
    }
    FILTER (STR(?norgateStreet) = "1578 Garden Ave" &&
            STR(?norgateCity) = "District of North Vancouver" && STR(?norgateCurrent) = "DC")
  }
  UNION
  {
    VALUES (?adapter ?model ?manufacturer ?from ?fromName ?to ?toName ?currentType ?evidence) {
      (catalog:ford-vrk9z10e826a "Ford Fast Charging Adapter (NACS) (VRK9Z10E826A)" "Ford"
       connector:6 "NACS / Tesla Supercharger" connector:2 "J1772COMBO" "DC"
       <https://www.ford.ca/product/ford-fast-charging-adapter-nacs-p2999073032>)
      (catalog:a2z-stellar-pro "A2Z EV Stellar Pro" "A2Z EV"
       connector:4 "Tesla (Model S/X)" connector:1 "J1772" "AC"
       <https://a2zev.com/products/nacs-j1772>)
      (catalog:a2z-legacy-ccs1 "A2Z EV Legacy (CCS1)" "A2Z EV"
       connector:2 "J1772COMBO" connector:7 "CHADEMO" "DC"
       <https://a2zev.com/products/ccs1-to-chademo>)
      (catalog:tesla-sae-j1772 "Tesla SAE J1772 Charging Adapter" "Tesla"
       connector:1 "J1772" connector:3 "TESLA" "AC"
       <https://shop.tesla.com/en_ca/product/sae-j1772-charging-adapter>)
    }
    GRAPH <https://github.com/chohoon901/PluggedIn/graph/> {
      ?from a plug:ConnectorType ; plug:connectorName ?storedFromName .
      ?to a plug:ConnectorType ; plug:connectorName ?storedToName .
    }
    FILTER (STR(?storedFromName) = ?fromName && STR(?storedToName) = ?toName)
  }
}
