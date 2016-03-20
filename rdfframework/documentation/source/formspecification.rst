Form RDF Specification
======================
Now comes the fun part. Defining your forms!!! Once your forms definitions are built your application can start saving data.  
    
Steps
-----
1. Make up a URI for your form and add **kds:FormClass** as the rdf:type. Then add basic information::
    
      obi:BadgeForm a kds:FormClass;
        	rdfs:label "Badge form";
        	rdfs:comment "Use this form for generating a new Badge.". 
        
2. Next we need to specify the instructions for the form. This is all captured in one blanknode of the **kds:formIntructions** property::

      obi:BadgeForm kds:formInstructions [
            		kds:loginRequired true ;
            		kds:form_Method "POST";
            		kds:form_enctype "multipart/form-data";
            		kds:formTitle "Open Badge";
            		kds:formDescription "Badge infomation";
            		kds:lookupClassUri obi:BadgeClass;
            		kds:formUrl "badge";
            		kds:submitSuccessRedirect kdr:DisplayForm;
            		kds:submitFailRedirect "!--currentpage";
            		kds:formInstance [
            			kds:formInstanceType kdr:NewForm;
            			kds:formTitle "New Open Badge";
            			kds:formDescription "Create a new open badge"
            		];
            		kds:formInstance [
            			kds:formInstanceType kdr:EditForm;
            			kds:formDescription "Edit badge information."
            		];
            		kds:formInstance [
            			kds:formInstanceType kdr:DisplayForm;
            			kds:formDescription "Badge information."
            		]
            	].
            	
.. note::
    
    Lets analyse the above definition:
    
    - **kds:form_Method** - defines the allowed methods for the form POST, GET
    - **kds:form_enctype** - HTML form type
    - **kds:formTitle** - The name to be displayed in the tile position of the form
    - **kds:formDescription** - A description of the form that will be displayed in the form description section
    - **kds:formUrl** - the url to use for the form. **If this is omitted the namespace will be removed from the form URI and that will be the base path. i.e. **obi:BadgeForm** will become **BadgeForm** as the form path.
    - **kds:lookupClassUri** - the rdf:Class that a passed in **id** value will pertains to. For example: we pass in the url **?id=<http:../Person/1232>** and the id is of the rdf:Class **schema:Person** we would set **schema:Person** as the **kds:lookupClassUri**.
    - **kds:submitSuccessRedirect** and **kds:submitFailRedirect** - specify where the form should redirect to on success and fail submit attempts.
    - **kds:formInstance** - There are 3 main instances of any form: a **new**, **edit** and **display** instance. If you want your form to have all three instances they need to be explicitly stated as above. **Within each instance declaration any of the previous declarations can be overriden for that particular instance.** As seen above the form description is change in each instance of the form and the title is changed in the new form intance.
    
3. Now all we need to do is add the **fields/properties** to the form. This is done with the **kds:hasProperty** tag::

        obi:BadgeForm kds:hasProperty [
        		kds:propUri schema:description;
        		kds:classUri obi:BadgeClass;
        		kds:formFieldOrder 2;
        		kds:formLayoutRow 2;
        	];
        	
.. note::

    The above declaration is the simplest of declarations. Here are a few key points.
    
    - The **kds:propUri** specifies which rdf:Property we are using.
    - The **kds:classUri** tag has been added since the **schema:description** property is used in multiple **rdf:Classes**. *This can be omitted if the property is only used in one class.*
    - Lastly we specify the **field order** and **form row**. The value can be either an integer or float/decimal value.
    
.. warning::

    The first question you may be thinking is how do we know what the field type, name and any other attributes are!!! When we declared in the **kds:formDefault** specification when we declared the properties. See `RDF Properties in the Framework <./definingprops.html>`_
    
    If you want to override any of those specification re-add the tags here::
    
        obi:BadgeForm kds:hasProperty [
            kds:propUri schema:description;
        		kds:classUri obi:BadgeClass;
        		kds:formFieldOrder 2;
        		kds:formLayoutRow 2;
        		kds:formLabelName "Describe your Badge in detail";
        		kds:formDescription "In this field you must provide a detailed explanation of the Badge."
        	];
        	
    If you want to change the details for specific instances of the form you can do that as well::
    
         obi:BadgeForm kds:hasProperty [
            kds:propUri schema:description;
        		kds:classUri obi:BadgeClass;
        		kds:formFieldOrder 2;
        		kds:formLayoutRow 2;
        		kds:formLabelName "Describe your Badge in detail";
        		kds:formDescription "In this field you must provide a detailed explanation of the Badge.";
        		kds:formInstance [
        			kds:formInstanceType kdr:NewForm;
        			kds:formLabelName "Label in New Form"; 
        		];
        		kds:formInstance [
        			kds:formInstanceType kdr:EditForm;
        			kds:formLabelName "Label in Edit Form"; 
        		];
        		kds:formInstance [
        			kds:formInstanceType kdr:DisplayForm;
        			kds:formLabelName "Label in Display Form"; 
        		]
        	]; 
      
