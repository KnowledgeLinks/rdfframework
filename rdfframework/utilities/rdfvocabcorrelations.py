""" Module contains RDF vocabulary correlations """

LABEL_FIELDS = ['skos_prefLabel',
                'schema_name',
                'skos_altLabel',
                'schema_alternateName',
                'foaf_labelproperty',
                'rdfs_label',
                'mads_authoritativeLabel',
                'hiddenlabel']
DESCRIPTION_FIELDS = ['skos_definition', 'schema_description', 'rdfs_comment']
NOTE_FIELDS = ['skos_note',
               'schema_disambiguatingDescription',
               'bf_note']
PROP_FIELDS = ['rdfs_comment']
VALUE_FIELDS = ['rdf_value',
                'rdfs_value',
                'rdfs_label']
DOMAIN_FIELDS = ['schema_domainIncludes', 'rdfs_domain']
RANGE_FIELDS = ['schema_rangeIncludes', 'rdfs_range']
PROP_RDF_TYPES = ['rdf_Property', 'owl_ObjectProperty' ]
RDF_CLASSES = ['rdfs_Class', 'rdf_Class', 'owl_Class']
INFERRED_CLASS_PROPS = ['rdfs_subClassOf']
