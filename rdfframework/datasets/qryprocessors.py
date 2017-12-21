import re
from rdfframework.utilities import UniqueList, cbool, KeyRegistryMeta
from rdfframework.datatypes import XsdString
import pdb

class QryProcessor(metaclass=KeyRegistryMeta):
    """ Base class for json query processors.  Provides a 'key' registry
    for all inherited classes.

    To make a new processor create an inherited class with the following
    attributes/methods at the class level

    Example:

    class NewProcessor(QryProcessor):
        key = "testkey" #this the string the json_qry will use

        def __init__(self, query_str_arg):
            # intialize base on query_str_arg

        def __call__(self, action_list):
            # do something to item in the action list
    """
    pass

class ListLimiter(QryProcessor):
    """ takes a list and a length limit and returns the list of appropriate
        length
    """
    key = "limit"

    def __init__(self, length):
        self.length = int(length)

    def __call__(self, action_list):
        if self.length >= 0:
            return action_list[:self.length]
        return action_list[self.length:]

class StripEnd(QryProcessor):
    """ strips off the provided characters from the end of strings
    """
    key = "stripend"

    def __init__(self, characters):
        self.regex = "[%s]+$" % characters

    def __call__(self, action_list):
        return [XsdString(re.sub(self.regex, '', str(action)))\
                for action in action_list]

class MakeDistinct(QryProcessor):
    """ Takes a list when called and removes dulplicates """
    key = "distinct"

    def __init__(self, active=True):
        self.active = cbool(active)

    def __call__(self, action_list):
        if not self.active:
            return action_list
        rtn_list = UniqueList()
        for action in action_list:
            rtn_list.append(action)
        return rtn_list
