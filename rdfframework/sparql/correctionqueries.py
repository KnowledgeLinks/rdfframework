correction_queries = [
"""
#Correct ShelfMark
DELETE
{
	?s ?p 	<http://id.loc.gov/ontologies/bibframe/ShelfMarkLLC>
}
INSERT
{
	?s ?p 	<http://id.loc.gov/ontologies/bibframe/ShelfMarkLcc>
}
WHERE
{
    ?s ?p 	<http://id.loc.gov/ontologies/bibframe/ShelfMarkLLC>
}
""",
"""
# convert 'bf:itemOf' to 'bf:hasItem'
DELETE
{
	?instance bf:itemOf ?work
}
INSERT
{
	?work bf:hasItem ?instance
}
WHERE
{
    ?instance bf:itemOf ?work
}
""",
"""
# convert 'bf:instanceOf' to 'bf:hasInstance'
DELETE
{
	?instance bf:instanceOf ?work
}
INSERT
{
	?work bf:hasInstance ?instance
}
WHERE
{
    ?instance bf:instanceOf ?work
}
""",
"""
# Add an rdfs:label to all of the works that do not have one
INSERT
{
    ?work rdfs:label ?f
}
WHERE
{
    # SAMPLE function will return one of the labels from the instances
    SELECT ?work (SAMPLE(?inst_label) as ?f)
    {
        ?work a bf:Work .
        OPTIONAL {
            ?work rdfs:label ?work_label 
        }
        # values statement below will return false if there is no rdfs:label
        VALUES (?work ?work_label)
        { (UNDEF false) }
        # get all of the labels of the associated instances to the work
        { 
            ?work bf:hasInstance ?instance.
            ?instance rdfs:label ?inst_label .
        } UNION {
            ?instance bf:instanceOf ?work .
            ?instance rdfs:label ?inst_label .
        }
        FILTER (?work_label=false)
    }
    group by ?work
}
"""
]