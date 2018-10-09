""" MODULE with file and directory utilities """
import os
import inspect
import logging
import tempfile
import errno

__author__ = "Mike Stabile, Jeremy Nelson"

__MNAME__ = "%s.%s" % \
        (os.path.basename(os.path.split(inspect.stack()[0][1])[0]),
         os.path.basename(inspect.stack()[0][1]))
__LOG_LEVEL__ = logging.DEBUG

def is_writable_dir(directory, **kwargs):
    """ tests to see if the directory is writable. If the directory does
        it can attempt to create it. If unable returns False

    args:
        directory: filepath to the directory

    kwargs:
        mkdir[bool]: create the directory if it does not exist

    returns
    """
    try:
        testfile = tempfile.TemporaryFile(dir = directory)
        testfile.close()
    except OSError as e:
        if e.errno == errno.EACCES:  # 13
            return False
        elif e.errno == errno.ENOENT: # 2
            if kwargs.get('mkdir') == True:
                try:
                    os.makedirs(directory)
                except OSError as e2:
                    if e2.errno == errno.EACCES: # 13
                        return False
            else:
                return False
        e.filename = directory
    return True

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
        root_dir: the root directory to remove if include_root is False

    returns:
        (tuple) (file_name, file_path_with_root_mod, modified_time, full_path)
    '''

    log = logging.getLogger("%s" % (inspect.stack()[0][3]))
    log.setLevel(__LOG_LEVEL__)

    rtn_list = []
    if not root_dir:
        root_dir = file_directory
    root_dir = root_dir.strip()
    if root_dir.endswith(os.path.sep):
        root_dir = root_dir.strip()[:-1]
    dir_parts_len = len(root_dir.split(os.path.sep))
    level = 0
    for root, dirnames, filenames in os.walk(file_directory):
        root_str = root
        if level > 0 and not include_subfolders:
            break
        if not include_root:
            root_str = os.path.sep.join(root.split(os.path.sep)[dir_parts_len:])
        if file_extensions:
            files = [(x,
                      os.path.join(root_str, x),
                      os.path.getmtime(os.path.join(root, x)),
                      os.path.join(root, x))
                     for x in filenames \
                     if "." in x \
                     and x.split(".")[len(x.split("."))-1] in file_extensions]
        else:
            files = [(x,
                      os.path.join(root_str, x),
                      os.path.getmtime(os.path.join(root, x)),
                      os.path.join(root, x))
                     for x in filenames]
        rtn_list += files
        level += 1
    rtn_list.sort(key=lambda tup: tup[0], reverse=True)
    return rtn_list


