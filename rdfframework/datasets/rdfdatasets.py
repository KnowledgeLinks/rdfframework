"""    This module is used for setting an intial test configs and values for
the rdfframework """

import re
import json
import copy
import types
import datetime
import functools
import pprint, pdb
import logging
import multiprocessing as mp

# from rdfframework import rdfclass
from rdfframework.utilities import DictClass, make_list, SimpleMapReduce
from rdfframework.configuration import RdfConfigManager
from rdfframework.datatypes import pyrdf, BaseRdfDataType, Uri
from rdfframework.rdfclass import RdfClassBase, remove_parents, list_hierarchy
from .jsonquery import json_qry

MODULE = __import__(__name__)
# import rdfframework.rdfclass as rdfclass
CFG = RdfConfigManager()
pool_size = mp.cpu_count() - 1 or 1
__a__ = Uri("rdf:type")

def convert_row_main(val, i, key, output):
    # rtn_obj = {}
    # rtn_tup = (pyrdf(row['s']), pyrdf(row['p']), pyrdf(row['o']))
    # return pyrdf(row['s']) #rtn_tup
    # for key, value in row.items():
    #     # try:
    #     # print("convert_row_main: ", value)
    #     # if value.get("datatype") == 'http://www.w3.org/2001/XMLSchema#dateTime':
    #     #     pdb.set_trace()
    #     rtn_obj[key] = pyrdf(value)
    #     # print(rtn_obj)
    #     # except:
    #     #     pdb.set_trace()
    # return rtn_obj
    output.put((i, key, pyrdf(val),))
    # output.put({key:pyrdf(value) for key, value in row.items()})

