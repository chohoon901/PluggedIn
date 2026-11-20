# Run after loading the sample20 RDF into the named graph below. In Conductor
# Interactive SQL, put SPARQL before this update and end it with a semicolon.
# Connector families follow cmn/enums/connector_family.py for the sample's raw names.
# On 2026-11-19, Tesla Canada's location 13658 listed 16 Superchargers at 2710 Kaslo St
# with an advertised maximum of 250 kW for the charging group. Ford Canada's SKU
# VRK9Z10E826A lists NACS DC charging into a CCS1 vehicle inlet. The adapter entry
# records connector direction and current for catalog queries.
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

    ?fordAdapter a plug:Adapter ;
      plug:adapterModel "Ford Fast Charging Adapter (NACS) (VRK9Z10E826A)" ;
      plug:manufacturer "Ford" ;
      plug:fromConnector connector:6 ;
      plug:toConnector connector:2 ;
      migration:adapterCurrentType "DC" ;
      migration:adapterEvidence <https://www.ford.ca/product/ford-fast-charging-adapter-nacs-p2999073032> .
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
    GRAPH <https://github.com/chohoon901/PluggedIn/graph/> {
      connector:6 a plug:ConnectorType ; plug:connectorName ?fromName .
      connector:2 a plug:ConnectorType ; plug:connectorName ?toName .
      FILTER (STR(?fromName) = "NACS / Tesla Supercharger" && STR(?toName) = "J1772COMBO")
    }
    BIND (catalog:ford-vrk9z10e826a AS ?fordAdapter)
  }
}
