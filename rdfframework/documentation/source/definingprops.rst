Defining RDF Properties in the Framework
****************************************
Now we will define the properties to be used in the application and which classes that use them. 

.. warning::

    Unlike a SQL field definition a property can be used in many rdf:Classes 
    
Steps
-----
1. Next add the basic information about a property you will be using::
    
    schema:email a rdf:Property;
        rdfs:label "Person";
        rdfs:comment "A person (alive, dead, undead, or fictional).".
        
3. Tag the class with **kds:ControlledClass**. This tells the Framework that you will be using the class in the application::

    schema:Person a kds:ControlledClass .
   
4. Now tell specify how the class should be stored. Options are "object" or "blanknode". This tells the Framework whether to create a new URI or store it as the blanknode in the object position of a triple::

    schema:Person kds:storageType "object" .
    
5. Next determine if there is a **Primary Key** for the class. This tells the framework that when adding a new instance of the class to the database that the specified properties must be unique or the combination of properties must be unique::

    schema:Person kds:primaryKey schema:email.
    
.. note::

    To make the primary key a combination of properties like this::
    
    schema:Peson kds:primaryKey [
        kds:keyCombo schema:givenName;
        kds:keyCombo schema:familyName
    ] .
    
6. Lastly we need to define the security rules for the class::

    schema:Person kds:classSecurity [
    		acl:agent kdr:Admin-SG;
    		acl:mode acl:Read, acl:Write
    ] ;
    
This means that anyone in the **kds:Admin-SG** has read and write prevledges to the class.

.. note::

    To add more permission repeat the above information.
    
7. Putting it all together would look like this::

    schema:email a rdf:Property;	
      	rdfs:domain	schema:Person;	
      	rdfs:domain schema:Organization;
      	rdfs:range	xsd:string;	
      	rdfs:comment "email address.";
      	kds:requiredByDomain schema:Person;
      	kds:propertyProcessing [
      		a kdr:EmailVerificationProcessor
      	];                   
      	kds:propertyValidation [
      		a kdr:EmailValidator
      	];
      	kds:propertySecurity [
      		acl:agent kdr:Self-SG;
      		acl:mode acl:Read, acl:Write
      	] ;
      	kds:jsonDefault [
      		kds:jsonObjName "email";
      		kds:jsonValFormat "objectValue"
      	] ;
      	kds:formDefault [
      		kds:formFieldName "emailaddr";
      		kds:formLabelName "Email Address";
      		kds:formFieldHelp "Enter a valid email address.";
      		kds:fieldType [
      			a	kdr:TextField
      		]
      	] .
        
Next define your rdf:Properties!


* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`