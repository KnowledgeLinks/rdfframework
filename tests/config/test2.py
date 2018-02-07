## False: Turns logging off. - True[default]: Uses default logging setup. -
## Dictionay is passed into the python logging.config.dictConfig()

LOGGING = True

## True: intelligent classes are created based off of the RDF vocabulary
## definitions and custom defintions. - False: only a basic RDF class is used.
## *Start time is increased with this on. It is required to be on for all
## advanced rdfframework functions.

TURN_ON_VOCAB = False

## secret key to be used by the Flask application security setting

SECRET_KEY = 'enter_a_secret_key_here'

## the name used for the site

SITE_NAME = 'afadfs'

## base URL for the site

BASE_URL = 'http://knowledgelinks.io/'

CONNECTIONS = [{'conn_type': 'triplestore',
  'container_dir': '/local_data',
  'graph': 'bd:nullGraph',
  'kwargs': None,
  'local_url': 'http://localhost:9999/blazegraph',
  'name': 'datastore',
  'namespace': 'kean_all',
  'namespace_params': {'quads': True},
  'python_dir': None,
  'url': 'http://localhost:9999/blazegraph',
  'vendor': 'rdflib'},
 {'conn_type': 'triplestore',
  'container_dir': '/local_data',
  'data_upload': [('vocabularies', ['rdf', 'owl', 'schema', 'bf', 'skos']),
                  ('package_all', 'bibcat.rdfw-definitions')],
  'graph': '<http://knowledgelinks.io/ns/application-framework/>',
  'local_url': 'http://localhost:9999/blazegraph',
  'name': 'active_defs',
  'namespace': 'active_defs',
  'namespace_params': {'quads': True},
  'url': 'http://localhost:9999/blazegraph',
  'vendor': 'blazegraph'},
 {'conn_type': 'triplestore',
  'container_dir': '/local_data',
  'graph': '<http://knowledgelinks.io/ns/application-framework/>',
  'local_url': 'http://localhost:9999/blazegraph',
  'name': 'all_defs',
  'namespace': 'active_defs',
  'namespace_params': {'quads': True},
  'url': 'http://localhost:9999/blazegraph',
  'vendor': 'blazegraph'},
 {'conn_type': 'triplestore',
  'container_dir': '/local_data',
  'name': 'rml',
  'namespace': 'rml_maps',
  'namespace_params': {'quads': True},
  'url': 'http://localhost:9999/blazegraph',
  'vendor': 'blazegraph'},
 {'active': False,
  'conn_type': 'search',
  'local_url': 'http://localhost:9200',
  'name': 'search',
  'url': 'http://localhost:9200',
  'vendor': 'elastic'},
 {'conn_type': 'repository',
  'local_url': 'http://localhost:8080/rest',
  'name': 'repo',
  'url': 'http://localhost:8080/rest',
  'vendor': 'fedora'}]

## Directory paths and short names for use. Each directory path is accesable
## through the RdfConfigManager() by selecting the following notation:
## RdfConfigManager.dirs.name Where the name is a short descriptive word
## descibing the directories use. There are 5 functional names used by the
## rdfframework. 1. base - a base directory for creating addtional directories
## *required 2. logs

DIRECTORIES = [{'name': 'fasdf', 'path': '/home/stabiledev/rdfw_test1'},
 {'name': 'base', 'path': '/home/stabiledev/rdfw_base'}]

## URI for an RDF namespace

NAMESPACES = {'acl': '<http://www.w3.org/ns/auth/acl#>',
 'bd': '<http://www.bigdata.com/rdf#>',
 'bf': 'http://id.loc.gov/ontologies/bibframe/',
 'dbo': 'http://dbpedia.org/ontology/',
 'dbp': 'http://dbpedia.org/property/',
 'dbr': 'http://dbpedia.org/resource/',
 'dc': 'http://purl.org/dc/elements/1.1/',
 'dcterm': 'http://purl.org/dc/terms/',
 'dpla': 'http://dp.la/about/map/',
 'edm': 'http://www.europeana.eu/schemas/edm/',
 'es': 'http://knowledgelinks.io/ns/elasticsearch/',
 'foaf': 'http://xmlns.com/foaf/0.1/',
 'kdr': 'http://knowledgelinks.io/ns/data-resources/',
 'kds': 'http://knowledgelinks.io/ns/data-structures/',
 'loc': 'http://id.loc.gov/authorities/',
 'm21': '<http://knowledgelinks.io/ns/marc21/>',
 'mads': '<http://www.loc.gov/mads/rdf/v1#>',
 'mods': 'http://www.loc.gov/mods/v3#',
 'ore': 'http://www.openarchives.org/ore/terms/',
 'owl': 'http://www.w3.org/2002/07/owl#',
 'relator': 'http://id.loc.gov/vocabulary/relators/',
 'schema': 'http://schema.org/',
 'skos': 'http://www.w3.org/2004/02/skos/core#',
 'void': 'http://rdfs.org/ns/void#',
 'xsd': 'http://www.w3.org/2001/XMLSchema#',
 'vcard': 'http://www.w3.org/2006/vcard/ns#'}


#! *** non specified attributes ***


ORGANIZATION = {'description': '',
 'name': 'knowledgeLinks.io',
 'url': 'http://knowledgelinks.io/'}

DATASET_URLS = {'bibframe_vocab_rdf': 'http://id.loc.gov/ontologies/bibframe.rdf',
 'loc_subjects_skos.nt.gz': 'http://id.loc.gov/static/data/authoritiessubjects.nt.skos.gz',
 'marc_relators_nt': 'http://id.loc.gov/static/data/vocabularyrelators.nt.zip'}