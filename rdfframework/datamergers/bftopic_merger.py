import os
import logging
import inspect

from rdfframework.configuration import RdfConfigManager, RdfNsManager

MNAME = "%s.%s" % \
        (os.path.basename(os.path.split(inspect.stack()[0][1])[0]),
         os.path.basename(inspect.stack()[0][1]))
LOG_LEVEL = logging.DEBUG

CFG = RdfConfigManager()
NSM = RdfNsManager()

CONVERT_BN_TO_URIS = """
DELETE {
    ?bn ?bn_p ?bn_o .
    ?f ?fp ?bn .
}
INSERT {
    ?f ?fp ?id .
    ?id ?bn_p ?bn_o.
}
where
{
    ?bn a bf:Topic .
    filter(isblank(?bn))
    ?bn rdfs:label ?o .
    ?bn ?bn_p ?bn_o .
    ?f ?fp ?bn .
    BIND (IRI(concat(REPLACE(str(?f),"#Work","#Topic"),'/',ENCODE_FOR_URI(?o))) as ?id)
}
"""

GET_MERGE_URIS = """
# This groups on the object literal and concats all of the subjects that
# have the same value

select ?uris
{
    {
        select (count(?s) as ?c) (group_concat(?i; separator=",") as ?uris)
        {
            ?s a bf:Topic .
            ?s skos:prefLabel ?o.
            BIND (concat('<',str(?s),'>') as ?i)
        }
        group by ?o
    }
    filter(?c!=1)
}
"""

CONVERT_LABEL = """
# The Loc Subject graph uses skos:prefLabel vs rdfs:label, also none of the
# subject headings end in a period or /. This query corrects those
DELETE {
  ?s rdfs:label ?o.
}
INSERT {
  ?s skos:prefLabel ?new_value.
}
WHERE
{
    ?s a bf:Topic .
    ?s rdfs:label ?o.
    BIND(REPLACE(?o, "[ .\n\t/]+$", "") as ?new_value)
}
"""

UPDATE_OLD_OBJ_REF = """
DELETE {
 ?s ?p ?old
}
INSERT {
 ?s ?p ?new
}
WHERE {
  ?old kds:mergeWith ?new.
  ?s ?p ?old
}
"""

DELETE_OLD = """
DELETE {
 ?old ?p ?o .
}
WHERE {
  ?old kds:mergeWith ?new.
  ?old ?p ?o
}
"""

class SparqlMerger(object):
    """ Base class of merging rdf class instances via spaqrl """
    ln = "%s-SparqlMerger" % MNAME
    log_level = logging.DEBUG

    local_filename = "owltags.ttl"

    def __init__(self, conn, uri_select_query, namespace):
        self.conn = conn
        self.uri_select_query = uri_select_query
        self.namespace = namespace

    def run(self):
        self.get_uris()
        self.create_same_as_file()
        self.send_to_tstore()
        self.delete_local_file()
        self.merge_instances()

    def get_uris(self):
        # first convert all blanknode topics to URIs
        lg = logging.getLogger("%s.%s" % (self.ln, inspect.stack()[0][3]))
        lg.setLevel(self.log_level)

        lg.info("Converting BNs to URIs")
        self.conn.query(CONVERT_BN_TO_URIS,
                         namespace=self.namespace,
                         mode='update')
        lg.info("FINISHED converting BNs to URIs")
        lg.info("Getting URI list")
        self.uri_list = self.conn.query(self.uri_select_query,
                                         namespace=self.namespace)

    def create_same_as_file(self):
        """ creates a local data file with all of the owl:sameAs tags """

        def find_preferred_uri(uri_list):
            index = None
            for i, uri in enumerate(uri_list):
                if uri.startswith("<http://id.loc.gov/authorities/subjects/"):
                        index = i
                        print(uri)
                        break
            if not index:
                for i, uri in enumerate(uri_list):
                    if uri.startswith(\
                            "<http://id.loc.gov/authorities/childrensSubjects/"):
                        index = i
                        print(uri)
                        break
            if not index:
                index = 0
            return (uri_list.pop(index), uri_list)


        with open(os.path.join(CFG.LOCAL_DATA_PATH, self.local_filename),
                  "w") as file_obj:
            file_obj.write(NSM.prefix("turtle"))
            for item in self.uri_list:
                uris = item['uris']['value'].split(",")
                new_list = find_preferred_uri(uris)
                uris = uris[1:]
                for uir in new_list[1]:
                    file_obj.write("%s kds:mergeWith %s .\n" % (uir,
                                                                new_list[0]))

    def send_to_tstore(self):
        result = self.conn.load_local_file(self.local_filename,
                                             self.namespace)
        return result

    def delete_local_file(self):
        os.remove(os.path.join(CFG.LOCAL_DATA_PATH, self.local_filename))

    def merge_instances(self):
        lg = logging.getLogger("%s.%s" % (self.ln, inspect.stack()[0][3]))
        lg.setLevel(self.log_level)

        lg.info("Updating old object references")
        self.conn.query(UPDATE_OLD_OBJ_REF,
                         namespace=self.namespace,
                         mode='update')

        lg.info("Deleting old objects")
        self.conn.query(DELETE_OLD,
                         namespace=self.namespace,
                         mode='update')

        lg.info("FINISHED")
