"""
Name:        badges
Purpose:     Islandora Badges Application

Author:      Jeremy Nelson
Created:     16/09/2014
Copyright:   (c) Jeremy Nelson, Colorado College, Islandora Foundation 2014-
Licence:     GPLv3
"""
__author__ = "Jeremy Nelson"
__license__ = "GPLv3"
__version_info__ = ('0', '5', '0')
__version__ = '.'.join(__version_info__)

import argparse
import configparser
import datetime
import dateutil.parser
import falcon
import hashlib
import json
import mimetypes
import os
import rdflib
import re
import requests
import time

from jinja2 import Environment, FileSystemLoader
from graph import *
from forms import NewBadgeClass
from wsgiref import simple_server

PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
CURRENT_DIR = os.path.dirname(PROJECT_ROOT)

ENV = Environment(loader=FileSystemLoader(os.path.join(PROJECT_ROOT, "templates")))

CONFIG = configparser.ConfigParser()
CONFIG.read(os.path.abspath(os.path.join(PROJECT_ROOT, "application.cfg")))
TRIPLESTORE_URL = CONFIG.get('BADGE', 'triplestore')

def bake_badge_dev(badge_uri):
    with open("E:\\2015\\open-badge-atla2015.png", "rb") as img:
        return img.read()

def bake_badge(badge_uri):
    assert_url = 'http://backpack.openbadges.org/baker?assertion={0}'.format(
        badge_uri)
    result = requests.post(assert_url)
    raw_image = result.content
    return raw_image

def add_get_issuer(ISSUER_URI, config=CONFIG):
    if ISSUER_URI:
        return ISSUER_URI
    issuer_url = CONFIG.get('BADGE', 'issuer_url')
    issuer_check_result = requests.post(
        TRIPLESTORE_URL,
        data={"query": CHECK_ISSUER_SPARQL.format(issuer_url),
              "format": "json"})
    if issuer_check_result.status_code < 400:
        info = issuer_check_result.json().get('results').get('bindings')
        if len(info) < 1:
            issuer_graph = default_graph()
            new_issuer_result =  requests.post("http://{}:{}/fedora/rest".format(
                config.get("DEFAULT", "host"),
                config.get("TOMCAT", "port")))
            issuer_graph.parse(new_issuer_result.text)
            issuer_temp_uri = rdflib.URIRef(new_issuer_result.text)
            issuer_graph.add((issuer_temp_uri,
                              RDF.type,
                              SCHEMA.Organization))
            issuer_graph.add((issuer_temp_uri,
                              RDF.type,
                              OBI.Issuer))
            issuer_graph.add((issuer_temp_uri,
                              OBI.url,
                              rdflib.URIRef(issuer_url)))
            issuer_graph.add((issuer_temp_uri,
                              OBI.name,
                              rdflib.Literal(CONFIG.get('BADGE', 'issuer_name'))))
            issuer_update_result = requests.put(str(issuer_temp_uri),
                data=issuer_graph.serialize(format='turtle'),
                headers={"Content-type": "text/turtle"})
            ISSUER_URI = rdflib.URIRef(str(issuer_temp_uri))
        else:
            ISSUER_URI = rdflib.URIRef(info[0].get('entity').get('value'))
    return ISSUER_URI

ISSUER_URI = add_get_issuer(ISSUER_URI=None)

def add_get_participant(**kwargs):
    email = kwargs.get('email')
    if email is None:
        raise ValueError("Email cannot be none")
    identity_hash = hashlib.sha256(email.encode())
    identity_hash.update(CONFIG.get('BADGE', 'identity_salt').encode())
    email_result = requests.post(
        TRIPLESTORE_URL,
        data={"query": CHECK_PERSON_SPARQL.format(email),
              "format": "json"})
    if email_result.status_code < 400:
        info = email_result.json().get('results').get('bindings')
        if len(info) > 1:
            return info[0].get('entity').get('value')
        new_person = default_graph()
        new_person_uri = generate_tmp_uri('Person')
        new_person.add((new_person_uri,
                        RDF.type,
                        SCHEMA.Person))
        new_person.add((new_person_uri,
                        SCHEMA.email,
                        rdflib.Literal(email)))
       
        for prop in ['givenName', 'familyName', 'url']:
            if prop in kwargs:
                new_person.add((new_person,
                               getattr(SCHEMA, prop),
                               rdflib.Literal(kargs.get(prop))))
        add_person = Resource(config=config)
        person_url = add_person.__create__(rdf=new_person)
        return str(person_url)

    