.. seealso::

    For a full listing of field specifications see the `Form field specification <./formfieldspecs.html>`_ section.
        
.. warning::

    **One more key point!** All the security and required property parameters are inhertied from the **rdf:Class** and **rdf:Property** declarations. Required properties do not need to be in the **Form** if they are calculated or have a default value. **The form will not validate and save if you are missing a required property and it can not calculate a value for it missing property!**
            
4. Below is a complete form definition::

        obi:BadgeForm a kds:FormClass;
          	rdfs:label "Badge form";
          	rdfs:comment "Use this form for generating a new Badge.";
          	kds:formInstructions [
          		kds:form_Method "POST";
          		kds:form_enctype "multipart/form-data";
          		kds:formTitle "Open Badge";
          		kds:loginRequired true ;
          		kds:formDescription "Badge infomation";
          		kds:lookupClassUri obi:BadgeClass;
          		kds:formUrl "badge";
          		kds:submitSuccessRedirect kdr:DisplayForm;
          		kds:submitFailRedirect "!--currentpage";
          		kds:formInstance [
          			kds:formInstanceType kdr:NewForm;
          			kds:formTitle "New Open Badge";
          			kds:formDescription "Create a new open badge"
          		];
          		kds:formInstance [
          			kds:formInstanceType kdr:EditForm;
          			kds:formDescription "Edit badge information."
          		];
          		kds:formInstance [
          			kds:formInstanceType kdr:DisplayForm;
          			kds:formDescription "Badge information."
          		]
          	];
          	kds:hasProperty [
          		kds:propUri obi:issuer;
          		kds:formFieldOrder 0.5;
          		kds:formLayoutRow 1;
          		kds:formInstance [
          			kds:formInstanceType kdr:NewForm;
          			kds:applicationAction kdr:LookupAddNewWorkFlow; 
          		];
          		kds:formInstance [
          			kds:formInstanceType kdr:EditForm;
          			kds:applicationAction kdr:NotEditable 
          		];
          		kds:formInstance [
          			kds:formInstanceType kdr:DisplayForm
          		]
          	];
          	kds:hasProperty [
          		kds:propUri schema:name;
          		kds:classUri obi:BadgeClass;
          		kds:formFieldOrder 1;
          		kds:formLayoutRow 1;
          		kds:formInstance [
          			kds:formInstanceType kdr:NewForm;
          			kds:applicationAction kdr:LookupAddNewWorkFlow; 
          		];
          		kds:formInstance [
          			kds:formInstanceType kdr:EditForm;
          			#kds:applicationAction kdr:NotEditable 
          		]
          	];
          	kds:hasProperty [
          		kds:propUri schema:description;
          		kds:classUri obi:BadgeClass;
          		kds:formFieldOrder 2;
          		kds:formLayoutRow 2;
          	];
          	kds:hasProperty [
          		kds:propUri obi:startDate;
          		kds:formFieldOrder 3;
          		kds:formLayoutRow 3;
          		kds:addOnCss "dp";
          	];
          	kds:hasProperty [
          		kds:propUri obi:endDate;
          		kds:formFieldOrder 4;
          		kds:formLayoutRow 3;
          	];
          	kds:hasProperty [
          		kds:propUri schema:image;
          		kds:classUri obi:BadgeClass;
          		kds:formFieldOrder 5;
          		kds:formLayoutRow 4;
          	];
          	kds:hasProperty [
          		kds:propUri obi:tags;
          		kds:formFieldOrder 6;
          		kds:formLayoutRow 5;
          	];
          	kds:hasProperty [
          		kds:propUri obi:criteria;
  		kds:formFieldOrder 7;
  		kds:formLayoutRow 6;
  	].

Next we will define our APIs!

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`