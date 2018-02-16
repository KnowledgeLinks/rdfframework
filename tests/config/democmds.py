import validconfig as config, json, pdb
from rdfframework.configuration import RdfConfigManager
from rdfframework import rdfclass
from rdfframework.utilities import colors
from rdfframework.datatypes import Uri

cfg = RdfConfigManager(config, turn_on_vocab=True)
from rdfframework.datatypes import XsdString
tutt = rdfclass.schema_Organization("http://tutt.edu/")
tutt.schema_name.append(XsdString("Tutt Library"))
from rdfframework.datasets import RdfDataset
x = RdfDataset()
x[tutt.subject] = tutt
conn = cfg.conns.datastore
import rdfframework.sparql as sp
print(colors.white.blue("  Instance Example                                                                                   "))
data = sp.get_all_item_data('https://plains2peaks.org/1f142250-0871-11e8-ad63-005056c00008', conn)
item = RdfDataset(data, "https://plains2peaks.org/1f142250-0871-11e8-ad63-005056c00008")
print(json.dumps(item[item.base_uri].es_json(), indent=8))
print(colors.white.blue("  Work Example                                                                                        "))
# data2 = sp.get_all_item_data('<https://plains2peaks.org/1f142250-0871-11e8-ad63-005056c00008#Work>', conn)
# work = RdfDataset(data2, "<https://plains2peaks.org/1f142250-0871-11e8-ad63-005056c00008#Work>")
data3 = sp.get_all_item_data('<https://plains2peaks.org/20497be2-732c-11e7-b6f2-005056c00008#Work>', conn)
work = RdfDataset(data3, "<https://plains2peaks.org/20497be2-732c-11e7-b6f2-005056c00008#Work>")

# print(colors.white.magenta(" Triples            "))
# print(colors.blue)
# work.triples("view")
# print(colors.white.magenta(" All values         "))
# print(colors.hd(work.format(remove='bnode', sort=True, pretty=True, compress=False, output='json', add_ids=True)))
print(colors.white.magenta(" Elasticsearch values         "))
print(colors.cyan(json.dumps(work[work.base_uri].es_json(), indent=8)))
# print(colors.white.blue("  DOC STRING Examples                                                                                "))
# print(colors.white.magenta("  bf:Topic                     "))
# print(colors.cyan(rdfclass.bf_Topic.__doc__))
# print(colors.white.magenta("  schema:Person                     "))
# print(colors.yellow(rdfclass.schema_Person.__doc__))

