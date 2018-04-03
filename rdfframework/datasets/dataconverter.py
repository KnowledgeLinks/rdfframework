"""    This module is used for setting an intial test configs and values for
the rdfframework """
import datetime
import multiprocessing as mp
import multiprocessing.managers as managers
import pdb

from rdfframework.utilities import SimpleMapReduce
from rdfframework.datatypes import pyrdf, BaseRdfDataType, Uri

def convert_batch(data, output=None):
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
    print("starting")
    # data_l = len(data)
    # i = 0
    # while i < data_l:
    #     converted = []
    #     for row in data[i:i+1000]:
    #         converted.append({key:pyrdf(value) for key, value in row.items()})

    #         i += 1
    #     output.put(converted)
    for row in data:
        # output.append({key:pyrdf(value) for key, value in row.items()})
        output.put([{key:pyrdf(value) for key, value in row.items()}])

    # converted = [{key:pyrdf(value) for key, value in row.items()}
    #              for row in data]
    print("converted")
    # output.put(converted)
    return
    # return (val[1], val[2], pyrdf(val[0]),)
    # output.put((i, key, pyrdf(val),))
    # return (i, key, pyrdf(val),)
    # output.put({key:pyrdf(value) for key, value in row.items()})

class SharedManager(managers.BaseManager):
    pass

def convert_results(data, **kwargs):
    """ converts the results of a query to RdfDatatype instances

        args:
            data: a list of triples
    """
    if kwargs.get("multiprocessing", False):
        manager = SharedManager()
        manager.register("BaseRdfDataType", BaseRdfDataType)
        manager.register("Uri", Uri)

        data_l = len(data)
        group_size = data_l // pool_size
        if data_l % pool_size:
            group_size += 1
        split_data = [data[i:i + group_size]
                      for i in range(0, data_l, group_size)]
        output = manager.Queue()
        # output = manager.list()
        # output_data = POOL.map(convert_row, split_data)
        workers = [mp.Process(target=convert_batch, args=(item, output,))
                   for item in split_data]
        for worker in workers:
            # worker.Daemon = True
            worker.start()
        results = []
        while True:
            running = any(p.is_alive() for p in workers)
            while not output.empty():
               results += output.get()
            if not running:
                break
        print("Finished - workers not stoped")
        for worker in workers:
            worker.join()
        # pdb.set_trace()
        # return output
        for i in range(output.qsize()):
            results += output.get()
        return results
    else:
        return [{key:pyrdf(value) for key, value in row.items()}
                for row in data]

pool_size = mp.cpu_count() - 1 or 1

def time_test(data, **kwargs):
    start = datetime.datetime.now()
    x = convert_results(data, **kwargs)
    print("time: ", (datetime.datetime.now() - start), " ", kwargs, " - len: ", len(x))