review_msg = """Please review the following for the Badge Class:
---------------
Name: {}
Description: {}
Started on: {}
Ended on: {}
Keywords: {}
Critera: {}
Badge location: {}
---------------"""

def create_badge_class():
    "Function creates an badge class through a command prompt"
    while 1:
        badge_name = input("Enter badge class name >>")
        check_badge_result = requests.post(
            TRIPLESTORE_URL,
            data={"query": CLASS_EXISTS_SPARQL.format(slugify(badge_name)),
                  "format": "json"})
        if check_badge_result.status_code < 400:
            info = check_badge_result.json().get('results').get('bindings')
            if len(info) > 0:
                print("{} already exists as {}\nPlease try again".format(
                    badge_name,
                    slugify(badge_name)))
            else:
                break
        else:
            print("Error with SPARQL {}\n{}".format(check_badge_result.status_code,
                check_badge_result.text))
            break

    
    description = input("Description >>")
    started_on = input("Badge started on >>")
    ended_on = input("Event finished on (can leave blank) >>")
    keywords = []
    while 1:
        keyword = input("Enter keyword (q to quit) >>")
        if keyword.lower() == 'q':
            break
        keywords.append(keyword)
    criteria = []
    while 1:
        requirement = input("Enter critera (q to quit) >>")
        if requirement.lower() == 'q':
            break
        criteria.append(requirement)
    image_location = input("Enter file path or URL for badge class image >>")

    print(review_msg.format(
        badge_name,
        description,
        started_on,
        ended_on,
        ','.join(keywords),
        ','.join(criteria),
        image_location))
    prompt = input("Keep? (Y|N) >>")
    if prompt.lower() == 'y':
        if image_location.startswith("http"):
            badge_image = urllib.request.urlopen(image_location).read()
        else:
            badge_image = open(image_location, 'rb').read()
    else:
        retry = input("Try again? (Y|N)")
        if retry.lower() == 'y':
            create_badge_class()

        
def new_badge_class(**kwargs):
    image_raw = kwargs.get('image')
    badge_name = kwargs.get('name')
    badge_name_slug = slugify(badge_name)
    description = kwargs.get('description')
    started_on = kwargs.get('startDate')
    ended_on = kwargs.get('endDate')
    keywords = kwargs.get('tags')
    criteria = kwargs.get('criteria', [])
    badge_image = kwargs.get('image_file')
    new_badge_result = requests.post("http://{}:{}/fedora/rest".format(
        CONFIG.get("DEFAULT", "host"),
        CONFIG.get("TOMCAT", "port")),
        data=badge_image,
        headers={"Content-type": "image/png"})
    if new_badge_result.status_code > 399:
        raise ValueError("Error adding new badge {}\n{}".format(
	    new_badge_result.status_code,
	    new_badge_result.text))
    badge_class_uri = rdflib.URIRef("{}/fcr:metadata".format(new_badge_result.text))
    class_graph = default_graph()
    class_graph.parse(str(badge_class_uri))
    class_graph.add((badge_class_uri, RDF.type, OBI.BadgeClass))
    class_graph.add((badge_class_uri, RDF.type, SCHEMA.EducationalEvent))
    class_graph.add((badge_class_uri, 
        OBI.issuer,
        ISSUER_URI))
    class_graph.add((badge_class_uri, 
        OBI.name, 
        rdflib.Literal(badge_name)))
    class_graph.add((badge_class_uri, 
        SCHEMA.alternativeName, 
        rdflib.Literal(badge_name_slug)))  
    class_graph.add((badge_class_uri, 
        OBI.description, 
        rdflib.Literal(' '.join(description))))
    class_graph.add((badge_class_uri, 
        SCHEMA.startDate, 
        rdflib.Literal(started_on)))
    if ended_on is not None or len(ended_on) > 0:
        class_graph.add((badge_class_uri, 
            SCHEMA.endDate, 
        rdflib.Literal(ended_on)))
    for keyword in keywords:
        class_graph.add((badge_class_uri,
            OBI.tags,
	    rdflib.Literal(keyword)))
    for requirement in criteria:
        class_graph.add((badge_class_uri,
            OBI.criteria,
            rdflib.Literal(requirement)))
    update_class_result = requests.put(
        str(badge_class_uri),
        data=class_graph.serialize(format='turtle'),
        headers={"Content-type": "text/turtle"})
    if update_class_result.status_code > 399:
        raise ValueError("Could not update {} with RDF {}\n{} {}".format(
	    str(badge_class_uri),
	    class_graph.serialize(format='turtle').decode(),
	    update_class_result.status_code,
	    update_class_result.text))
    return str(badge_class_uri), badge_name_slug

