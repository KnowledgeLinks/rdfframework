"""OMNIBUS CONFIG file for KnowlegeLinks.io applications"""
# enter a secret key for the flask application instance
import os
import inspect

# SECRET KEY for flask application
SECRET_KEY = "enter_a_secret_key_here"

# Organzation information for the hosting org.
ORGANIZATION = {
    "name": "knowledgeLinks.io",
    "url": "http://knowledgelinks.io/",
    "description": ""
}

# The name used for the site
SITE_NAME = "TEST-RDFFRAMEWORK"

# URL used in generating IRIs
BASE_URL = "http://knowledgelinks.io/"

# Path to where local data files are stored, as python sees the file path.
# This variable is paired with the 'container_dir' in a TRIPLESTORE declaration.
# Without this linkage the only way to send a file through to the triplestore
# is via a REST call that does not work well for large and large numbers of
# files
#! The docker container should be volume mapped to this location.
#! Example: -v {python_dir}:{docker_container_dir}
#!          -v /home/username/local_data:/local_data
LOCAL_DATA_PATH = os.path.join(os.path.expanduser("~"), 'local_data')
CACHE_DATA_PATH = os.path.join(os.path.expanduser("~"), 'cache_data')
CONFIG_FILE_PATH = os.path.split(inspect.stack()[0][1])[0]

# urls for use internal to the config file use
__blazegraph_url__ = "http://localhost:9999/blazegraph"
__blazegraph_local_url__ = "http://localhost:9999/blazegraph"
__es_url__ = "http://localhost:9200"
__es_local_url__ = "http://localhost:9200"
__fedora_url__ = "http://localhost:8080/rest"
__fedora_local_url__ = "http://localhost:8080/rest"

CONNECTIONS = [
    # Declaration for the triplestore that stores data for the application
    {
        "conn_type": "triplestore",
        "name": "datastore",
        "vendor": "rdflib",
        "url": __blazegraph_url__,
        "local_url": __blazegraph_local_url__,
        # The 'container_dir' is linked with the LOCAL_DATA_PATH declaration
        # This is how the triplestore sees the file path.
        "container_dir": "local_data",
        "namespace": "kean_all", # "kb",
        "graph": "bd:nullGraph",
        "namespace_params": {"quads": True},
        "data_upload": [
                ("directory", os.path.join(os.path.realpath(".."),
                                           "data",
                                           "rdfw-definitions")),
                ("data_file", ""),
                ("package_all", "bibcat.maps")
        ]
    },
    # Declaration for the triplestore storing the active rdf vocab and
    # rdfframework files that define the applications classes, forms, and API
    {
        "conn_type": "triplestore",
        "name": "active_defs",
        "vendor": "rdflib",
        "url": __blazegraph_url__,
        "local_url": __blazegraph_local_url__,
        "container_dir": "local_data",
        "graph": "<http://knowledgelinks.io/ns/application-framework/>",
        "namespace": "active_defs",
        "namespace_params": {"quads": True},
        "data_upload": [("vocabularies", "all")]
    },
    # Declaration for the triplestore storing the vocab definitions whether in
    # use or not. This provides an easily queriable source for vocabularies.
    {
        "conn_type": "triplestore",
        "name": "all_defs",
        "vendor": "blazegraph",
        "url": __blazegraph_url__,
        "local_url": __blazegraph_local_url__,
        "container_dir": "local_data",
        "graph": "<http://knowledgelinks.io/ns/application-framework/>",
        "namespace": "active_defs",
        "namespace_params": {"quads": True}
    },
    # RML database for storing RML defintions
    {
        "conn_type": "triplestore",
        "name": "rml",
        "vendor": "blazegraph",
        "url": __blazegraph_url__,
        # "local_url": __blazegraph_local_url__,
        "container_dir": "local_data",
        "namespace": "rml_maps",
        "namespace_params": {"quads": True}
    },
    # connection for indexing and search
    {
        "conn_type": "search",
        "name": "search",
        "active": False,
        "vendor": "elastic",
        "url": __es_url__,
        "local_url": __es_local_url__
    },
    # digital repository connection
    {
        "conn_type": "repository",
        "name": "repo",
        "vendor": "fedora",
        "url": __fedora_url__,
        "local_url": __fedora_local_url__
    }
]


# RML mappings locations to be used in the application.
# This is a list of tuples:
#    [("package" or "directory", "package name or directory path")]
RML_MAPS = [
    ("package_all", "bibcat.maps"),
    ("directory", None)
    ]
RDF_DEFS = [
    ("directory", os.path.join(os.path.realpath(".."),
                               "data",
                               "rdfw-definitions")),
    ("vocabularies", ["rdf", "owl", "rdfs", "schema", "skos", "bf"]),
    ("package_all", "bibcat.maps")
    ]

# Declaration for the triplestore storing the rdf vocab and rdfframework files
# that define the applications classes, forms, and APIs

REPOSITORY_URL = "http://localhost:8080/rest"

# Dictionary of web accessibale datasets
DATASET_URLS = {
    "loc_subjects_skos.nt.gz":
            "http://id.loc.gov/static/data/authoritiessubjects.nt.skos.gz",
    "marc_relators_nt":
            "http://id.loc.gov/static/data/vocabularyrelators.nt.zip",
    "bibframe_vocab_rdf":
            "http://id.loc.gov/ontologies/bibframe.rdf"
}

RDF_NAMESPACES = {
    "kds": "http://knowledgelinks.io/ns/data-structures/",
    "kdr": "http://knowledgelinks.io/ns/data-resources/",
    "bf": "http://id.loc.gov/ontologies/bibframe/",
    "dpla": "http://dp.la/about/map/",
    "skos": "http://www.w3.org/2004/02/skos/core#",
    "loc": "http://id.loc.gov/authorities/",
    "mods": "http://www.loc.gov/mods/v3#",
    "es": "http://knowledgelinks.io/ns/elasticsearch/",
    "edm": "http://www.europeana.eu/schemas/edm/",
    "schema": "http://schema.org/",
    "xsd": "http://www.w3.org/2001/XMLSchema#",
    "ore": "http://www.openarchives.org/ore/terms/",
    "owl": "http://www.w3.org/2002/07/owl#",
    "void": "http://rdfs.org/ns/void#",
    "dcterm": "http://purl.org/dc/terms/",
    "dc": "http://purl.org/dc/elements/1.1/",
    "dbo": "http://dbpedia.org/ontology/",
    "dbp": "http://dbpedia.org/property/",
    "dbr": "http://dbpedia.org/resource/",
    "m21": "<http://knowledgelinks.io/ns/marc21/>",
    "acl": "<http://www.w3.org/ns/auth/acl#>",
    "bd": "<http://www.bigdata.com/rdf#>",
    "relator": "http://id.loc.gov/vocabulary/relators/",
    "foaf": "http://xmlns.com/foaf/0.1/",
    "mads": "<http://www.loc.gov/mads/rdf/v1#>"
}



# Default data to load at initial application creation
FRAMEWORK_DEFAULT = []

DATE_FORMAT = {
    "python": "",
    "json": ""
}
