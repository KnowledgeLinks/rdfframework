# knowledgelinks.io RDF Framework for web applications

[![Build Status](https://travis-ci.org/KnowledgeLinks/rdfframework.svg)](https://travis-ci.org/KnowledgeLinks/rdfframework)


Development Documentation is available on the Knowledgelinks.io's  
[website](http://knowledgelinks.io/products/rdfframework/index.html).

This application reads an RDF data file that describes a web application using the [knowledgelinks.io][KL] data-structures RDF Vocabulary.

###RDF Namespaces
PREFIX kds: http://knowledgelinks.io/ns/data-structures/

PREFIX kdr: http://knowledgelinks.io/ns/data-resources/

## Introduction
The versitility of RDF allows a simple means for describing anything. Using our developed vocabulary for describing a web application we are building a framework for a highly customizable, secure and a fully RDF/bigdata integrated web application framework. Since RDF databases do not have an inherent forced data structures like SQL Databases (i.e. table defs, primary keys, etc) they have great flexibility, however they are left open to having a lot of junk data. To solve this problem the kds vocabulary completely integrates with the any other RDF vocabulary (i.e. schema, FOAF, etc.) by augmenting those vocabularies with how they are to be used in the specific application. 

## Installation
This is set to run as a python package but does not need to be installed as a package. Add this repository as a git submodule 
Then add sys.path.append(os.path.realpath('./....path-to..../rdfframework')) to your root init or application start-up

### From source


## Configuration


## Usage



[KL]: http://knowledgelinks.io/
[FEDORA]: http://fedora-commons.org/
[ISLANDORA_CA]: http://islandora.ca/
[OPENBADGE]: http://openbadges.org/
[PY3]: https://www.python.org/
[VRTENV]: http://virtualenv.readthedocs.org/