def create_identity_object(email):
    person_uri = rdflib.URIRef(add_get_participant(email=email))
    identity_graph = default_graph()
    new_identity_object = Resource(config=config)
    identity_uri = generate_tmp_uri('IdentityType')
    identity_graph.add(
        (identity_uri,
         RDF.type,
         OB.IdentityType))
    
    identity_hash = hashlib.sha256(email.encode())
    salt = CONFIG.get('BADGE', 'identity_salt')
    identity_hash.update(salt.encode())
    identity_graph.add(
        (identity_uri,
         OB.salt,
         rdflib.Literal(salt)))
    identity_graph.add(
        (identity_uri, 
         OB.identity,
         rdflib.Literal("sha256${0}".format(identity_hash.hexdigest()))))
    identity_graph.add(
        (identity_uri,
         OB.hashed,
         rdflib.Literal("true",
                        datatype=XSD.boolean)))
    return str(new_identity_object.__create__(rdf=identity_graph))



def issue_badge(email, event):
    """Function issues a badge based on an event and an email, returns the
    assertation URI.

    Args:
        email(str): Email of participant
        event(str): Event

    Returns:
        assertation_uri(str)
    """
    if email is None or event is None:
        raise ValueError("email and event cannot be None")
    event_check_result = requests.post(
        TRIPLESTORE_URL,
        data={"query": FIND_CLASS_SPARQL.format(event),
              "format": "json"})
    if event_check_result.status_code < 400:
        info = event_check_result.json().get('results').get('bindings')
        if len(info) < 1:
            raise ValueError("{} event not found".format(event))
        else:
            event_uri = rdflib.URIRef(info[0].get('class').get('value'))
    badge_assertion_graph = default_graph()
    badge_uri = generate_tmp_uri('BadgeAssertion')
    badge_assertion_graph.add((badge_uri,
                               OB.BadgeClass,
                               event_uri))
    badge_assertion_graph.add((badge_uri,
                               OB.verify,
                               OB.hosted))
    badge_assertion_graph.add((badge_uri, 
                         RDF.type, 
                         OB.Badge))
    identity_uri = rdflib.URIRef(create_identity_object(email))
    badge_assertion_graph.add(
         (badge_uri, 
          OB.recipient,
          identity_uri))  
    badge_assertion_graph.add(
        (badge_uri,
         OB.verify,
         OB.hosted))
    badge_assertion_graph.add(
        (badge_uri,
         OB.issuedOn,
         rdflib.Literal(datetime.datetime.utcnow().isoformat(),
                        datatype=XSD.dateTime)))
    new_badge = Resource(config=config)
    badge_uri = new_badge.__create__(
        rdf=badge_assertion_graph)
    if badge_uri.endswith("fcr:metadata"):
        badge_uid = badge_uri.split("/")[-2]
    else:
        badge_uid = badge_uri.split("/")[-1]
    if not new_badge.__new_property__(
        "openbadge:uid", 
        '"{}"'.format(badge_uid),
        False):
            print("ERROR unable to save OpenBadge uid={}".format(badge_uid))
    ## Manually update triplestore
    ts_update = requests.post(
        TRIPLESTORE_URL,
        data={"update": UPDATE_UID_SPARQL.format(badge_uri, badge_uid),
              "format": "json"})
    if ts_update.status_code > 399:
        print("Error updating triplestore subject={} openbadge:uid to {}".format(
            badge_uri, badge_uid))
    badge_url = "{}/BadgeAssertion/{}".format(
        CONFIG.get('BADGE', 'badge_base_url'),
        badge_uid)
    new_badge = requests.post(badge_uri,
        data=bake_badge(badge_url),
        headers={"Content-type": 'image/png'})
    print("Issued badge {}".format(badge_url))
    return str(badge_url)


def slugify(value):
    """Converts to lowercase, removes non-word characters (alphanumerics and
    underscores) and converts spaces to hyphens. Also strips leading and
    trailing whitespace using Django format

    Args:

    """
    value = re.sub('[^\w\s-]', '', value).strip().lower()
    return re.sub('[-\s]+', '-', value)

class BadgeCollection(object):

    def on_get(self, req, resp):
        resp.status_code = falcon.HTTP_200       
 

