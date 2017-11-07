"""Security related functions"""
from rdfframework.utilities import make_list

DEBUG = True

def get_app_security(rdfw, user_groups):
    ''' Compares the user_groups against app wide security levels and 
        returns a list of app permissions 
        
        Args:
            rdfw = the current instance of the RdfFramework Class
            user_groups - a list of user groups the user belongs to
            
    '''
    
    if not DEBUG:
        debug = False
    else:
        debug = True
        
    if debug: print("START get_app_security securityfunctions.py ---------\n")
    app_rights = set()
    app_sec = rdfw.app.get('kds_applicationSecurity',[])
    for setting in app_sec:
        if setting.get("acl_agent") in user_groups:
            for right in make_list(setting.get("acl_mode")):
                if right not in [None, "None"]:
                    app_rights.add(right)  
    if debug: print("app_rights: ", list(app_rights))     
    if debug: print("END get_app_security securityfunctions.py -----------\n")
    return list(app_rights)