import os
import hashlib
import datetime
import re
from base64 import b64encode
from dateutil.parser import parse as parse_date
from passlib.hash import sha256_crypt
from rdfframework.utilities import is_not_null, make_set, make_list, pyuri,\
        slugify, clean_iri, iri, cbool, remove_null, pp, ttluri, get_attr
from rdfframework import get_framework
from flask.ext.login import login_required, login_user, current_user


__author__ = "Mike Stabile, Jeremy Nelson"
DEBUG = True
def run_form_processor(processor, obj, prop=None, mode="save"):
    '''runs the passed in processor and returns the saveData'''
    if isinstance(processor, dict):
        processor_type = processor.get('rdf_type')
    else:
        processor_type = processor
    processor_type = processor_type.replace(\
            "http://knowledgelinks.io/ns/data-resources/", "kdr_")

    if processor_type == "kdr_PasswordStatusChecker":
        return pw_status_processor(obj, mode)

def pw_status_processor(obj, mode):
    ''' This processor will check the status of the user's password
        credential's. If the kds:changePasswordRequired it set to true the
        application will redirect to the change password formMode'''

    if current_user.change_password is True:
        setattr(obj,'immediate_redirect', "login/reset")