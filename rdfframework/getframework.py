__author__ = "Mike Stabile, Jeremy Nelson"

from rdfframework.utilities import fw_config


def get_framework(**kwargs):
    ''' sets an instance of the the framework as a global variable. This
        this method is then called to access that specific instance '''
    global RDF_GLOBAL
    root_file_path = kwargs.get('root_file_path')
    fw_config(config=kwargs.get("config"))
    _reset = kwargs.get("reset")
    server_check = kwargs.get("server_check", True)
    if _reset:
        from .framework import RdfFramework
        RDF_GLOBAL = RdfFramework(root_file_path,
                                  reset=_reset,
                                  server_check=server_check)
    try:
        RDF_GLOBAL
    except NameError:
        RDF_GLOBAL = None
    if RDF_GLOBAL is None:
        from .framework import RdfFramework
        RDF_GLOBAL = RdfFramework(root_file_path,
                                  reset=_reset,
                                  server_check=server_check)
    return RDF_GLOBAL