class RdfDataset(dict):
    """ A container for holding rdf data """
    log_level = logging.INFO
    _reserved = ['add_triple',
                  '_format',
                  '_reserved',
                  '_link_objects',
                  'load_data',
                  'class_types',
                  'subj_list',
                  'non_defined',
                  '',
                  ]

    __slots__ = ['classes',
                 'subj_list',
                 'non_defined',
                 'base_uri',
                 'base_class',
                 'relate_obj_types',
                 'smap',
                 'pmap',
                 'omap',
                 'rmap']

    def __init__(self, data=None, base_uri=None, **kwargs):
        start = datetime.datetime.now()
        self.smap = 's'
        self.pmap = 'p'
        self.omap = 'o'
        self.rmap = {}
        if base_uri:
            base_uri = Uri(base_uri)
        self.base_uri = base_uri
        if kwargs.get("debug"):
            log.setLevel(logging.DEBUG)
        # realate_bnode_obj_types sets whether to relate the object of a class
        # back to itself
        self.relate_obj_types = ['bnode','uri']
        if kwargs.get("bnode_only"):
            self.relate_obj_types = ['bnode']

        if data:
            self.load_data(data, **kwargs)
            log.debug("loaded %s triples in %s" % (len(data),
                                               (datetime.datetime.now()-start)))

    def __repr__(self):
        return "<Dataset([{'base_uri': '%s',\n'keys': '%s'}])>" % \
               (self.base_uri,
                [key.sparql for key in self if key.type != 'bnode'])

    def __set_map__(self, **kwargs):
        """ sets the subject predicat object json mapping

        kwargs:
            map: dictionary mapping 's', 'p', 'o' keys
        """
        if kwargs.get('map'):
            map = kwargs.pop('map',{})
            self.smap = map.get('s','s')
            self.pmap = map.get('p','p')
            self.omap = map.get('o','o')

    def add_triple(self, sub, pred=None,  obj=None, **kwargs):
        """ Adds a triple to the dataset

            args:
                sub: The subject of the triple or dictionary contaning a
                     triple
                pred: Optional if supplied in sub, predicate of the triple
                obj:  Optional if supplied in sub, object of the triple

            kwargs:
                map: Optional, a ditionary mapping for a supplied dictionary
                strip_orphans: Optional, remove triples that have an orphan
                               blanknode as the object
                obj_method: if "list" than the object will be returned in the
                            form of a list
        """
        self.__set_map__(**kwargs)
        strip_orphans = kwargs.get("strip_orphans", False)
        obj_method = kwargs.get("obj_method")
        if isinstance(sub, DictClass) or isinstance(sub, dict):
            pred = sub[self.pmap]
            obj = sub[self.omap]
            sub = sub[self.smap]

        pred = pyrdf(pred)
        obj = pyrdf(obj)
        sub = pyrdf(sub)
        # reference existing attr for bnodes and uris
        if obj.type in self.relate_obj_types :
            if strip_orphans and not self.get(obj):
                return
            obj = self.get(obj,obj)
        try:
            self[sub].add_property(pred, obj)
        except KeyError:
            self[sub] = RdfClassBase(sub, self, **kwargs)
            self[sub].add_property(pred, obj)

    def format(self, **kwargs):

        uri_format = kwargs.get('uri_format', "pyuri")
        output = kwargs.get('output', "dict")
        pretty = kwargs.get('pretty', False)
        remove = make_list(kwargs.get('remove', None))
        compress = kwargs.get('compress', False)
        sort = kwargs.get('sort', False)
        base_uri = kwargs.get("base_uri",None)
        add_ids = kwargs.get("add_ids", False)
        base_only = kwargs.get("base_only", False)

        if compress:
            new_obj = copy.copy(self)
            for key, value in self.items():
                for skey, svalue in value.items():
                    if isinstance(svalue, list) and len(svalue) == 1:
                        try:
                            new_obj[key][skey] = svalue[0]
                        except KeyError:
                            new_obj[key] = {skey: svalue[0]}
            format_obj = new_obj
        else:
            format_obj = self
        if remove:
            remove = make_list(remove)

        conv_data = {key: value.conv_json(uri_format, add_ids)
                     for key, value in format_obj.items()
                     if value.subject.type not in remove}
        if base_only:
            try:
                conv_data = conv_data[self.base_uri]
            except KeyError:
                return "Base_uri undefined or not in dataset"

        if output.lower() == 'json':
            indent = None
            if pretty:
                indent = 4
            return json.dumps(conv_data, indent=indent, sort_keys=sort)
        elif output.lower() == 'dict':
            return conv_data

    @property
    def view(self):
        """ prints the dataset in an easy to read format """
        print(self.format(remove='bnode',
                          sort=True,
                          pretty=True,
                          compress=True,
                          output='json',
                          add_ids=True))

    @property
    def view_main(self):
        """ prints the dataset in an easy to read format """
        print(self.format(remove='bnode',
                          sort=True,
                          pretty=True,
                          compress=True,
                          output='json',
                          base_only = True,
                          add_ids=True))

    def load_data(self, data, **kwargs):
        """
        Bulk adds rdf data to the class

        args:
            data: the data to be loaded

        kwargs:
            strip_orphans: True or False - remove triples that have an
                           orphan blanknode as the object
            obj_method: "list", or None: if "list" the object of a method
                         will be in the form of a list.
        """
        self.__set_map__(**kwargs)
        start = datetime.datetime.now()
        log.debug("Dataload stated")
        if isinstance(data, list):
            data = self._convert_results(data, **kwargs)
        class_types = self.__group_data__(data, **kwargs)

        # generate classes and add attributes to the data
        self._generate_classes(class_types, self.non_defined, **kwargs)
        # add triples to the dataset
        for triple in data:
            self.add_triple(sub=triple, **kwargs)
        log.debug("Dataload completed in '%s'",
                  (datetime.datetime.now() - start))

    def __group_data__(self, data, **kwargs):
        """ processes the data in to groups prior to loading into the
            dataset

            args:
                data: a list of triples
        """
        # strip all of the rdf_type triples and merge

        class_types = self._merge_classtypes(self.__get_classtypes__(data))
        self.subj_list = list([item[self.smap] for item in class_types])
        # get non defined classes
        self.non_defined = self._get_non_defined(data, class_types)
        return class_types

    def triples(self, output=None):
        rtn_list = []
        for sub, props in self.items():
            for pred, obj in props.items():
                # if not isinstance(pred, Uri):
                #     pred = Uri(pred)
                if isinstance(obj, list):
                    for oo in obj:
                        if isinstance(oo, RdfClassBase):
                            oo = oo.subject
                        rtn_list.append((sub, pred, oo))
                else:
                    if isinstance(obj, RdfClassBase):
                        obj = obj.subject
                    rtn_list.append((sub, pred, obj))
        # rtn_list.sort(key=lambda tup: tup[0]+tup[1]+tup[2])
        if output:
            def size(value):
                if len(value) > 42:
                    value = "... %s" % value[-39:]
                spaces = 45 - len(value)
                return "%s%s" %(value," " * spaces)
            if output == "view":
                print("\n".join(
                        ["%s  %s%s%s" %
                         (i,
                          size(trip[0].sparql),
                          size(trip[1].sparql),
                          size(trip[2].sparql))
                         for i, trip in enumerate(rtn_list)]))
        else:
            return rtn_list

    @property
    def __set_classes__(self):
        def add_class(key, value):
            nonlocal rtn_obj
            try:
                rtn_obj[value].append(key)
            except AttributeError:
                rtn_obj[value] = [rtn_obj[value['rdf_type']]]
                rtn_obj[value].append(key)
            except KeyError:
                rtn_obj[value] = [key]
            except TypeError:
                for item in value:
                    add_class(key, item)
        rtn_obj = {}
        for key, value in self.items():
            try:
                add_class(key, value['rdf_type'])
            except KeyError:
                pass
        self.classes = rtn_obj
        #return rtn_obj

    def __get_classtypes__(self, data):
        """ returns all of the triples where rdf:type is the predicate and
            removes them from the data list

            agrs:
                data: a list of triples
        """
        rtn_list = []
        remove_index = []
        for i, triple in enumerate(data):
            if triple[self.pmap] == __a__:
                remove_index.append(i)
                rtn_list.append(triple)
        for i in reversed(remove_index):
            data.pop(i)
        return rtn_list

    def add_rmap_item(self, subj, pred, obj):
        """
        adds a triple to the inverted  dataset index
        """
        def add_item(self, subj, pred, obj):
            try:
                self.rmap[obj][pred].append(subj)
            except KeyError:
                try:
                    self.rmap[obj][pred] = [subj]
                except KeyError:
                    self.rmap[obj] = {pred: [subj]}

        if isinstance(obj, list):
            for item in obj:
                add_item(self, subj, pred, item)
        else:
            add_item(self, subj, pred, obj)

    def _generate_classes(self, class_types, non_defined, **kwargs):
        """ creates the class for each class in the data set

            args:
                class_types: list of class_types in the dataset
                non_defined: list of subjects that have no defined class
        """
        # kwargs['dataset'] = self
        for class_type in class_types:
            self[class_type[self.smap]] = self._get_rdfclass(class_type,
                                                             **kwargs)\
                                                            (class_type,
                                                             self,
                                                             **kwargs)

            self.add_rmap_item(self[class_type[self.smap]],
                               class_type[self.pmap],
                               class_type[self.omap])

        for class_type in non_defined:
            self[class_type] = RdfClassBase(class_type, self, **kwargs)
            self.add_rmap_item(self[class_type], __a__, None)
        self.__set_classes__
        try:
            self.base_class = self[self.base_uri]
        except KeyError:
            self.base_class = None

    def _get_rdfclass(self, class_type, **kwargs):
        """ returns the instanticated class from the class list

            args:
                class_type: dictionary with rdf_types
        """
        def select_class(class_name):
            """ finds the class in the rdfclass Module"""
            try:
                return getattr(MODULE.rdfclass, class_name.pyuri)
            except AttributeError:
                return RdfClassBase

        if kwargs.get("def_load"):
            return RdfClassBase

        if isinstance(class_type[self.omap], list):
            bases = [select_class(class_name)
                     for class_name in class_type[self.omap]]
            bases = [base for base in bases if base != RdfClassBase]
            if len(bases) == 0:
                return RdfClassBase
            elif len(bases) == 1:
                return bases[0]
            else:
                bases = remove_parents(bases)
                if len(bases) == 1:
                    return bases[0]
                else:
                    name = "_".join(sorted(class_type[self.omap]))
                    # if the the class has already been created return it
                    if hasattr(MODULE.rdfclass, name):
                        return getattr(MODULE.rdfclass, name)
                    new_class = type(name,
                                     tuple(bases),
                                     {})
                    new_class.hierarchy = list_hierarchy(class_type[self.omap][0],
                                                         bases)
                    new_class.class_names = sorted([base.__name__ \
                            for base in bases \
                            if base not in [RdfClassBase, dict]])
                    setattr(MODULE.rdfclass, name, new_class)
                    return new_class
        else:
            return select_class(class_type[self.omap])

    def _merge_classtypes(self, data):
        obj = {}
        for triple in data:
            try:
                obj[triple[self.smap]][self.omap].append(triple[self.omap])
            except AttributeError:
                obj[triple[self.smap]][self.omap] = [obj[triple[self.smap]][self.omap]]
                obj[triple[self.smap]][self.omap].append(triple[self.omap])
            except KeyError:
                obj[triple[self.smap]] = triple
        return list(obj.values())

    def _get_non_defined(self, data, class_types):
        """
        returns a list of URIs and blanknodes that are not defined within
        the dataset. For example: schema:Person has an associated rdf:type
        then it is considered defined.

        args:
            data: a list of triples
            class_types: list of subjects that are defined in the dataset
        """
        subj_set = set([item[self.smap] for item in class_types])
        non_def_set = set([item[self.smap] for item in data])
        return list(non_def_set - subj_set)

    def _convert_results(self, data, **kwargs):
        """ converts the results of a query to RdfDatatype instances

            args:
                data: a list of triples
        """

        if kwargs.get("multiprocessing", False):
            m = mp.Manager()
            output = m.Queue()
            pdb.set_trace()
            # processes = [mp.Process(target=convert_row_main,
            #                         args=(row, output,))
            #              for row in data]
            # # Run processes
            # for p in processes:
            #     p.start()

            # # Exit the completed processes
            # for p in processes:
            #     p.join()
            # # Get process results from the output queue
            # return [output.get() for p in processes]

            pool = mp.Pool(processes=pool_size)
            for i, row in enumerate(data):
                for key, val in row.items():
                    try:
                        pool.apply(convert_row_main, args=(val, i, key, output,))
                    except:
                        pass #
            # run = [pool.apply(convert_row_main, args=(row, i, output))
            #        for i, row in enumerate(data)]
            for item in output:
                pdb.set_trace()
            return output
            # with multiprocessing.Pool(processes=pool_size) as pool:
            #     results = [convert_row_main, (row,))
            #                for row in data]
            #     converted = [r.get() for r in results]
            # return converted #pool_outputs
        else:
            return [{key:pyrdf(value) for key, value in row.items()}
                    for row in data]

    # def json_qry(self, qry_str, params):
    def json_qry(*args):
        """ Takes a json query string and returns the results

        args:
            qry_str: query string
        """
        return json_qry(*args)

