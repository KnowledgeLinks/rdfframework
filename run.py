import os
import sys
import logging
import inspect
import argparse

from flask import  Flask
from views import base_site

__version_info__ = ('0', '0', '1')
__version__ = '.'.join(__version_info__)
__author__ = "Mike Stabile, Jeremy Nelson"


app = Flask(__name__, instance_relative_config=True)
# get the module file name. This will allow the logger to print with the file
# name dynamically
mfname = inspect.stack()[0][1]

# register the main site views
app.register_blueprint(base_site, url_prefix='')
# set a serect key. this should be moved to a config file in production
app.secret_key = "DASFADFADSFAHGNBX#^%#%&WYUYREDH"

def main(args):
    ''' Launches application with passed in Args '''
    # turn on logging
    logging.basicConfig(level=logging.DEBUG) 
    # turn of loggers for other external packages 
    turn_off_lg = logging.getLogger("elasticsearch")
    turn_off_lg.setLevel(logging.INFO)
    turn_off_lg = logging.getLogger("urllib3")
    turn_off_lg.setLevel(logging.WARN)
    host = '0.0.0.0'
    port = 8081 # Debug
    ssl_context = 'adhoc'
    app.run(host=host,
            port=port,
            #threaded=True, 
            #ssl_context=ssl_context,
            use_reloader=True,
            debug=True)

if __name__ == '__main__':
    arg_parser = argparse.ArgumentParser()
    app_args = vars(arg_parser.parse_args())
    main(app_args)

