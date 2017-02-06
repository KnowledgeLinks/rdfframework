__author__ = "Mike Stabile, Jeremy Nelson"

from types import ModuleType

RDF_GLOBAL = None
FRAMEWORK_CONFIG = None

def fw_config(**kwargs):
    ''' function returns the application configuration information '''
    global FRAMEWORK_CONFIG
    try:
        FRAMEWORK_CONFIG
    except NameError:
        FRAMEWORK_CONFIG = None
    if FRAMEWORK_CONFIG is None:
        if  kwargs.get("config"):
            # if the config is in the form of Mudule convet to a dictionary
            if isinstance(kwargs['config'], ModuleType):
                kwargs['config'] = kwargs['config'].__dict__
            config = kwargs.get("config")
        else:
            try:
                config = current_app.config
            except:
                config = None
        if not config is None:
            FRAMEWORK_CONFIG = make_class(config)
        else:
            print("framework not initialized")
            return "framework not initialized"
    return FRAMEWORK_CONFIG

def get_framework(**kwargs):
    ''' sets an instance of the the framework as a global variable. This
        this method is then called to access that specific instance '''
    global RDF_GLOBAL
    root_file_path = kwargs.get('root_file_path')
    fw_config(config=kwargs.get("config"))
    _reset = kwargs.get("reset")
    server_check = kwargs.get("server_check", True)
    if _reset:
        try:
            from .framework import RdfFramework
        except ImportError:
            from rdfframework.framework import RdfFramework
        if root_file_path:
            RDF_GLOBAL = RdfFramework(root_file_path,
                                      reset=_reset,
                                      server_check=server_check)
        else:
            return "Root_File_path not set"
    try:
        RDF_GLOBAL
    except NameError:
        RDF_GLOBAL = None
    if RDF_GLOBAL is None:
        try:
            from .framework import RdfFramework
        except ImportError:
            from rdfframework.framework import Rdfframework
        if root_file_path:
            RDF_GLOBAL = RdfFramework(root_file_path,
                                      reset=_reset,
                                      server_check=server_check)
        else:
            RDF_GLOBAL = "root_file_path is not set"
    return RDF_GLOBAL

