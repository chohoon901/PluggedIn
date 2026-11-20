# Synthetic boundary cases for CQ2–CQ4. These are fictional adapter records.
# In Conductor Interactive SQL, put SPARQL before this update and end it with a semicolon.
# Use this graph's IRI in CQ2–CQ4 to reproduce the fixture results.
PREFIX plug: <https://github.com/chohoon901/PluggedIn/ontology/>
PREFIX migration: <https://github.com/chohoon901/PluggedIn/migration/>
PREFIX demo: <https://github.com/chohoon901/PluggedIn/data/cq-demo/>

INSERT DATA {
  GRAPH <https://github.com/chohoon901/PluggedIn/graph/cq-demo/> {
    demo:chademo a plug:ConnectorType ; plug:connectorName "CHAdeMO" ; migration:connectorFamily "CHADEMO" .
    demo:ccs1 a plug:ConnectorType ; plug:connectorName "CCS1" ; migration:connectorFamily "CCS1" .
    demo:ccs1Alias a plug:ConnectorType ; plug:connectorName "  CCS (Type   1)  " ; migration:connectorFamily "CCS1" .
    demo:j1772 a plug:ConnectorType ; plug:connectorName "J1772" ; migration:connectorFamily "J1772" .
    demo:vehicle a plug:Vehicle ;
      plug:vehicleModel "Synthetic CCS1 vehicle" ; plug:vehicleAccepts demo:ccs1 .
    demo:twoInlets a plug:Vehicle ;
      plug:vehicleModel "Synthetic direct and adapter paths" ; plug:vehicleAccepts demo:ccs1, demo:chademo .

    demo:eligible a plug:Station ; plug:stationName "Synthetic adapter candidate" ;
      plug:city "Vancouver" ; migration:portsCompleteness "COMPLETE" ; plug:hasPort demo:dc150 .
    demo:dc150 a plug:Port ; plug:hasConnectorType demo:chademo ;
      plug:currentType "DC" ; plug:powerKw 150.0 .

    demo:boundary a plug:Station ; plug:stationName "Synthetic power boundary" ;
      plug:city "Vancouver" ; migration:portsCompleteness "PARTIAL" ;
      plug:hasPort demo:dc100, demo:ac150 .
    demo:dc100 a plug:Port ; plug:hasConnectorType demo:chademo ;
      plug:currentType "DC" ; plug:powerKw 100.0 .
    demo:ac150 a plug:Port ; plug:hasConnectorType demo:j1772 ;
      plug:currentType "AC" ; plug:powerKw 150.0 .

    demo:hasDirect a plug:Station ; plug:stationName "Synthetic direct alternative" ;
      plug:city "Vancouver" ; migration:portsCompleteness "COMPLETE" ;
      plug:hasPort demo:directAlias, demo:adapterPortWithDirect .
    demo:directAlias a plug:Port ; plug:hasConnectorType demo:ccs1Alias ; plug:currentType "DC" .
    demo:adapterPortWithDirect a plug:Port ; plug:hasConnectorType demo:chademo ; plug:currentType "DC" .

    demo:unknown a plug:Station ; plug:stationName "Synthetic current unknown" ;
      plug:city "Vancouver" ; migration:portsCompleteness "COMPLETE" ;
      plug:hasPort demo:unknownCurrent, demo:adapterPortWithUnknown .
    demo:unknownCurrent a plug:Port ; plug:hasConnectorType demo:ccs1Alias .
    demo:adapterPortWithUnknown a plug:Port ; plug:hasConnectorType demo:chademo ; plug:currentType "DC" .

    demo:adapterForward a plug:Adapter ; plug:adapterModel "Synthetic directed adapter" ;
      plug:fromConnector demo:chademo ; plug:toConnector demo:ccs1 ;
      migration:adapterCurrentType "DC" ; migration:adapterEvidence "Synthetic test fixture" .
    demo:adapterReverse a plug:Adapter ; plug:adapterModel "Synthetic reverse-only adapter" ;
      plug:fromConnector demo:ccs1 ; plug:toConnector demo:chademo ;
      migration:adapterCurrentType "DC" ; migration:adapterEvidence "Synthetic test fixture" .
    demo:adapterUnconfirmed a plug:Adapter ; plug:adapterModel "Synthetic unverified adapter" ;
      plug:fromConnector demo:chademo ; plug:toConnector demo:ccs1 ; migration:adapterCurrentType "DC" .
    demo:adapterWrongCurrent a plug:Adapter ; plug:adapterModel "Synthetic mismatched current adapter" ;
      plug:fromConnector demo:chademo ; plug:toConnector demo:ccs1 ; migration:adapterCurrentType "AC" .
  }
}