DATA = [
 {'o': {'type': 'uri', 'value': 'http://id.loc.gov/ontologies/bibframe/Agent'},
  'p': {'type': 'uri',
        'value': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#type'},
  's': {'type': 'uri', 'value': 'https://plains2peaks.org/agent/chris-clark'}},
 {'o': {'type': 'literal', 'value': 'Chris Clark'},
  'p': {'type': 'uri',
        'value': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#value'},
  's': {'type': 'uri', 'value': 'https://plains2peaks.org/agent/chris-clark'}},
 {'o': {'type': 'uri',
        'value': 'http://id.loc.gov/ontologies/bibframe/Collection'},
  'p': {'type': 'uri',
        'value': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#type'},
  's': {'type': 'uri',
        'value': 'https://plains2peaks.org/marmot-collection/veterans-remember'}},
 {'o': {'type': 'literal', 'value': 'Veterans Remember'},
  'p': {'type': 'uri', 'value': 'http://www.w3.org/2000/01/rdf-schema#label'},
  's': {'type': 'uri',
        'value': 'https://plains2peaks.org/marmot-collection/veterans-remember'}},
 {'o': {'type': 'uri', 'value': 'http://id.loc.gov/ontologies/bibframe/Topic'},
  'p': {'type': 'uri',
        'value': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#type'},
  's': {'type': 'uri', 'value': 'https://plains2peaks.org/topic/970west'}},
 {'o': {'type': 'literal', 'value': '970west'},
  'p': {'type': 'uri',
        'value': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#value'},
  's': {'type': 'uri', 'value': 'https://plains2peaks.org/topic/970west'}},
 {'o': {'type': 'uri', 'value': 'http://id.loc.gov/ontologies/bibframe/Topic'},
  'p': {'type': 'uri',
        'value': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#type'},
  's': {'type': 'uri',
        'value': 'https://plains2peaks.org/topic/970west-veterans-remember'}},
 {'o': {'type': 'literal', 'value': '970west -- veterans remember'},
  'p': {'type': 'uri',
        'value': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#value'},
  's': {'type': 'uri',
        'value': 'https://plains2peaks.org/topic/970west-veterans-remember'}},
 {'o': {'type': 'uri', 'value': 'http://id.loc.gov/ontologies/bibframe/Topic'},
  'p': {'type': 'uri',
        'value': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#type'},
  's': {'type': 'uri', 'value': 'https://plains2peaks.org/topic/wwii'}},
 {'o': {'type': 'literal', 'value': 'wwii'},
  'p': {'type': 'uri',
        'value': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#value'},
  's': {'type': 'uri', 'value': 'https://plains2peaks.org/topic/wwii'}},
 {'o': {'type': 'uri', 'value': 'http://id.loc.gov/ontologies/bibframe/Agent'},
  'p': {'type': 'uri',
        'value': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#type'},
  's': {'type': 'uri',
        'value': 'https://plains2peaks.org/agent/charlie-blackmer'}},
 {'o': {'type': 'literal', 'value': 'Charlie Blackmer'},
  'p': {'type': 'uri',
        'value': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#value'},
  's': {'type': 'uri',
        'value': 'https://plains2peaks.org/agent/charlie-blackmer'}},
 {'o': {'type': 'uri', 'value': 'http://id.loc.gov/ontologies/bibframe/Agent'},
  'p': {'type': 'uri',
        'value': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#type'},
  's': {'type': 'uri',
        'value': 'https://plains2peaks.org/agent/laura-mullenix'}},
 {'o': {'type': 'literal', 'value': 'Laura Mullenix'},
  'p': {'type': 'uri',
        'value': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#value'},
  's': {'type': 'uri',
        'value': 'https://plains2peaks.org/agent/laura-mullenix'}},
 {'o': {'type': 'uri', 'value': 'http://id.loc.gov/ontologies/bibframe/Topic'},
  'p': {'type': 'uri',
        'value': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#type'},
  's': {'type': 'uri',
        'value': 'https://plains2peaks.org/topic/interview-with-ralph-dorn'}},
 {'o': {'type': 'literal', 'value': 'Interview with Ralph Dorn'},
  'p': {'type': 'uri',
        'value': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#value'},
  's': {'type': 'uri',
        'value': 'https://plains2peaks.org/topic/interview-with-ralph-dorn'}},
 {'o': {'type': 'uri', 'value': 'http://id.loc.gov/ontologies/bibframe/Place'},
  'p': {'type': 'uri',
        'value': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#type'},
  's': {'type': 'bnode', 'value': 't3186684'}},
 {'o': {'type': 'literal', 'value': 'Grand Junction, Colorado'},
  'p': {'type': 'uri',
        'value': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#value'},
  's': {'type': 'bnode', 'value': 't3186684'}},
 {'o': {'type': 'uri',
        'value': 'http://id.loc.gov/ontologies/bibframe/Summary'},
  'p': {'type': 'uri',
        'value': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#type'},
  's': {'type': 'bnode', 'value': 't3193326'}},
 {'o': {'type': 'literal',
        'value': 'Interview with Mesa County Libraries production team.'},
  'p': {'type': 'uri',
        'value': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#value'},
  's': {'type': 'bnode', 'value': 't3193326'}},
 {'o': {'type': 'uri',
        'value': 'https://plains2peaks.org/d573941e-82c6-11e7-b159-005056c00008#Work'},
  'p': {'type': 'uri',
        'value': 'http://id.loc.gov/ontologies/bibframe/instanceOf'},
  's': {'type': 'uri',
        'value': 'https://plains2peaks.org/d573941e-82c6-11e7-b159-005056c00008'}},
 {'o': {'type': 'uri',
        'value': 'https://plains2peaks.org/marmot-collection/veterans-remember'},
  'p': {'type': 'uri', 'value': 'http://id.loc.gov/ontologies/bibframe/partOf'},
  's': {'type': 'uri',
        'value': 'https://plains2peaks.org/d573941e-82c6-11e7-b159-005056c00008#Work'}},
 {'o': {'type': 'uri', 'value': 'https://plains2peaks.org/topic/970west'},
  'p': {'type': 'uri',
        'value': 'http://id.loc.gov/ontologies/bibframe/subject'},
  's': {'type': 'uri',
        'value': 'https://plains2peaks.org/d573941e-82c6-11e7-b159-005056c00008#Work'}},
 {'o': {'type': 'uri',
        'value': 'https://plains2peaks.org/topic/970west-veterans-remember'},
  'p': {'type': 'uri',
        'value': 'http://id.loc.gov/ontologies/bibframe/subject'},
  's': {'type': 'uri',
        'value': 'https://plains2peaks.org/d573941e-82c6-11e7-b159-005056c00008#Work'}},
 {'o': {'type': 'uri', 'value': 'https://plains2peaks.org/topic/wwii'},
  'p': {'type': 'uri',
        'value': 'http://id.loc.gov/ontologies/bibframe/subject'},
  's': {'type': 'uri',
        'value': 'https://plains2peaks.org/d573941e-82c6-11e7-b159-005056c00008#Work'}},
 {'o': {'type': 'uri',
        'value': 'https://plains2peaks.org/topic/interview-with-ralph-dorn'},
  'p': {'type': 'uri',
        'value': 'http://id.loc.gov/ontologies/bibframe/subject'},
  's': {'type': 'uri',
        'value': 'https://plains2peaks.org/d573941e-82c6-11e7-b159-005056c00008#Work'}},
 {'o': {'type': 'bnode', 'value': 't3186684'},
  'p': {'type': 'uri',
        'value': 'http://id.loc.gov/ontologies/bibframe/subject'},
  's': {'type': 'uri',
        'value': 'https://plains2peaks.org/d573941e-82c6-11e7-b159-005056c00008#Work'}},
 {'o': {'type': 'uri', 'value': 'https://plains2peaks.org/agent/chris-clark'},
  'p': {'type': 'uri', 'value': 'http://id.loc.gov/vocabulary/relators/cre'},
  's': {'type': 'uri',
        'value': 'https://plains2peaks.org/d573941e-82c6-11e7-b159-005056c00008#Work'}},
 {'o': {'type': 'uri',
        'value': 'https://plains2peaks.org/agent/charlie-blackmer'},
  'p': {'type': 'uri', 'value': 'http://id.loc.gov/vocabulary/relators/cre'},
  's': {'type': 'uri',
        'value': 'https://plains2peaks.org/d573941e-82c6-11e7-b159-005056c00008#Work'}},
 {'o': {'type': 'uri',
        'value': 'https://plains2peaks.org/agent/laura-mullenix'},
  'p': {'type': 'uri', 'value': 'http://id.loc.gov/vocabulary/relators/cre'},
  's': {'type': 'uri',
        'value': 'https://plains2peaks.org/d573941e-82c6-11e7-b159-005056c00008#Work'}},
 {'o': {'type': 'bnode', 'value': 't3193326'},
  'p': {'type': 'uri',
        'value': 'http://id.loc.gov/ontologies/bibframe/summary'},
  's': {'type': 'uri',
        'value': 'https://plains2peaks.org/d573941e-82c6-11e7-b159-005056c00008#Work'}},
 {'o': {'datatype': 'http://www.w3.org/2001/XMLSchema#dateTime',
        'type': 'literal',
        'value': '2018-03-28T21:01:01.049Z'},
  'p': {'type': 'uri',
        'value': 'http://knowledgelinks.io/ns/data-structures/esIndexTime'},
  's': {'type': 'uri',
        'value': 'https://plains2peaks.org/d573941e-82c6-11e7-b159-005056c00008#Work'}},
 {'o': {'type': 'uri', 'value': 'http://id.loc.gov/ontologies/bibframe/Work'},
  'p': {'type': 'uri',
        'value': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#type'},
  's': {'type': 'uri',
        'value': 'https://plains2peaks.org/d573941e-82c6-11e7-b159-005056c00008#Work'}},
 {'o': {'type': 'uri',
        'value': 'http://id.loc.gov/ontologies/bibframe/MovingImage'},
  'p': {'type': 'uri',
        'value': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#type'},
  's': {'type': 'uri',
        'value': 'https://plains2peaks.org/d573941e-82c6-11e7-b159-005056c00008#Work'}},
 {'o': {'type': 'uri', 'value': 'http://id.loc.gov/ontologies/bibframe/Local'},
  'p': {'type': 'uri',
        'value': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#type'},
  's': {'type': 'bnode', 'value': 't3190361'}},
 {'o': {'type': 'literal', 'value': 'mesa:48'},
  'p': {'type': 'uri',
        'value': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#value'},
  's': {'type': 'bnode', 'value': 't3190361'}},
 {'o': {'type': 'uri',
        'value': 'https://plains2peaks.org/agent/mesa-county-libraries'},
  'p': {'type': 'uri', 'value': 'http://id.loc.gov/ontologies/bibframe/agent'},
  's': {'type': 'bnode', 'value': 't3192025'}},
 {'o': {'type': 'uri',
        'value': 'http://id.loc.gov/ontologies/bibframe/Manufacture'},
  'p': {'type': 'uri',
        'value': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#type'},
  's': {'type': 'bnode', 'value': 't3192025'}},
 {'o': {'type': 'literal', 'value': '2017-08-16T21:06:55.434652'},
  'p': {'type': 'uri',
        'value': 'http://id.loc.gov/ontologies/bibframe/generationDate'},
  's': {'type': 'bnode', 'value': 't3194298'}},
 {'o': {'type': 'uri',
        'value': 'http://id.loc.gov/ontologies/bibframe/GenerationProcess'},
  'p': {'type': 'uri',
        'value': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#type'},
  's': {'type': 'bnode', 'value': 't3194298'}},
 {'o': {'type': 'literal',
        'value': 'Generated by BIBCAT version i1.13.0 from KnowledgeLinks.io',
        'xml:lang': 'en'},
  'p': {'type': 'uri',
        'value': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#value'},
  's': {'type': 'bnode', 'value': 't3194298'}},
 {'o': {'type': 'uri', 'value': 'https://plains2peaks.org/agent/ralph-dorn'},
  'p': {'type': 'uri', 'value': 'http://id.loc.gov/ontologies/bibframe/agent'},
  's': {'type': 'bnode', 'value': 't3194722'}},
 {'o': {'type': 'uri',
        'value': 'http://id.loc.gov/ontologies/bibframe/Manufacture'},
  'p': {'type': 'uri',
        'value': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#type'},
  's': {'type': 'bnode', 'value': 't3194722'}},
 {'o': {'type': 'literal', 'value': 'Interview with Ralph Dorn'},
  'p': {'type': 'uri',
        'value': 'http://id.loc.gov/ontologies/bibframe/mainTitle'},
  's': {'type': 'bnode', 'value': 't3196122'}},
 {'o': {'type': 'uri', 'value': 'http://id.loc.gov/ontologies/bibframe/Title'},
  'p': {'type': 'uri',
        'value': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#type'},
  's': {'type': 'bnode', 'value': 't3196122'}},
 {'o': {'type': 'literal', 'value': 'Interview with Ralph Dorn'},
  'p': {'type': 'uri', 'value': 'http://www.w3.org/2000/01/rdf-schema#label'},
  's': {'type': 'bnode', 'value': 't3196122'}},
 {'o': {'type': 'uri',
        'value': 'http://id.loc.gov/ontologies/bibframe/Carrier'},
  'p': {'type': 'uri',
        'value': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#type'},
  's': {'type': 'bnode', 'value': 't3196572'}},
 {'o': {'type': 'literal', 'value': 'Moving Image'},
  'p': {'type': 'uri',
        'value': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#value'},
  's': {'type': 'bnode', 'value': 't3196572'}},
 {'o': {'type': 'uri', 'value': 'https://marmot.org/'},
  'p': {'type': 'uri', 'value': 'http://id.loc.gov/ontologies/bibframe/agent'},
  's': {'type': 'bnode', 'value': 't3199929'}},
 {'o': {'type': 'uri',
        'value': 'http://id.loc.gov/ontologies/bibframe/Distribution'},
  'p': {'type': 'uri',
        'value': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#type'},
  's': {'type': 'bnode', 'value': 't3199929'}},
 {'o': {'type': 'uri',
        'value': 'http://id.loc.gov/ontologies/bibframe/CoverArt'},
  'p': {'type': 'uri',
        'value': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#type'},
  's': {'type': 'bnode', 'value': 't3200840'}},
 {'o': {'type': 'uri',
        'value': 'https://islandora.marmot.org/islandora/object/mesa:48/datastream/TN/view'},
  'p': {'type': 'uri',
        'value': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#value'},
  's': {'type': 'bnode', 'value': 't3200840'}},
 {'o': {'type': 'uri', 'value': 'https://mesacountylibraries.org/'},
  'p': {'type': 'uri', 'value': 'http://id.loc.gov/ontologies/bibframe/agent'},
  's': {'type': 'bnode', 'value': 't3202252'}},
 {'o': {'type': 'uri',
        'value': 'http://id.loc.gov/ontologies/bibframe/Publication'},
  'p': {'type': 'uri',
        'value': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#type'},
  's': {'type': 'bnode', 'value': 't3202252'}},
 {'o': {'type': 'uri',
        'value': 'http://id.loc.gov/ontologies/bibframe/Organization'},
  'p': {'type': 'uri',
        'value': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#type'},
  's': {'type': 'uri', 'value': 'https://marmot.org/'}},
 {'o': {'type': 'uri', 'value': 'http://schema.org/NGO'},
  'p': {'type': 'uri',
        'value': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#type'},
  's': {'type': 'uri', 'value': 'https://marmot.org/'}},
 {'o': {'type': 'literal', 'value': 'Marmot Library Network', 'xml:lang': 'en'},
  'p': {'type': 'uri', 'value': 'http://www.w3.org/2000/01/rdf-schema#label'},
  's': {'type': 'uri', 'value': 'https://marmot.org/'}},
 {'o': {'type': 'uri',
        'value': 'http://id.loc.gov/ontologies/bibframe/Organization'},
  'p': {'type': 'uri',
        'value': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#type'},
  's': {'type': 'uri', 'value': 'https://mesacountylibraries.org/'}},
 {'o': {'type': 'uri', 'value': 'http://schema.org/Library'},
  'p': {'type': 'uri',
        'value': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#type'},
  's': {'type': 'uri', 'value': 'https://mesacountylibraries.org/'}},
 {'o': {'type': 'literal', 'value': 'Mesa County Libraries', 'xml:lang': 'en'},
  'p': {'type': 'uri', 'value': 'http://www.w3.org/2000/01/rdf-schema#label'},
  's': {'type': 'uri', 'value': 'https://mesacountylibraries.org/'}},
 {'o': {'type': 'uri', 'value': 'http://id.loc.gov/ontologies/bibframe/Agent'},
  'p': {'type': 'uri',
        'value': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#type'},
  's': {'type': 'uri',
        'value': 'https://plains2peaks.org/agent/mesa-county-libraries'}},
 {'o': {'type': 'literal', 'value': 'Mesa County Libraries'},
  'p': {'type': 'uri',
        'value': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#value'},
  's': {'type': 'uri',
        'value': 'https://plains2peaks.org/agent/mesa-county-libraries'}},
 {'o': {'type': 'uri', 'value': 'http://id.loc.gov/ontologies/bibframe/Agent'},
  'p': {'type': 'uri',
        'value': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#type'},
  's': {'type': 'uri', 'value': 'https://plains2peaks.org/agent/ralph-dorn'}},
 {'o': {'type': 'literal', 'value': 'Ralph Dorn'},
  'p': {'type': 'uri',
        'value': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#value'},
  's': {'type': 'uri', 'value': 'https://plains2peaks.org/agent/ralph-dorn'}},
 {'o': {'type': 'bnode', 'value': 't3194298'},
  'p': {'type': 'uri',
        'value': 'http://id.loc.gov/ontologies/bibframe/generationProcess'},
  's': {'type': 'uri',
        'value': 'https://plains2peaks.org/d573941e-82c6-11e7-b159-005056c00008'}},
 {'o': {'type': 'bnode', 'value': 't3196122'},
  'p': {'type': 'uri', 'value': 'http://id.loc.gov/ontologies/bibframe/title'},
  's': {'type': 'uri',
        'value': 'https://plains2peaks.org/d573941e-82c6-11e7-b159-005056c00008'}},
 {'o': {'type': 'bnode', 'value': 't3200840'},
  'p': {'type': 'uri',
        'value': 'http://id.loc.gov/ontologies/bibframe/coverArt'},
  's': {'type': 'uri',
        'value': 'https://plains2peaks.org/d573941e-82c6-11e7-b159-005056c00008'}},
 {'o': {'type': 'bnode', 'value': 't3192025'},
  'p': {'type': 'uri',
        'value': 'http://id.loc.gov/ontologies/bibframe/provisionActivity'},
  's': {'type': 'uri',
        'value': 'https://plains2peaks.org/d573941e-82c6-11e7-b159-005056c00008'}},
 {'o': {'type': 'bnode', 'value': 't3194722'},
  'p': {'type': 'uri',
        'value': 'http://id.loc.gov/ontologies/bibframe/provisionActivity'},
  's': {'type': 'uri',
        'value': 'https://plains2peaks.org/d573941e-82c6-11e7-b159-005056c00008'}},
 {'o': {'type': 'bnode', 'value': 't3199929'},
  'p': {'type': 'uri',
        'value': 'http://id.loc.gov/ontologies/bibframe/provisionActivity'},
  's': {'type': 'uri',
        'value': 'https://plains2peaks.org/d573941e-82c6-11e7-b159-005056c00008'}},
 {'o': {'type': 'bnode', 'value': 't3202252'},
  'p': {'type': 'uri',
        'value': 'http://id.loc.gov/ontologies/bibframe/provisionActivity'},
  's': {'type': 'uri',
        'value': 'https://plains2peaks.org/d573941e-82c6-11e7-b159-005056c00008'}},
 {'o': {'type': 'bnode', 'value': 't3196572'},
  'p': {'type': 'uri',
        'value': 'http://id.loc.gov/ontologies/bibframe/carrier'},
  's': {'type': 'uri',
        'value': 'https://plains2peaks.org/d573941e-82c6-11e7-b159-005056c00008'}},
 {'o': {'type': 'bnode', 'value': 't3190361'},
  'p': {'type': 'uri',
        'value': 'http://id.loc.gov/ontologies/bibframe/identifiedBy'},
  's': {'type': 'uri',
        'value': 'https://plains2peaks.org/d573941e-82c6-11e7-b159-005056c00008'}},
 {'o': {'type': 'uri',
        'value': 'http://id.loc.gov/ontologies/bibframe/Instance'},
  'p': {'type': 'uri',
        'value': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#type'},
  's': {'type': 'uri',
        'value': 'https://plains2peaks.org/d573941e-82c6-11e7-b159-005056c00008'}}]

if __name__ == '__main__':
    time_test(DATA)
    time_test(DATA, multiprocessing=True)
    time_test(DATA)
    time_test(DATA, multiprocessing=True)
    from rdfframework.sparql import get_all_item_data
    from rdfframework.connections import Blazegraph
    from rdfframework.datatypes import RdfNsManager
    RdfNsManager({"bf": "http://id.loc.gov/ontologies/bibframe/"})
    data_iri = "<https://plains2peaks.org/d573941e-82c6-11e7-b159-005056c00008>"
    conn = Blazegraph(namespace="plain2peak")
    data = get_all_item_data(data_iri, conn)
    print("data count: ", len(data))
    time_test(data)
    time_test(data, multiprocessing=True)
