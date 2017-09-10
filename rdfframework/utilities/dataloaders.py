""" Class for getting data mappings"""
    
__author__="Mike Stabile, Jeremy Nelson"
import os
import datetime
import inspect
import logging
import json
import requests
import pdb
import elasticsearch.exceptions as es_except

from rdfframework.utilities import pp, RdfConfigManager, DictClass


MNAME = "%s.%s" % \
        (os.path.basename(os.path.split(inspect.stack()[0][1])[0]),
         os.path.basename(inspect.stack()[0][1]))
LOG_LEVEL = logging.DEBUG

CFG = RdfConfigManager()

def list_files(file_directory,
               file_extensions=None,
               include_subfolders=True,
               include_root=True):
    '''Returns a list of files

        args:
            file_directory: a sting path to the file directory
            file_extensions: a list of file extensions to filter
                    example ['xml', 'rdf']. If none include all files
            include_subfolders: as implied
            include_root: whether to include the root in the path
    '''
    
    lg = logging.getLogger("%s" % (inspect.stack()[0][3]))
    lg.setLevel(LOG_LEVEL)
    
    rtn_list = []
    dir_parts_len = len(file_directory.split("/"))
    for root, dirnames, filenames in os.walk(file_directory):
        root_str = root
        if not include_root:
            root_str = "/".join(root.split("/")[dir_parts_len:])
        files = [(x,
                  os.path.join(root_str,x),
                  os.path.getmtime(os.path.join(root,x)))
                 for x in filenames \
                 if "." in x \
                 and x.split(".")[len(x.split("."))-1] in file_extensions]
        rtn_list += files
    rtn_list.sort(key=lambda tup: tup[2], reverse=True)
    return rtn_list
        
    
class Blazegraph(object):

    ln = "%s-Blazegraph" % MNAME
    log_level = logging.DEBUG

    def __init__(self, 
                 local_directory=None,
                 url=None,
                 ns_url=None,
                 default_ns=None):
        
        args = DictClass(locals())
        self.local_directory = args.get('local_directory', 
                                        CFG.LOCAL_DATA_PATH,
                                        True)
        self.url = args.get('url', CFG.TRIPLESTORE.url, True)
        self.ns_url = args.get('ns_url', CFG.TRIPLESTORE.ns_url, True)
        self.default_ns = args.get('default_ns', 
                                   CFG.TRIPLESTORE.default_ns,
                                   True)
        self.container_dir = args.get('container_dir',
                                      CFG.TRIPLESTORE.container_dir,
                                      True)


    def load_local_files(self,
                         file_directory=None,
                         file_extensions=None,
                         include_subfolders=True,
                         include_root=False,
                         namespace=None,
                         graph=None):
        """ Uploads data to the Blazegraph Triplestore that is stored in files
            in  a local directory

            args:
                file_directory: a sting path to the file directory
                file_extensions: a list of file extensions to filter
                        example ['xml', 'rdf']. If none include all files
                include_subfolders: as implied
                namespace: the Blazegraph namespace to load the data
                graph: uri of the graph to load the data. Default is None
        """
        lg = logging.getLogger("%s.%s" % (self.ln, inspect.stack()[0][3]))
        lg.setLevel(self.log_level)
        time_start = datetime.datetime.now()
        args = DictClass(locals())
        file_directory = args.get('file_directory', self.local_directory, True)
        file_extensions = args.get('file_directory',
                                   ['xml', 'rdf', 'ttl'],
                                   True)
        file_list = list_files(file_directory,
                               file_extensions,
                               include_subfolders,
                               include_root=False)
        url = self.make_url(namespace)
        params = {}
        if graph:
            params['context-uri'] = graph   
        path_parts = []
        if self.container_dir:
            path_parts.append(self.container_dir)

        for file in file_list:
            new_path = path_parts.copy()
            new_path.append(file[1])
            params['uri'] = "file:///%s" % os.path.join(*new_path)
            lg.info("loading %s into blazegraph" % file[0])
            result = requests.post(url=url, params=params)
        lg.info("%s file(s) loaded in: %s" % (len(file_list),
                datetime.datetime.now() - time_start))

    def make_url(self, namespace=None, url=None):
        args = DictClass(locals())
        namespace = args.get("namespace", self.default_ns, True)
        url = args.get("url", self.url, True)
        if namespace:
            return os.path.join(url.replace("sparql",""),
                                       "namespace",
                                        namespace,
                                       "sparql").replace("\\","/")
        else:
            return url
                
        