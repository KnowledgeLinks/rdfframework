import validconfig as config, json, pdb, pprint
from rdfframework.configuration import RdfConfigManager
from rdfframework import rdfclass
from rdfframework.utilities import colors
from rdfframework.datatypes import Uri, XsdBoolean
from rdfframework.datasets import RdfDataset
from rdfframework import search
from rdfframework.sparql import get_all_item_data
import rdfframework, datetime
rdfframework.configure_logging(rdfframework.__modules__, "dummy")
import cProfile
cfg = RdfConfigManager(config.__dict__) #, turn_on_vocab=False)
from rdfframework.datatypes import XsdString
tutt = rdfclass.schema_Organization("http://tutt.edu/")
tutt.add_property('schema_name', XsdString("Tutt Library"))
from rdfframework.datasets import RdfDataset
x = RdfDataset()
x[tutt.subject] = tutt
conn = cfg.conns.datastore
import rdfframework.sparql as sp
# print(colors.white.blue("  Instance Example                                                                                   "))
# data = sp.get_all_item_data('<https://plains2peaks.org/20497be2-732c-11e7-b6f2-005056c00008>', conn)
# item = RdfDataset(data, "<https://plains2peaks.org/20497be2-732c-11e7-b6f2-005056c00008>")
# item[item.base_uri].add_property(cfg.nsm.bf.test, XsdBoolean(True))
# print(json.dumps(item[item.base_uri].es_json(), indent=8))
# print(item[item.base_uri].es_json())
print(colors.white.blue("  Work Example                                                                                        "))
# # data2 = sp.get_all_item_data('<https://plains2peaks.org/1f142250-0871-11e8-ad63-005056c00008#Work>', conn)
# # work = RdfDataset(data2, "<https://plains2peaks.org/1f142250-0871-11e8-ad63-005056c00008#Work>")
# data_uri = "<https://plains2peaks.org/5a6169c0-77ef-11e7-abd0-005056c00008#Work>"
data_uri = "<https://plains2peaks.org/8bb38f18-0ba8-11e8-b4aa-005056c00008#Work>"
data_uri = "<https://plains2peaks.org/98c03b42-83b7-11e7-8180-ac87a3129ce6#Work>"
data3 = sp.get_all_item_data(data_uri,
                             conn,
                             rdfclass=rdfclass.bf_Work)
work = RdfDataset(data3, data_uri)
from rdfframework.rml.processor import SPARQLProcessor
# SCHEMA_PROCESSOR = SPARQLProcessor(
#     conn=cfg.conns.datastore,
#     rml_rules=["bf-to-schema_rdfw.ttl"])
from bibcat.rml.processor import SPARQLProcessor as SPARQLProcessorOrig

instance_iri = "https://plains2peaks.org/98c01afe-83b7-11e7-83be-ac87a3129ce6"
item_iri = "http://digitalcollections.uwyo.edu/luna/servlet" \
           "/detail/uwydbuwy~96~96~3373447~294069"
print("init processor")
MAP4_PROCESSOR = SPARQLProcessor(
    conn=cfg.conns.datastore,
    rml_rules=["bf-to-map4.ttl"])
ORIG4_PROCESSOR = SPARQLProcessorOrig(
    triplestore_url='http://localhost:9999/blazegraph/namespace/plain2peak'
                    '/sparql',
    rml_rules=["bf-to-map4.ttl"])
print("init completed")
MAP4_PROCESSOR.run(dataset=work,
                   instance_iri=instance_iri,
                   item_iri=item_iri)
out = MAP4_PROCESSOR.output
MAP4_PROCESSOR.use_json_qry = False
ORIG4_PROCESSOR.run(dataset=work,
                   instance_iri=instance_iri,
                   item_iri=item_iri)
out2 = ORIG4_PROCESSOR.output
print(out.serialize(format="json-ld",
                    context=dict(cfg.nsm.namespaces)).decode())
print(out2.serialize(format="json-ld",
                     context=dict(cfg.nsm.namespaces)).decode())
# print(colors.cyan(json.dumps(work[work.base_uri].es_json(), indent=8)))

#
# mp = search.EsMappings()
# ref = mp.mapping_ref(mp.get_es_mappings())['catalog/work']
# pprint.pprint(ref)
# s = search.EsRdfBulkLoader(rdfclass.bf_Work, cfg.conns.datastore, cfg.conns.search)
# s.batch_data = {}
# s.batch_data[0] = []
# uri_list = s._get_uri_list()[:1000]
# # qdata = s.run_query(uri_list)
# cProfile.runctx('data = s._index_sub(uri_list, 0, 0)', globals(), locals())
def run():
    with open("/home/stabiledev/rdfw_base/logs/batch_list.txt", "rb") as fo:
        data = json.loads(fo.read().decode())
    filename = "/home/stabiledev/rdfw_base/logs/qrytime.csv"
    fo = open(filename, "w")
    fo.write("Number,Time,Uri,Count\n")
    i=0
    count = 0
    for batch, items in data.items():
        count += len(items)
    print("query test for %s items" % count)
    for batch, items in data.items():
        for item in items:
            start = datetime.datetime.now()
            r = get_all_item_data(item, conn, rdfclass=rdfclass.bf_Work)
            end = datetime.datetime.now()
            i += 1
            stats = "%s,%s,%s,%s" % (i, end-start, item, len(r))
            print(stats)
            fo.write(stats + "\n")
    fo.close()