class BadgeAssertion(object):

    def __get_identity_object__(self, uri):
        salt = None
        identity = None
        sparql = IDENT_OBJ_SPARQL.format(uri) 
        ident_result = requests.post(
            TRIPLESTORE_URL,
            data={"query": sparql,
                  "format": "json"}) 
        if ident_result.status_code > 399:
            raise falcon.HTTPInternalServerError(
                "Could not retrieve {} IdentityObject".format(uri),
                "Error:\n{}\nSPARQL={}".format(
                    ident_result.text,
                    sparql))
        bindings = ident_result.json().get('results').get('bindings')
        if len(bindings) < 1:
            return
        identity_hash = bindings[0].get('identHash').get('value') 
        salt = bindings[0].get('salt').get('value')
        return {
                 "type": "email",
                 "hashed": True,
                 "salt": salt,
                 "identity": identity_hash
        }

    def __valid_image_url__(self, uuid):
        sparql = FIND_IMAGE_SPARQL.format(uuid)
        result = requests.post(
            TRIPLESTORE_URL,
            data={"query": sparql,
                  "format": "json"})
        if result.status_code < 400:
            bindings = result.json().get('results').get('bindings')
            if len(bindings) > 0:
                image_url = bindings[0].get('image').get('value')
                badge_result = requests.get(image_url)
                if len(badge_result.content) > 1:
                    return url
        return None

    def on_get(self, req, resp, uuid, ext='json'):
        sparql = FIND_ASSERTION_SPARQL.format(uuid)
        #print(sparql)
        result = requests.post(TRIPLESTORE_URL,
            data={"query": sparql,
                  "format": 'json'})
        if result.status_code > 399:
            raise falcon.HTTPInternalServerError(
                "Cannot retrieve {}/{} badge".format(name, uuid),
                result.text)
        bindings = result.json().get('results').get('bindings')
##        try:
        issuedOn = dateutil.parser.parse(
            bindings[0]['DateTime']['value'])
        recipient = self.__get_identity_object__(
            bindings[0]['IdentityObject'].get('value'))

        name = bindings[0]['badgeClass'].get('value')
        badge_base_url = CONFIG.get('BADGE', 'badge_base_url')
        badge = {
        "@context": "https://w3id.org/openbadges/v1",
        "uid": uuid,
        "type": "Assertion",
        "recipient": recipient,
        "badge": "{}/BadgeClass/{}".format(
            badge_base_url, 
            name),
        #"issuedOn": int(time.mktime(issuedOn.timetuple())),
        "issuedOn": issuedOn.strftime("%Y-%m-%d"),
        "verify": {
            "type": "hosted",
            "url": "{}/BadgeClass/{}".format(
                        badge_base_url,
                        name)
            }
        }
        # Badge has been successfully baked and badge image 
        badge_image_url = self.__valid_image_url__(uuid)
        print("Badge img url {}".format(badge_image_url))
        if badge_image_url:
            badge["image"] = badge_image_url 
##        except:
##            print("Error {}".format(sys.exc_info()))
        resp.status = falcon.HTTP_200
        if ext.startswith('json'):
            resp.body = json.dumps(badge)
        else:
            resp.body = str(badge)

class BadgeClass(object):

    def __init__(self):
        pass

    def __keywords__(self, name, ext='json'):
        sparql = FIND_KEYWORDS_SPARQL.format(name)
        result = requests.post(
            TRIPLESTORE_URL,
            data={"query": sparql,
                  "format": "json"})
        info = result.json()['results']['bindings']
        output = [] 
        for result in info:
            output.append(result.get('keyword').get('value'))
        return list(set(output))

    def __html__(self, name=None):
        """Generates HTML view for web-browser"""
        if not name:
            badge_class_form = NewBadgeClass()
        badge_class_template = ENV.get_template("badge_class.html")
        return badge_class_template.render(
            name=name, 
            form=badge_class_form)

    def on_get(self, req, resp, name=None, ext='json'):
        if name and name.endswith(ext):
            name = name.split(".{}".format(ext))[0]
        resp.status = falcon.HTTP_200
        if not name:
            resp.content_type = "text/html"
            resp.body = self.__html__(name)
            return
        sparql = FIND_CLASS_SPARQL.format(name)
        result = requests.post(
            TRIPLESTORE_URL,
            data={"query": sparql,
                  "format": "json"})
        if result.status_code > 399:
            raise falcon.HTTPInternalServerError(
                   "Cannot retrieve {} Badge Class".format(name),
                   result.text)
        info = result.json()['results']['bindings'][0]
        keywords = self.__keywords__(name)
        badge_base_url = CONFIG.get('BADGE', 'badge_base_url')
        badge_class_json = {
            "@context": "https://w3id.org/openbadges/v1",
            "type": "BadgeClass",
            "name": info.get('name').get('value'),
            "description": info.get('description').get('value'),
            "criteria": '{}/BadgeCriteria/{}'.format(
                           badge_base_url,
                           name),
            "image": '{}/BadgeImage/{}.png'.format(
                          badge_base_url,
                          name),
            "issuer": "{}/IssuerOrganization".format(
                          badge_base_url),
             "tags": keywords
        }
        if ext.startswith('json'):
            resp.body = json.dumps(badge_class_json)

    def on_post(self, req, resp, name=None, ext='json'):
        new_badge_url, slug_name = new_badge_class(**req.params)
        print("Slug name is {}".format(slug_name))
        resp.status = falcon.HTTP_201
        resp.body = json.dumps({"message": "Success"})
        resp.location = '/BadgeClass/{}'.format(slug_name)



