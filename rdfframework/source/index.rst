.. RdfFramework documentation master file, created by
   sphinx-quickstart on Thu Mar 17 22:03:23 2016.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

rdfframework 
**************************
*Developed by KnowledgeLinks.io*

*** *** *** STILL IN DEVELOPMENT *** *** ***

This application reads a RDF data file that describes a web application using the `knowledgelinks.io <http://knowledgelinks.io>`_ data-structures RDF Vocabulary. The current test web application is for issuing and hosting `Open Badges <http://openbadges.org/>`_.


.. toctree::
   :maxdepth: 4



Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

RDF Namespaces
==================
+------------+----------------------------------------------+
| **PREFIX** | **URI**                                      |
+------------+----------------------------------------------+
| **kds**    | http://knowledgelinks.io/ns/data-structures/ |
+------------+----------------------------------------------+
| **kdr**    | http://knowledgelinks.io/ns/data-resources/  |
+------------+----------------------------------------------+

Introduction
==================
The versitility of RDF allows a simple means for describing anything. Using our developed vocabulary for describing a web application we are building a framework for a highly customizable, secure and a fully RDF/bigdata integrated web application. 

Since RDF databases do not have inherent forced data structures like SQL Databases (i.e. table defs, primary keys, etc) they have great flexibility. However, with the increased flexibility comes other challenges:

- Challenge of consistant object saving
- Redudant data
- Data consistancy
- Consistancy between modules reading and saving data

To solve this problem the kds vocabulary completely integrates with the any other RDF vocabulary (i.e. schema, FOAF, etc.) by augmenting those vocabularies with how they are to be used in the specific application. 

RdfFramework - *Main Application Controller*
=========================

.. automodule:: rdfframework.framework
    :members:
    
RdfClass - *Contoller for a rdf:Class*
=========================
    
.. automodule:: rdfframework.rdfclass
    :members:
    
RdfProperty - *Class for controlling a rdf:Property*
=========================
.. automodule:: rdfframework.rdffproperty
    :members:
    
RdfDataType - *Class for formating an Object of a triple*
=========================
.. automodule:: rdfframework.rdfdatatype
    :members: