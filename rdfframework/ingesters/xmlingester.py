"""
Base injester classes and functions for injesting raw data into an
rdfframework based application
"""
import pdb
import datetime
import click

try:
    from lxml import etree
except ImportError:
    log.warning("'lxml' package not available. Using ptyhon 'xml'")
    import xml.etree.ElementTree as etree

from rdfframework.datatypes import Uri, RdfNsManager

RdfNsManager({'bf': 'http://id.loc.gov/ontologies/bibframe/'})

_RES_TAG = Uri("rdf:resource").etree
_RDF_TYPE_TAG = Uri("rdf:type").etree

class Extractor(object):
    """
    Extracts all nodes specified nodes from an xml file

    Args:
    -----
        source: the filepath to the xml file
        output: the filepath to output the results
    """

    def __init__(self, source, output=None, **kwargs):
        self.source = source
        self.output = output
        self.filter_tag = Uri("rdf:type")
        self.filter_val = Uri("bf:Topic")
        self.rdf_type = Uri("rdf:type")

    def run(self, tag=None, output=None, **kwargs):
        """
        runs the extractor

        Args:
        -----
            output: ['filepath', None]

        """
        start = datetime.datetime.now()
        count = 0
        if tag:
            tag = Uri(tag)
            xml_generator = etree.iterparse(self.source,
                                            #events=("start", "end"),
                                            tag=tag.etree)
        else:
            xml_generator = etree.iterparse(self.source) #,
                                            #events=("start", "end"))
        i = 0
        for event, element in xml_generator:
            type_tags = element.findall(_RDF_TYPE_TAG)
            rdf_types = [el.get(_RES_TAG)
                         for el in type_tags
                         if el.get(_RES_TAG)]
            # print(rdf_types)
            if str(self.filter_val) in rdf_types:
                pdb.set_trace()
                # print("%s - %s - %s - %s" % (event,
                #                              element.tag,
                #                              element.attrib,
                #                              element.text))
                count += 1
            # if i == 100:
            #     break
            i += 1
            element.clear()
        print("Found '{}' items in {}".format(count,
                (datetime.datetime.now() - start)))

class Updater(object):
    """
    Updates specified nodes in the xml file
    """
    pass


class BlankConverter(object):
    """
    Changes blanknodes to URIs
    """
    pass

@click.command()
@click.argument('source')
@click.argument('output')
@click.option('--tag', default=None, help="xml element name")
def run_extractor(*args, **kwargs):
    """
    Initializes and runs an extractor
    """
    # pdb.set_trace()
    extractor = Extractor(*args, **kwargs)
    result = extractor.run(**kwargs)

@click.group()
def cli():
    pass

cli.add_command(run_extractor)

if __name__ == '__main__':
    cli()
