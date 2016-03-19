Understanding the RDF Application Files
***************************************

Contents
========
.. toctree::
   :maxdepth: 1
   
   definingclasses
   definingprops
   
Essential RDF concepts
======================
*Turtle RDF notation will be used throughout the documentation. However the the application files do not need to be written in turtle notation. For our purposes it is the easiest to read and understand.*

There are a few RDF concepts that are essential to understanding how the application is defined. These are:

* The Triple Pattern
* RDF classes
* RDF properties
* rdfs domains
* rdfs ranges

The Triple Pattern
==================

RDF data is written in a triple pattern that has a specific order. The items in the pattern form a sentance composed of a subject, predicate and object. **Throughout the documentation and in the framework these items will be referred to over and over again.

**Example**

+-------------------+------------------+----------------------------+
| **subject**       | **predicate**    | **object**                 |
+-------------------+------------------+----------------------------+
| John's            | phone number is  | 555-555-1234               |
+-------------------+------------------+----------------------------+
| <http://.../john> | schema:telephone | "555-555-1235"^^xsd:string |
+-------------------+------------------+----------------------------+

The **subject** is SQL database terms is the **uuid**(universal unique identifier) 

The **predicate** is a rdf vocabulary term that is in the form of URI/IRI that describes the relationship between the **subject** and **object**

The **object** is a either another IRI or a literal (a string, date, number etc)

RDF classes
===========
A class represents a categorization of subjects. i.e. organizations, people, events, etc. Where a **subject** that is identified by a class is one instance of the large grouping.

**schema:Organization** is a rdf class for describing organization.

Identifying **<http://example.com/org#a>** **rdf:type** **schema:Organization** means that **<http://example.com/orf#a>** is an **organization**.

RDF properties
==============
Rdf properties are used as the predicates of the triple pattern. In general they are used to describe how one rdf class relates to another rdf class.

.. note::

   A property can be used to in multiple classes. i.e. schema:name can be used with schema:Person, schema:Organization, etc.

.. warning::

   Throughout the code property and predicate are used interchangeably.

rdfs domains
============
The **rdfs:domain** declartion is essential to defining an application wih the framework. The **domain** statement tells what type of rdf:Class should be in the **subject** position of a triple. For example: ::

    schema:email rdfs:domain schema:Person .

The above statement means that when the **schema:email** property is used that the subject of the triple should be a schema:Person. ::

    <http://example.com/john> rdf:type schema:Person ;
                          schema:email "john@example.com"^^xsd:string .
               
                          
*<http://example.com/john> is a Person and we are in compliance of the specified domain rule.* ::

    <http://example.com/moby-dick> rdf:type schema:Book ;
                          schema:email "myemail@example.com"^^xsd:string .
                          
*The above triples are a violation of the specified domain rule. The point is not that a book can't have an email, but rather that the specified rule says that only a schema:Person should use the property schema:email.*

.. warning::
    Their are rdf rules that allow for looking at subclasses and so forth but for the **rdfframework** you must specifically specify each class the property will be used in. 
    
To use the schema:email property for a Person, Book and Organization specifiy them explicitly::

    schema:email rdfs:domain schema:Person, 
                         schema:Book, 
                         schema:Organization .
                         
rdfs ranges
===========
The **rdfs:range** tells us what type of rdf:Class should occupy the **object** position of the triple pattern.::

    schema:email rdfs:range xsd:string

This means that when ever a the **schema:email** property is used it should have a string as the object. Having a URI in the object position would be a violation of the rule.

.. note::                
    For the **rdfframework** be as specific as possible for specification of the range value. If you want a date value to be stored in the object position use **xsd:date**. Do not specify the range as a **literal**. 
    
If you want more than one option for the range specifically specify it.::

    schema:email rdfs:range xsd:string,
                        yourNs:EmailObject .

Next we will look at defining our **classes** and **properties** for the framework.

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`