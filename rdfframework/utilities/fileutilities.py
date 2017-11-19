""" MODULE with file and directory utilities """
import os
import inspect
import logging

__author__ = "Mike Stabile, Jeremy Nelson"

MNAME = "%s.%s" % \
        (os.path.basename(os.path.split(inspect.stack()[0][1])[0]),
         os.path.basename(inspect.stack()[0][1]))
LOG_LEVEL = logging.DEBUG


def list_files(file_directory,
               file_extensions=None,
               include_subfolders=True,
               include_root=True,
               root_dir=None):
    '''Returns a list of files

    args:
        file_directory: a sting path to the file directory
        file_extensions: a list of file extensions to filter example
                ['xml', 'rdf']. If none include all files
        include_subfolders: as implied
        include_root: whether to include the root in the path
    '''

    log = logging.getLogger("%s" % (inspect.stack()[0][3]))
    log.setLevel(LOG_LEVEL)

    rtn_list = []
    if not root_dir:
        root_dir = file_directory
    dir_parts_len = len(root_dir.split("/"))
    level = 0
    for root, dirnames, filenames in os.walk(file_directory):
        root_str = root
        if level > 0 and not include_subfolders:
            break
        if not include_root:
            root_str = "/".join(root.split("/")[dir_parts_len:])
        if file_extensions:
            files = [(x,
                      os.path.join(root_str, x),
                      os.path.getmtime(os.path.join(root, x)))
                     for x in filenames \
                     if "." in x \
                     and x.split(".")[len(x.split("."))-1] in file_extensions]
        else:
            files = [(x,
                      os.path.join(root_str, x),
                      os.path.getmtime(os.path.join(root, x)))
                     for x in filenames]
        rtn_list += files
        level += 1
    rtn_list.sort(key=lambda tup: tup[0], reverse=True)
    return rtn_list


