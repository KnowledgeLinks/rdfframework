Application wide RDF specification
==================================
Now we will specify some specific rules and information pertaining application wide.
    
Steps
-----
1. Make up a URI for your application add **kds:Application** as the rdf:type and then add the basic information about the application::
    
    myns:My-Awsome-App a kds:Application;
        rdfs:label "My Awesome Application";
        rdfs:comment "An application that does everything.".
        
2. Next specify all the namespaces that are to be used in the application::

       myns:My-Awsome-App kds:appNameSpace [
        		kds:prefix "rdf";
        		kds:nameSpaceUri "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
        	];
        	kds:appNameSpace [
        		kds:prefix "acl";
        		kds:nameSpaceUri "http://www.w3.org/ns/auth/acl#"
        	]; 
        	kds:appNameSpace [
        		kds:prefix "xsd";
        		kds:nameSpaceUri "http://www.w3.org/2001/XMLSchema#"
        	]; 
        	kds:appNameSpace [
        		kds:prefix "schema";
        		kds:nameSpaceUri "https://schema.org/"
        	]; 
        	kds:appNameSpace [
        		kds:prefix "kds";
        		kds:nameSpaceUri "http://knowledgelinks.io/ns/data-structures/"
        	]; 
        	kds:appNameSpace [
        		kds:prefix "kdr";
        		kds:nameSpaceUri "http://knowledgelinks.io/ns/data-resources/"
        	] .
   
3. Specify the specific data formats. This is essential since python's date methods require specific formating parameters. This allows for consitancy when moving between javascript and python::

        myns:My-Awsome-App kds:dataFormats [
          		kds:pythonDateFormat "%m/%d/%Y";
          		kds:javascriptDateFormat "mm/dd/yyyy"
          	];
    
4. Now define where the app should save its data and how to generate new URIs::

        myns:My-Awsome-App kds:saveLocation "triplestore";
          	kds:subjectPattern "!--baseUrl,/,ns,/,!--classPrefix,/,!--className,/,!--uuid".
    
.. note::

    The **kds:saveLocation** states the authoriative datastore for the application. This can be overridden in the rdf:class definition by adding the a **kds:saveLocation** tag to that class. Options are **triplestore**, **repository**, and **elasticsearch**.
    
    The **kds:subjectPattern** specifies how new URIs should be formatted. It is a comma separated string. Items that start with **!--** are calculated. You can also specify specific properties as well by using **<<prop_uri>>**. For example if you wanted to generate a this pattern::
    
        <http://myappurl.com/organization/my-awesome-org>
        
    and where the class is **schema:Organization** and you have a property in the class **schema:alternativeName** the slugifies the name of the organization, the **kds:subjectPattern** would be::
    
        "!--baseUrl,/,!--className,/,<<schema:alternativeName>>"
    
5. Next we can define some default settings for our forms::

        myns:My-Awsome-App kds:formDefault [
        		kds:fieldCss "form-control";
        		kds:rowCss "appFormRowCss";
        		kds:formCss "appFormFormCss"
        	];

.. note::

    All of these can be added to or overridden in the form and then further added to or overridden in the field definitions.

6. Lastly, we define the security settings for the application::

        myns:My-Awsome-App kds:applicationSecurity [
          		acl:mode kds:SuperUser;
          		acl:agent kdr:SysAdmin-SG
          	];
          	kds:applicationSecurity [
          		acl:mode acl:Read, acl:Write, acl:Control;
          		acl:agent kdr:Admin-SG
          	];
          	kds:applicationSecurity [
          		acl:mode acl:Read, acl:Append;
          		acl:agent kdr:User-SG
          	];
      	
.. seealso::

    see the Security section for a complete understanding of the security architecture and implementation
     
7. Putting it all together would look like this::

        myns:My-Awsome-App a kds:Application;
          	kds:applicationSecurity [
          		acl:mode kds:SuperUser;
          		acl:agent kdr:SysAdmin-SG
          	];
          	kds:applicationSecurity [
          		acl:mode acl:Read, acl:Write, acl:Control;
          		acl:agent kdr:Admin-SG
          	];
          	kds:applicationSecurity [
          		acl:mode acl:Read, acl:Append;
          		acl:agent kdr:User-SG
          	];
          	kds:formDefault [
          		kds:fieldCss "form-control";
          		kds:rowCss "appFormRowCss";
          		kds:formCss "appFormFormCss"
          	];
          	kds:dataFormats [
          		kds:pythonDateFormat "%m/%d/%Y";
          		kds:javascriptDateFormat "mm/dd/yyyy"
          	];
          	kds:appNameSpace [
          		kds:prefix "rdf";
          		kds:nameSpaceUri "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
          	];
          	kds:appNameSpace [
          		kds:prefix "acl";
          		kds:nameSpaceUri "http://www.w3.org/ns/auth/acl#"
          	]; 
          	kds:appNameSpace [
          		kds:prefix "xsd";
          		kds:nameSpaceUri "http://www.w3.org/2001/XMLSchema#"
          	]; 
          	kds:appNameSpace [
          		kds:prefix "schema";
          		kds:nameSpaceUri "https://schema.org/"
          	]; 
          	kds:appNameSpace [
          		kds:prefix "kds";
          		kds:nameSpaceUri "http://knowledgelinks.io/ns/data-structures/"
          	]; 
          	kds:appNameSpace [
          		kds:prefix "kdr";
          		kds:nameSpaceUri "http://knowledgelinks.io/ns/data-resources/"
          	]; 
          	kds:appNameSpace [
          		kds:prefix "foaf";
          		kds:nameSpaceUri "http://xmlns.com/foaf/0.1/"
          	]; 
          	kds:appNameSpace [
          		kds:prefix "rdfs";
          		kds:nameSpaceUri "http://www.w3.org/2000/01/rdf-schema#"
          	]; 
          	kds:saveLocation "triplestore";
          	kds:subjectPattern "!--baseUrl,/,ns,/,!--classPrefix,/,!--className,/,!--uuid".

Next we will define our Forms!

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`