class BadgeClassCriteria(object):

    def on_get(self, req, resp, name):
        sparql = FIND_CRITERIA_SPARQL.format(name)
        badge_result = requests.post(
            TRIPLESTORE_URL,
            data={"query": sparql,
                  "format": "json"})
        if badge_result.status_code > 399:

            raise falcon.HTTPInternalServerError(
                "Cannot retrieve {}'s criteria".format(name),
                badge_result.text)
        bindings = badge_result.json().get('results').get('bindings')
        if len(bindings) < 1:
            raise falcon.HTTPNotFound()
        name ="Criteria for {} Open Badge".format(bindings[0]['name']['value']) 
        badge_criteria = {
            "name": name,
            "educationalUse": list(set([row.get('criteria').get('value') for row in bindings]))
        }
        resp.status = falcon.HTTP_200
        resp.body = json.dumps(badge_criteria) 
        

class BadgeImage(object):

    def __image_exists__(self, name, template):
        sparql = template.format(name)
        img_exists = requests.post(
            TRIPLESTORE_URL,
            data={"query": sparql,
                  "format": "json"})
        if img_exists.status_code > 399:
            raise falcon.HTTPInternalServerError(
                "Cannot retrieve {}'s image".format(name),
                img_exists.text)
        bindings = img_exists.json()['results']['bindings']
        if len(bindings) < 1:
            return False
        return bindings[0].get('image').get('value')

    def on_get(self, req, resp, name):
        resp.content_type = 'image/png'
        img_url = self.__image_exists__(name, FIND_IMAGE_SPARQL)
        if not img_url:
            img_url = self.__image_exists__(name, FIND_CLASS_IMAGE_SPARQL)
        if not img_url:
            raise falcon.HTTPNotFound()
        img_result = requests.get(img_url)
        resp.body = img_result.content

class DefaultView(object):

    def on_get(self, req, resp):
        resp.status = falcon.HTTP_200
        resp.body = "In default view"

class IssuerOrganization(object):

    def on_get(self, req, resp):
        resp.body = json.dumps({"name": CONFIG.get('BADGE', 'issuer_name'),
                                "url": CONFIG.get('BADGE', 'issuer_url')})

api = falcon.API()
        
#api.add_route("badge/{uuid}", Badge())
api.add_route("/", DefaultView())
api.add_route("/BadgeClass", BadgeClass())
api.add_route("/BadgeClass/{name}", BadgeClass())
api.add_route("/BadgeClass/{name}.{ext}", BadgeClass())
api.add_route("/BadgeCriteria/{name}", BadgeClassCriteria())
api.add_route("/BadgeImage/{name}.png", BadgeImage())
api.add_route("/BadgeAssertion/{uuid}", BadgeAssertion())
api.add_route("/IssuerOrganization", IssuerOrganization())

def main(args):
    """Function runs the development application based on arguments passed in
    from the command-line.

    Args:
        args(argpare.ArgumentParser.args): Argument list

    """
    if args.action.startswith('serve'):
        print("Starting REST API on port 7500")
        host = args.host or '0.0.0.0'
        port = args.port or 7500
        httpd = simple_server.make_server(host, port, api)
        httpd.serve_forever()
    elif args.action.startswith('issue'):
        email = args.email
        event = args.event
        issue_badge(email, event)
    elif args.action.startswith('new'):
        create_badge_class()
    elif args.action.startswith('revoke'):
        email = args.email
        event = args.event
        revoke_bade(email, event)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'action',
        choices=['serve', 'issue', 'revoke', 'new'],
        help='Action for badge, choices: serve, issue, new, revoke')
    parser.add_argument('--host', help='Host IP address for dev server')
    parser.add_argument('--port', help='Port number for dev server')
    parser.add_argument('--email', help='Email account to issue event badge')
    parser.add_argument('--event', help='Event to issue badge')
    args = parser.parse_args()
    main(args)