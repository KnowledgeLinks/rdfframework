"""	This module is used for setting an intial test configs and values for 
the rdfframework """

import sys
import os
import pdb
import pprint
PACKAGE_BASE = os.path.abspath(
    os.path.split(
        os.path.dirname(__file__))[0])
print("PACKAGE_BASE: ", PACKAGE_BASE)
sys.path.append(PACKAGE_BASE)

from testconfig import config

from rdfframework.getframework import fw_config as fwc, get_framework as fw
from rdfframework.utilities import DictClass, pp, RdfNsManager, pp, \
								   render_without_request, RdfConfigManager, \
								   make_list
from rdfframework.rdfdatatypes import rdfdatatypes as rdt
from rdfframework.sparql import run_sparql_query
print("CONFIG ---------------------------------------------------------------")
#config = DictClass(config)
pp.pprint(config)
print("----------------------------------------------------------------------")
#fw(config=config, root_file_path=PACKAGE_BASE)
#NSM = get_ns_obj(config=DictClass(config))
config2 = RdfConfigManager(config=config)
NSM = RdfNsManager(config=config2)
rdf_defs = config2.RDF_DEFINITIONS

sparql = render_without_request("sparqlClassDefinitionList.rq",
                                             graph=rdf_defs.graph,
                                             prefix=NSM.prefix())
print(sparql)
x = run_sparql_query(sparql, namespace=config2.RDF_DEFINITIONS.namespace)
y = [rdt.pyrdf(i['kdsClass']) for i in x]

_sparql = render_without_request("sparqlClassDefinitionDataTemplate.rq",
                                 prefix=NSM.prefix(),
                                 item_uri="schema:Person",
                                 graph=rdf_defs.graph)
z = run_sparql_query(_sparql, namespace=rdf_defs.namespace)

def convert_query_row(row):
	""" Takes a JSON row and converts it to class """
	new_dict = {}
	for key, value in row.items():
		new_dict[key] = rdt.pyrdf(value)
	return DictClass(new_dict)

def convert_query_results(results):
	""" Takes a query result and converts it to a class """
	return [convert_query_row(row) for row in results]

v = convert_query_results(z)

def convert_to_class(con_results):
	new_dict = {}
	for row in con_results:
		#pdb.set_trace()

		if not new_dict.get(row.s):
			new_dict[row.s] = {}
		if not new_dict[row.s].get(row.p):
			new_dict[row.s][row.p] = row.o
		else:
			if not isinstance(new_dict[row.s][row.p], list):
				new_dict[row.s][row.p] = [new_dict[row.s][row.p]]
			new_dict[row.s][row.p].append(row.o)
	return DictClass(obj=new_dict, debug=False)

n = convert_to_class(v)
pyrdf = rdt.pyrdf
p1 = pprint.PrettyPrinter(indent=2,depth=1,)
class RdfBaseClass(object):
	_reserved = ['add_property',
				 '_format',
				 '_reserved',
				 '_subject']

	def __init__(self, sub):
		self._subject = sub

	def add_property(self, pred, obj):
		if hasattr(self, pred):
			#pdb.set_trace()
			if isinstance(getattr(self, pred), list):
				new_list = getattr(self, pred)				
			else:
				new_list = [getattr(self, pred)]
			setattr(self, pred, new_list.append(obj))
			#pdb.set_trace()
		else:
			setattr(self, pred, obj)

	# def __repr__(self):
	# 	return pp.pformat(self._format())

	def _format(self):
		return_val = {}
		for attr in dir(self):
			if attr not in self._reserved and not attr.startswith("__"):
				print(attr)
				return_val[attr] = getattr(self, attr)
		return return_val

class RdfDataset(object):
	""" A container for holding rdf data """
	_reserved = ['add_triple',
				  '_format',
				  '_reserved',
				  '_link_objects']

	def add_triple(self, sub, pred=None, obj=None, map={}):
		""" Adds a triple to the dataset 

			args:
				sub: The subject of the triple or dictionary contaning a
					 triple
				pred: Optional if supplied in sub, predicate of the triple
				obj:  Optional if supplied in sub, object of the triple
				map: Optional, a ditionary mapping for a supplied dictionary
		"""
		if isinstance(sub, dict):
			pred = sub[map.get('p','p')]
			obj = sub[map.get('o','o')]
			sub = sub[map.get('s','s')]
		pred = pyrdf(pred)
		obj = pyrdf(obj)
		sub = pyrdf(sub)
		
		if hasattr(self, sub):
			print("exists - %s %s %s" % (sub.sparql, pred.sparql, obj.sparql))
			getattr(self,sub).add_property(pred, obj)
		else:
			new_class = RdfBaseClass(sub)
			new_class.add_property(pred, obj)
			setattr(self, sub, new_class)
			print("new - %s %s %s" % (sub.sparql, pred.sparql, obj.sparql))
		#self._link_objects()

	# def __repr__(self):
	# 	return pp.pformat(self._format())

	def _format(self):
		return_val = {}
		for attr in dir(self):
			if attr not in self._reserved and not attr.startswith("__"):
				return_val[attr] = getattr(self, attr)
		return return_val

	# def _link_objects(self):
	# 	for attr in dir(self):
	# 		if attr not in self._reserved and not attr.startswith("__"):
	# 			temp = getattr(self, attr)
	# 			for class_attr in dir(temp):
					
	# 				print(class_attr)
					
	# 				if class_attr not in temp._reserved and not \
	# 						class_attr.startswith("__"):
	# 					if isinstance(getattr(temp, class_attr), list):
	# 						for i, item in enumerate(getattr(temp, class_attr):

	# 						if hasattr(getattr(temp, class_attr), 'type') and \
	# 								getattr(temp, class_attr).type == 'bnode':
	# 							if hasattr(self, getattr(temp, class_attr)):
	# 								pdb.set_trace()
	# 								setattr(temp, class_attr, getattr(self, getattr(temp, class_attr)))

	def load_data(self, data):
		if isinstance(data, list):
			data = self._convert_results(data)
		self._group_data(data)
		# generate classes and add attributes to the data
		# self._generate_classes(self.class_types, self.non_defined)
		# add triples to the dataset
		# for triple in self.data:
		# 	self.add_triple(triple)

	def _group_data(self, data):
		# strip all of the rdf_type triples
		class_types = self._get_classtypes(data)
		# merge class_types with it mulitple rdf_types
		self.class_types = self._merge_classtypes(class_types)
		# get non defined classes
		#self.non_defined = self._get_non_defined(data, class_types)
		#self.data = data
		

	@staticmethod
	def _get_blanks(data):
		rtn_list = []
		for i, triple in enumerate(data):
			if triple.s.type == "bnode":
				rtn_list.append(data.pop(i))
		return rtn_list

	@staticmethod
	def _get_classtypes(data):
		rtn_list = []
		for i, triple in enumerate(data):
			if triple.p == "rdf:type":
				rtn_list.append(data.pop(i))
		return rtn_list

	@staticmethod
	def _merge_classtypes(data):
		obj = {} 
		for i, triple in enumerate(data):
			if triple.s in obj.keys():
				obj[triple.s].o = make_list(obj[triple.s].o).append(triple.o)
			else:
				obj[triple.s] = triple
		return list(obj.values())

	@staticmethod	
	def _convert_results(data):
		converted_data = []
		converted_data = convert_query_results(data)
		# for triple in data:
		# 	converted_data.append(convert_to_class(triple))
		return converted_data

ds = RdfDataset()
ds.load_data(z)
# for x in z:
# 	ds.add_triple(x)
# ds._link_objects()