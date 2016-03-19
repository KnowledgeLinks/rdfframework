Defining RDF Classes in the Framework
*************************************
After you have decided what rdf:Classes that you will be using in the application it is now time to start specifying them. 

.. note:
    Don't worry if you are unsure about all the classes that you want to use. To add additional classes later you will just need to update the the definition file and restart the application. 
    
Steps
-----
1. Open a text editor and add your turtle prefixes for the namespaces that you will be using::

    # Required namespaces
    @prefix acl: <http://www.w3.org/ns/auth/acl#> .
    @prefix kds: <http://knowledgelinks.io/ns/data-structures/> .
    @prefix kdr: <http://knowledgelinks.io/ns/data-resources/> .
    @prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
    @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
    @prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
    
    # Any addtional namespaces
    @prefix schema: <https://schema.org/> .
    
2. Next add the basic information about the first class you will be using::
    
    schema:Person a rdf:Class;
        rdfs:label "Person";
        rdfs:comment "A person (alive, dead, undead, or fictional).".
        
3. Tag the class with **kds:ControlledClass**. This tells the Framework that you will be using the class in the application::

    schema:Person a kds:ControlledClass .
   
4. Now tell specify how the class should be stored. Options are "object" or "blanknode". This tells the Framework whether to create a new URI or store it as the blanknode in the object position of a triple::

    schema:Person kds:storageType "object" .
    
5. Next determine if there is a **Primary Key** for the class. This tells the framework that when adding a new instance of the class to the database that the specified properties must be unique or the combination of properties must be unique::

    schema:Person kds:primaryKey schema:email.
    
.. note::

    Make the primary key a combination of properties like this::
    
        schema:Person kds:primaryKey [
            kds:keyCombo schema:givenName;
            kds:keyCombo schema:familyName
        ] .
    
6. Lastly we need to define the security rules for the class::

    schema:Person kds:classSecurity [
    		acl:agent kdr:Admin-SG;
    		acl:mode acl:Read, acl:Write
    ] ;
    
This means that anyone in the **kds:Admin-SG** has read and write privaledges to the class.

.. note::

    To add more permissions repeat the above information.
    
7. Putting it all together would look like this::

    schema:Person a rdf:Class;
        rdfs:label "Person";
        rdfs:comment "A person (alive, dead, undead, or fictional).";
        a kds:ControlledClass ;
        kds:storageType "object" ;
        kds:primaryKey schema:email;
        kds:classSecurity [
        		acl:agent kdr:Admin-SG;
        		acl:mode acl:Read, acl:Write
        ] ;
        kds:classSecurity [
        		acl:agent kdr:LoggedIn-SG;
        		acl:mode acl:Read
        ] .
        
Next define your rdf:Properties!


* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`