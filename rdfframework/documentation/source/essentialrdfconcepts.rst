Essential RDF concepts
======================
*Turtle RDF notation will be used throughout the documentation. However the the application files do not need to be written in turtle notation.*

There are a few RDF concepts that are essential to understanding how the application is defined. These are:

* The Triple Pattern
* RDF classes
* RDF properties
* rdfs domains
* rdfs ranges

The Triple Pattern
------------------

RDF data is written in a triple pattern that has a specific order. The items in the pattern form a sentence composed of a subject, predicate and object. 
**Throughout the documentation and in the framework these items will be referred to repeatly.**

**Example**

+-------------------+------------------+----------------------------+
| **subject**       | **predicate**    | **object**                 |
+-------------------+------------------+----------------------------+
| John's            | phone number is  | 555-555-1234               |
+-------------------+------------------+----------------------------+
| <http://.../john> | schema:telephone | "555-555-1235"^^xsd:string |
+-------------------+------------------+----------------------------+

The **subject**, in SQL/Relational database terms, is a **uuid** (universal unique identifier).

.. note::
    The **subject/IRI/URI** value itself may contain human readable information but it is not necessary that it does. Sometimes it causes confusion if it does! For example. If you look at **<http://.../Topic/Battle-of-Gettysburg>** it may lead one to think that we are refering to the **Battle of Gettysburg** as a **topic** to be used for categorization. However, the **Battle of Gettysburg** can a **calendar event**, a **battle**, a **historical event**, etc. It would be better to list it solely as **<http://.../Battle-of-Gettysburg>**. This will avoid creating multiple **URIs/IRIs** for one particular concept.

.. warning::

    Blanknodes have a **subject** value that is a variable specific to the triplestore. Blanknode subjects will **NOT** function as **uuids**. Blanknodes are used to group properties together for a particular **subject** i.e. if you have the **subject/IRI/URI** **<http://.../john>** as above and you want to add an address for him you can group all the address properties in one blanknode as below::
   
        <http://.../john> schema:address [
                schema:Country 	"USA";
                schema:addressLocality	"Mountain View";
                schema:addressRegion	"CA";
                schema:postalCode	Text 	"94043";
                schema:streetAddress	"1600 Amphitheatre Pkwy"
           ] .

The **predicate** is a RDF vocabulary term that is in the form of URI/IRI that describes the relationship between the **subject** and **object** 

The **object** is a either another **IRI**, a  **blankenode** or a **literal** (a string, date, number etc)

RDF classes
-----------
A class represents a category of subjects. Examples of classes are organizations, people, and events. When a **subject** that is identified as a class
it is one instance of the larger category and shares many properties with other **subjects**.

**schema:Organization** is a RDF class for describing organization.

Identifying **<http://example.com/org#a>** **rdf:type** **schema:Organization** means that **<http://example.com/orf#a>** is an **organization**.

RDF properties
--------------
RDF properties are used as the predicates of the triple pattern. In general they are used to 
describe the relationships between RDF classes.

.. note::

   A property can be used in multiple classes. i.e. schema:name can be used with schema:Person, schema:Organization, etc.

.. warning::

   Throughout the code property and predicate are used interchangeably.

rdfs:domains
------------
The **rdfs:domain** declaration is essential to defining an application within 
the framework. The **domain** statement tells what type of rdf:Class should be in the **subject** position of a triple. For example: ::

    schema:email rdfs:domain schema:Person .

The above statement means that when the **schema:email** property is used that the subject of the triple should be a schema:Person. ::

    <http://example.com/john> rdf:type schema:Person ;
                          schema:email "john@example.com"^^xsd:string .
               
                          
*<http://example.com/john> is a Person and we are in compliance of the specified domain rule.* ::

    <http://example.com/moby-dick> rdf:type schema:Book ;
                          schema:email "myemail@example.com"^^xsd:string .
                          
*The above triples are a violation of the specified domain rule. The point is not that a book can't have an 
email, but rather that the specified statement says that only a schema:Person should use the property schema:email.*

.. warning::
    There are RDF rules that allow for looking at subclasses and so forth but for 
    the **rdfframework** you must specifically specify each class the property will be used in. 
    
To use the schema:email property for a Person, Book and Organization specify them explicitly::

    schema:email rdfs:domain schema:Person, 
                         schema:Book, 
                         schema:Organization .
                         
rdfs:ranges
-----------
The **rdfs:range** tells us what type of rdf:Class should occupy the **object** position of the triple pattern.::

    schema:email rdfs:range xsd:string

This means that when ever a **schema:email** property is used it should have a string as the object. Having 
an URI in the object position would be a violation of the rule.

.. note::                
    For the **rdfframework** be as specific as possible for specification of the range value. If you want a 
    date value to be stored in the object position use **xsd:date**. Do not specify the range as a **literal**. 
    
If you want more than one option for the range specifically specify it.::

    schema:email rdfs:range xsd:string,
                        yourNs:EmailObject .

Next we will look at defining our **classes** and **properties** for the framework.
   
* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
