RDF Properties in the Framework
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
        
3. Add a rdfs:domain tag for each class that uses the property::

    schema:email rdfs:domain schema:Person,
                             schema:Organization .
                       
.. note::

    The two **rdfs:domain** statements listed above state that the **schema:email** property will be used in both the **schema:Person** and **schema:Organization** rdf:Classes.
   
4. Next specify the **rdfs:range** for the property. Remember this tells the framework which type of value should be in the **object** position of a triple::

    schema:email rdfs:range xsd:string .
    
5. Now we need to specify more specific rules for the property. If we want to make it a required property for a **rdf:Class** we can add a **kds:requiredByDomain** tag. ::

    schema:email kds:requiredByDomain schema:Person .
    
.. note::

    Since we only added a **kds:requiredByDomain** tag for the **schema:Person** class, the **schema:Organization**, which also uses the property will not require the property. To make it a required property for the **schema:Organization** class as well add::
    
    schema:email kds:requiredByDomain schema:Organization. 
    
.. warning::

    If the property was specified as a **Primary Key** in the **rdf:Class** definition it is not necessary to make it a **required property** in the property definition. **Primary Keys** are required by definition. It will **NOT** cause a problem if a primary key is also specified as a required property.
    
6. Define any security rules for the property::

    schema:email kds:propertySecurity [
    		**kds:appliesTo schema:Person**
    		acl:agent kdr:Admin-SG;
    		acl:mode acl:Read
    ] ;

.. note::

    The **kds:appliesTo** tag specifies which rdf:Class to apply the security setting. In this case adding the above means that the schema:email property when used in the **schema:Person** class can only be seen by the kdr:Admin-SG. However, when it is used in the **schema:Organization** class no such rules apply.
    
7. The next major component is to tell the framework how to validate the property. This way we have consistancy when saving data::

    schema:email **kds:propertyValidation** [
      		a kdr:EmailValidator
      	] .

.. seealso::

    For a full listing of validators see the Validator section
    
8. Now state how the application should process the data for the property. There are wide variety of actions that can be performed::

    schema:email kds:propertyProcessing [
      kds:appliesTo schema:Person ;
      a kdr:EmailVerificationProcessor
    ] .           
    
.. note::

    We are appling an email verification action only to the schema:Person class. If we wanted to apply it to all rdf:Classes that use the property we would leave that line out.
    
.. seealso::

    The processor section lists all available processors and their specifications.
    
9. Lastly, we can define a default pattern for how the property will appear in forms::   

    schema:email kds:formDefault [
      		kds:formFieldName "emailaddr";
      		kds:formLabelName "Email Address";
      		kds:formFieldHelp "Enter a valid email address.";
      		kds:fieldType [
      			a	kdr:TextField
      		]
      	] .

.. note::

    These can be overridden in the actual form specification. Defining a default here allows for easy insertion of the property into many forms without having to specify the basics about the field each time.
    
.. seealso::

    For a detailed explanation and options see the Forms section
    
10. Putting it all together would look like this::    	

        schema:email a rdf:Property;	
          	rdfs:domain	schema:Person;	
          	rdfs:domain schema:Organization;
          	rdfs:range	xsd:string;	
          	rdfs:comment "email address.";
          	kds:requiredByDomain schema:Person;
          	kds:propertyProcessing [
          	  kds:appliesTo schema:Person;
          		a kdr:EmailVerificationProcessor
          	];                   
          	kds:propertyValidation [
          		a kdr:EmailValidator
          	];
          	kds:propertySecurity [
          	  kds:appliesTo schema:Person;
          		acl:agent kdr:Self-SG;
          		acl:mode acl:Read, acl:Write
          	] ;
          	kds:formDefault [
          		kds:formFieldName "emailaddr";
          		kds:formLabelName "Email Address";
          		kds:formFieldHelp "Enter a valid email address.";
          		kds:fieldType [
          			a	kdr:TextField
          		]
          	] .
        
Next define the application settings!


* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`