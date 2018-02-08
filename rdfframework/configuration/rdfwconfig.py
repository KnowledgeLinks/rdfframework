''' Application Configuration Manager '''
import inspect
import os
import logging
import datetime
import pdb
import re
import types
import importlib.util
import copy
import pprint
import sys
import json
import shutil
import copy

from collections import OrderedDict
from rdfframework.utilities import (DictClass,
                                    initialized,
                                    get_attr,
                                    clean_iri,
                                    reg_patterns,
                                    format_multiline,
                                    colors,
                                    is_writeable_dir)
import pydoc

__author__ = "Mike Stabile, Jeremy Nelson"


class ConfigSingleton(type):
    """Singleton class for the RdfConfigManager that will allow for only one
    instance of the RdfConfigManager to be created.  """

    _instances = {}
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(ConfigSingleton,
                                        cls).__call__(*args, **kwargs)
        else:
            config = None
            if args:
                config = args[0]
            elif 'config' in kwargs:
                config = kwargs['config']
            if config:
                cls._instances[cls].__load_config__(config, **kwargs) # pylint: disable=W0212
        return cls._instances[cls]

    def clear(cls):
        cls._instances = {}


class RdfConfigManager(metaclass=ConfigSingleton):
    """
    Configuration Manager for the application.

    *** Of Note: this is a singleton class and only one instance of it will
                 exisit.

    args:
        config: the configuration module or dictionary of attributes

    kwargs:
        exit_on_error: True will kill the application if there is an error with
            the confirguation. False will prompt the user to correct any
            issues with the configuration.
        verify: Boolean. Whether to verify the configuation against the
            requirements. Default is True
        autosave: Boolean. True will automatically save any updates to the
            configuration file. False will prompt the user with save options
        requirements: a dictionary of attribute requirements to override the
            default attribute requirements. Requirements are updated with the
            these requirements. To remove a requirement completely use the
            'remove_reqs' kwarg.
        remove_reqs: list of requirment attribute names to remove

    """
    __err_file_name__ = "config_errs.txt"
    __type = 'DictClass'
    __reserved = ['dict',
                  'get',
                  'items',
                  'keys',
                  'values',
                  '_RdfConfigManager__reserved',
                  'is_intialized',
                  '_DictClass__type',
                  'debug',
                  'os']
    __cfg_reqs__ = OrderedDict([
        ("LOGGING", {"required": True,
                     "type": (bool, dict),
                     "description": "False: Turns logging off. - "
                                    "True[default]: Uses default logging "
                                    "setup. - "
                                    "Dictionay is passed into the python "
                                    "logging.config.dictConfig()",
                     "default": True}),
        ("TURN_ON_VOCAB", {"required": True,
                           "type": bool,
                           "description": "True: intelligent classes are "
                                          "created based off of the RDF "
                                          "vocabulary definitions and custom "
                                          "defintions. - False: only a basic "
                                          "RDF class is used. *Start time is "
                                          "increased with this on. It is "
                                          "required to be on for all "
                                          "advanced rdfframework functions.",
                           "default": False}),
        ("SECRET_KEY", {"required": True,
                        "description": """secret key to be used
                                       by the Flask application
                                       security setting""",
                        "type": str,
                        "length": {"min": 64, "max": 256}}),
        ("SITE_NAME", {"required": True,
                       "description": "the name used for the site",
                       "type": str}),
        ("BASE_URL", {"required": True,
                      "description": "base URL for the site",
                      "type": str,
                      "format": "url"}),
        ("CONNECTIONS", {"required": False,
                         "type": list,
                         "item_type": dict,
                         "item_dict": OrderedDict([
                            ("name", {
                                "type": str,
                                "required": True,
                                "description": """name for the connection.
                                                     typical names are:
                                                     datastore*, search,
                                                     active_defs, repo  * -
                                                     required"""}),
                            ("conn_type", {
                                "type": str,
                                "required": True,
                                "options": "rdfframework.connections.RdfwConnections.nested",
                                "description": "type of connection"}),
                            ("vendor", {
                                "type": str,
                                "required": True,
                                "options": "rdfframework.connections.RdfwConnections[{conn_type}]",
                                "description": """the producer of the connection
                                        for the specified connection type"""}),
                            ("url", {
                                "type": str,
                                "required": False,
                                "format": "url",
                                "description": """the url for the
                                         connection"""}),
                            ("local_url", {
                                "type": str,
                                "required": False,
                                "format": "url",
                                "description": """alternate/local url for the
                                         connection"""}),
                            ("container_dir", {
                                "type": str,
                                "format": "directory",
                                "required": False,
                                "description": """directory path as the docker
                                        container of the connetion sees a
                                        shared directory with the python
                                        application. This is paired with the
                                        'python_dir' value."""}),
                            ("python_dir", {
                                "type": str,
                                "format": "directory",
                                "required": False,
                                "description": """directory path as the python
                                        application sees a shared directory
                                        with the connection running in a
                                        docker container. This is paired with
                                        the 'container_dir' value."""}),
                            ("kwargs", {
                                "type": dict,
                                "doc": "rdfframework.connections.RdfwConnections[{conn_type}][{vendor}]",
                                "description": """additional kwargs as detailed
                                        in the below __doc__ string. Use python
                                        dictionary notation"""})
                         ]),
                         "action": "send to ConnManager",
                         "format": "create_instance",
                         "action": {"type": "replace",
                                    "object": "rdfframework.connections.ConnManager",
                                    "args": "self",
                                    "attr": "conns"},
                         # "optional_items": [{"name":'search'},
                         #                    {"name":'repository'},
                         #                    {"name":'active_defs'}]
                         "req_items": [{"name": "datastore",
                                        "description": "data triplestore" }]
            }),
        ("DIRECTORIES", {"required": True,
                         "type": list,
                         "item_type": dict,
                         "description": 'Directory paths and short names for'
                                        ' use. Each directory path is accesable'
                                        ' through the RdfConfigManager() by'
                                        ' selecting the following notation:\n\n'
                                        '\t RdfConfigManager.dirs.name\n\n'
                                        'Where the name is a short descriptive'
                                        ' word descibing the directories use.'
                                        ' There are 5 functional names used by'
                                        ' the rdfframework.\n'
                                        '\t1. base - a base directory for '
                                        'creating addtional directories '
                                        '*required\n\t2. logs',
                         "item_dict": OrderedDict([
                                ("name", {"type": str,
                                          "required": True,
                                          "description": ["""descriptive name of
                                                the directory, i.e. 'base'.""",
                                                """Additional subdirectories
                                                will be created if not
                                                otherwise specifed here.""",
                                                """*** the 'base' directory is
                                                required. ***""",
                                                """Subdirectrories created if
                                                not specified otherwise:""",
                                                "logs: base/logs",
                                                "data: base/data",
                                                "cache: base/cache",
                                                """vocabularies:
                                                base/vocabularies"""]}),
                                ("path", {"type": str,
                                          "required": True,
                                          "description": "directory path",
                                          "format": "directory"})]),
                         "format": "directory",
                         "action": {"type": "add_attr",
                                    "key": "name",
                                    "value": "path",
                                    "attr": "dirs",
                                    "auto_create": {"logs": ("base", "logs"),
                                                    "data": ("base", "data"),
                                                    "cache": ("base", "cache"),
                                                    "vocabularies":
                                                    ("base", "vocabularies")}},
                         "req_items": [{"name": "base",
                                        "description": """the base directory for
                                                saving application data"""}]}),
        ("NAMESPACES", {"required": False,
                        "type": dict,
                        "item_type": str,
                        "action": {"type": "replace",
                                   "object": "rdfframework.datatypes.RdfNsManager",
                                   "args": "self"},
                        "format": "namespace",
                        "description": "URI for an RDF namespace"})
    ])



    def __init__(self, config=None, **kwargs):
        self.__config__ = {}
        self.__config_file__ = None
        self.__config_dir__ = None
        self.__err_file__ = None
        self.__locked__ = False
        self.__is_initialized__ = False
        if config:
            self.__load_config__(config, **kwargs)

    def __load_config__(self, config, **kwargs):
        """ Reads a python config file and initializes the cloass

            args:
                obj: the config data
        """
        # The configuration cannot be initialised more than once
        if self.__is_initialized__:
            raise ImportError("RdfConfigManager has already been initialized")
        self.__set_cfg_reqs__(**kwargs)
        self.__set_cfg_attrs__(config, **kwargs)
        if kwargs.get("verify") != False:
            errors = self.__verify_config__(self.__config__, **kwargs)
            self.__reslove_errors__(errors, **kwargs)

        self.__is_initialized__ = True
        self.__initialize_directories__(**kwargs)
        self.__initialize_conns__(**kwargs)
        self.__load_namespaces__(**kwargs)
        self.__run_defs__(**kwargs)

    def __load_namespaces__(self, **kwargs):
        if not self.namespaces:
            return
        ns_mgr = get_obj_frm_str("rdfframework.datatypes.RdfNsManager")
        self.__config__['nsm'] = ns_mgr(self.namespaces)

    def __run_defs__(self, **kwargs):
        """
        Generates all of the classes based on the loaded RDF vocabularies and
        custom definitions
        """
        if self.__config__.get("TURN_ON_VOCAB") or kwargs.get("turn_on_vocab"):
            from rdfframework.rdfclass import (RdfPropertyFactory,
                                               RdfClassFactory)
            conn = self.__config__.get('conns',{}).get('active_defs')
            if conn:
                RdfPropertyFactory(conn, reset=kwargs.get("reset"))
                RdfClassFactory(conn, reset=kwargs.get("reset"))
            else:
                log.warning("No definition connection found. rdfframework "
                            "initialized with out definitions")
        else:
            source = []
            if self.__config__.get("TURN_ON_VOCAB") == False:
                source.append("config file")
            if kwargs.get("turn_on_vocab") == False:
                source.append("keywords")
            log.warning("rdfframework initialized without rdf "
                        "definitions because of 'TURN_ON_VOCAB' in %s",
                        source)
    def __verify_config__(self, config, **kwargs):
        """ reads through the config object and validates missing arguments

        args:
            config: the config object

        """
        log.info("Verifiying config settings")
        error_dict = OrderedDict()
        for attr, req in self.__cfg_reqs__.items():
            result = test_attr(get_attr(config, attr), req)
            if result:
                error_dict[attr] = result
        return error_dict

    def __reslove_errors__(self, errors={}, **kwargs):
        """ Determines how to deal with and config issues and resolves them

        args:
            errors: list of config errors
        """
        def get_missing(self, attr):
            req = self.__cfg_reqs__[attr]
            if req['type'] == str:
                while True:
                    print("{}: {}".format(colors.fail('Enter ' + attr),
                            colors.cyan(req['description'])))
                    value = input('-> ')
                    if value.strip() != '':
                        return value
            elif req['type'] == list:
                return []
        def fix_str(self, attr, key, value):
            req = self.__cfg_reqs__[attr]
            while True:
                new_val = input("{err} {key} | value: {val} | *** {msg}\n\t{desc}\n - Enter corrected value [{val}]: ".format(
                        err=colors.fail("ERROR"),
                        key=colors.warning(key),
                        val=colors.fail(value['value']),
                        msg=colors.yellow(value['msg']),
                        desc=colors.green(req['description'])))
                errors = test_attr({key: new_val}, req)
                if not errors:
                    return new_val
                value = errors['items'][key]

        def fix_item(self, req, obj):
            for key, val in req.items():
                while True:
                    errors = test_attr([strip_errors(obj)], {"type": list,
                                                             "item_type": dict,
                                                             "item_dict": req})
                    for ky in errors.get('items',
                                         [{}])[0].get('__error_keys__', []):
                        obj[ky] = errors['items'][0][ky]
                    if errors:
                        obj['__error_keys__'] = \
                                errors['items'][0]['__error_keys__']
                    else:
                        idx = obj.get('__list_idx__')
                        obj = strip_errors(obj)
                        obj.update({'__list_idx__': idx, '__error_keys__': []})
                    desc = format_multiline(val.get("description", ""))
                    desc_items = ["%s: %s" % (i_key,
                                              colors.cyan(format_multiline(i_val)))
                                  for i_key, i_val in sorted(val.items())
                                  if i_key.lower() not in ["doc", "options"]]
                    if val.get("doc"):
                        doc = get_obj_frm_str(val['doc'], **obj)
                        if doc:
                            desc_items.append("__doc__: %s" % doc.__doc__)
                    if val.get("options"):
                        options = get_options_from_str(val['options'], **obj)
                        desc_items.append("options: %s" % colors.warning(options))
                    desc = "\n\t".join(desc_items)
                    if isinstance(obj.get(key), dict) and \
                            (obj[key].get('msg') or obj[key].get('reason')):
                        new_val = input(
                                "{err} {key} | value: {val} | *** {msg}\n\t{desc}\n - Enter corrected value [{val}]: ".format(
                                        err=colors.fail("ERROR"),
                                        key=colors.warning(key),
                                        val=colors.fail(obj[key]['value']),
                                        msg=colors.yellow(obj[key].get('msg') \
                                                or obj[key].get('reason')),
                                        desc=colors.green(desc)))
                        new_val = new_val or obj[key]['value']
                    else:
                        new_val = input("{ok} {key} | value: {val}\n\t{desc}\n - Enter to keep current value [{val}]: ".format(
                                        ok=colors.green("OK"),
                                        key=colors.lcyan(key),
                                        val=colors.green(obj.get(key)),
                                        desc=desc))
                        new_val = new_val or obj.get(key)
                    errors = test_attr(new_val, val, obj)
                    if not errors:
                        obj[key] = new_val
                        try:
                            obj['__error_keys__'].remove(key)
                        except ValueError:
                            pass
                        break
                    else:
                        errors["value"] = new_val
                        obj[key] = errors

            return {key: value for key, value in obj.items()
                    if not key.startswith("__")}

        def cycle_errors(self, errors, cfg_obj):
            for attr, err in errors.items():
                if err.get("set"):
                    cfg_obj[attr] = err['set']
                elif err['reason'] == "missing":
                    cfg_obj[attr] = get_missing(self, attr)
                elif err['reason'] == "list_error":
                    req = self.__cfg_reqs__[attr]['item_dict']
                    print("Correcting list items for configuration item: \n\n",
                          "***",
                          attr,
                          "****\n")
                    for item in err['items']:
                        new_item = fix_item(self, req, item)
                        if item['__list_idx__'] == None:
                            try:
                                cfg_obj[attr].append(new_item)
                            except KeyError:
                                cfg_obj[attr] = [new_item]
                        else:
                            cfg_obj[attr][item['__list_idx__']] = new_item
                elif err['reason'] == "dict_error":
                    if self.__cfg_reqs__[attr]['item_type'] == dict:
                        req = self.__cfg_reqs__[attr]['item_dict']
                    elif self.__cfg_reqs__[attr]['item_type'] == str:
                        req = self.__cfg_reqs__[attr]
                        print("Correcting dictionay for item:\n\n",
                              colors.warning("**** %s ****\n" % attr))
                        for item, val in err['items'].items():
                            new_val = fix_str(self, attr, item, val)
                            cfg_obj[attr][item] = new_val

        if not errors:
            return


        colors.turn_off
        nocolor_err_msg = self.__format_err_summary__(errors)
        colors.turn_on
        err_msg = self.__format_err_summary__(errors)
        msg_kwargs = dict(time=datetime.datetime.now(),
                          err_msg=err_msg,
                          cfg_path=self.__config_file__,
                          err_path=self.__err_file__)
        print(format_multiline(__MSGS__["initial"], **msg_kwargs))
        while True:
            if kwargs.get("exit_on_error") == True:
                resolve_choice = "2"
            else:
                resolve_choice = input(format_multiline(\
                                        __MSGS__["resolve_options"]))
            if resolve_choice.strip() == "2":
                err_text = format_multiline(__MSGS__["exit"], **msg_kwargs)
                if self.__err_file__:
                    with open(self.__err_file__, "w") as fo:
                        colors.turn_off
                        msg_kwargs['err_msg'] = nocolor_err_msg
                        fo.write(format_multiline(__MSGS__["exit"],
                                                  **msg_kwargs))
                        colors.turn_on
                        msg_kwargs['err_msg'] = err_msg
                sys.exit(err_text)
            elif resolve_choice.strip() in ["", "1"]:
                break
        while True:
            cycle_errors(self, errors, self.__config__)
            errors = self.__verify_config__(self.__config__, **kwargs)
            if not errors:
                break
        self.__save_config__(**kwargs)
        print(self.__format_err_summary__(errors))

    def __save_config__(self, **kwargs):
        """
        Provides the user the option to save the current configuration

        kwargs:
            autosave: True automatically saves the config file
                      False prompts user
        """
        option = "1"
        new_path = self.__config_file__
        config_dir = os.path.split(self.__config_file__)[0]
        filename = os.path.split(self.__config_file__)[1]
        if not kwargs.get("autosave"):
            while True:
                option = input(format_multiline(__MSGS__['save'])).strip()
                if option in ["1", "2", "3"]:
                    break
        if option == "3":
            return
        if option == "1" and not self.__config_file__:
            option = "2"
        if option == "2":
            while True:
                new_path = input("Enter a file path to save the new "
                                 "configuation -> ")
                try:
                    path = os.path.split(new_path)
                    if not path[0]:
                        path = (config_dir, path[1])
                    if not os.path.isdir(path[0]):
                        print(" ** directory does not exist")
                        raise OSError
                    elif not is_writeable_dir(path[0]):
                        print(" ** directory is not writable")
                        raise OSError
                    new_path = os.path.join(*path)
                    break
                except OSError:
                    pass

        elif option == "1":
            shutil.copy(self.__config_file__, self.__config_file__ + ".bak")

        with open(new_path, "w") as fo:
            fo.write(self.__format_save_config__(self.__config__,
                                                 self.__cfg_reqs__,
                                                 **kwargs))


    def __set_cfg_attrs__(self, config, **kwargs):

        def read_module_attrs(module, ignore=[]):
            """ Returns the attributes of a module in an dict

            args:
                module: the module to read
                ignore: list of attr names to ignore
            """
            rtn_obj = {attr: getattr(module, attr)
                       for attr in dir(module)
                       if attr not in ignore
                       and not attr.startswith("_")
                       and not isinstance(getattr(module, attr),
                                          types.ModuleType)}
            return rtn_obj

        # if the config is a module determine the module path
        if isinstance(config, types.ModuleType):
            self.__config_file__ = config.__file__
            self.__config_dir__ = os.path.split(self.__config_file__)[0]
            self.__err_file__ = os.path.join(self.__config_dir__,
                                             self.__err_file_name__)
            new_config = read_module_attrs(config, self.__reserved)
        else:
            new_config = copy.deepcopy(config)
        self.__config__ = OrderedDict()
        for attr, req in self.__cfg_reqs__.items():
            if new_config.get(attr):
                self.__config__[attr] = new_config.pop(attr)
            elif "default" in req:
                self.__config__[attr] = req["default"]
        self.__config__.update(new_config)

    def __set_cfg_reqs__(self, requirements=None, **kwargs):
        """ Applies any new requirements

        args:
            requirements: dictionary of attribute requirements

        kwargs:
            remove_reqs: list of requirement names to remove
        """
        if requirements:
            self.__cfg_reqs__.update(requirements)
        for attr in kwargs.get('remove_reqs', []):
            try:
                del self.__cfg_reqs__[attr]
            except KeyError:
                pass

    def __initialize_conns__(self, **kwargs):
        """
        Reads the loaded config and creates the defined database
        connections
        """
        if not self.__config__.get("CONNECTIONS"):
            return
        conn_mgr = get_obj_frm_str("rdfframework.connections.ConnManager")
        self.__config__['conns'] = conn_mgr(self.__config__['CONNECTIONS'])
        # RdfPropertyFactory(CFG.def_tstore, reset=reset)
        # RdfClassFactory(CFG.def_tstore, reset=reset)

    def __initialize_directories__(self, **kwargs):
        """
        reads through the config and verifies if all directories exist and
        creates them if they do not
        """
        if not self.__config__.get("DIRECTORIES"):
            return
        dir_config = self.__config__.get('DIRECTORIES', [])
        dirs = {item['name']: item['path'] for item in dir_config}
        req = self.__cfg_reqs__['DIRECTORIES']
        auto = req.get("action", {}).get("auto_create", {})
        for name, args in auto.items():
            if name not in dirs:
                dirs[name] = os.path.join(dirs.get(args[0], args[0]), args[1])
        paths = sorted(dirs.values())
        for path in paths:
            if not os.path.exists(path):
                log.warning("Creating Directory [%s]", path)
                os.makedirs(path)
        self.__config__['dirs'] = DictClass(dirs)

    def __repr__(self):
        if self.__is_initialized__:
            return "<%s.%s object at %s> (\n%s)" % (self.__class__.__module__,
                                                    self.__class__.__name__,
                                                    hex(id(self)),
                                                    list(self.__config__))
        else:
            return "<RdfConfigManager has not been initialized>"

    @initialized
    def __getattr__(self, attr):
        for key, value in self.__config__.items():
            if attr.lower() == key.lower():
                return value
        return None

    @initialized
    def __getitem__(self, item):
        if self.__config__.get(item):
            return self.__config__.get(item)
        return None
        # if hasattr(self, item):
        #     return getattr(self, item)
        # return None

    @initialized
    def __str__(self):
        try:
            return str(self.dict())
        except TypeError:
            return ""

    def __setattr__(self, attr, value, override=False):
        if attr.startswith("__"):
            self.__dict__[attr] = value
        elif self.__is_initialized__ and self.locked:
            raise RuntimeError("The configuration may not be changed after" + \
                               " locking")
        elif str(attr) in self.__reserved:
            raise AttributeError("'%s' is a reserved word in this class." % \
                                 attr)
        elif not self.__is_initialized__ and isinstance(value, (list, dict)):
            value = DictClass(value)
        else:
            self.__config__[attr] = value

    @initialized
    def dict(self):
        """ converts the class to a dictionary object """
        return DictClass(self.__config__).dict()

    @initialized
    def get(self, attr, none_val=None):
        """ returns and attributes value or a supplied default

            args:
                attr: the attribute name
                none_val: the value to return in the attribute is not found or
                        is equal to 'None'.
        """
        return self.__config__.get(attr, none_val)
        # if attr in self.keys():
        #     return getattr(self, attr)
        # return none_val

    @initialized
    def keys(self):
        """ returns a list of the attributes in the config manager """
        # return [attr for attr in dir(self) if not attr.startswith("_") and \
        #         attr not in self.__reserved]
        return self.__config__.keys()

    @initialized
    def values(self):
        """ returns the values of the config manager """
        # return [getattr(self, attr) for attr in dir(self) \
        #         if not attr.startswith("_") and attr not in self.__reserved]
        return self.__config__.values()

    @initialized
    def items(self):
        """ returns a list of tuples with the in a key: value combo of the
        config manager """
        # return_list = []
        # for attr in dir(self):
        #     if not attr.startswith("_") and attr not in self.__reserved:
        #         return_list.append((attr, getattr(self, attr)))
        # return return_list
        return self.__config__.items()

    def __format_err_summary__(self, errors, indent=0, initial=True):
        """
        Formats the error dictionary for printing

        args:
            errors: the error dictionary
            indent: the indent level in number of spaces
        """
        ind_interval = 5
        parts = []
        ind = ''.ljust(indent, ' ')
        curr_err = copy.deepcopy(errors)
        msg_str = "{indent}{attr}: {val}{msg}"
        good_dict = {}
        if errors.get("__error_keys__"):
            line = colors.hd(''.ljust(50, '-'))
            parts.append(colors.hd("{}index number: {}".format(ind,
                    errors.get("__list_idx__"))))
            parts.append("{}{}".format(ind, line))
            curr_err = {key: curr_err[key] for key in errors['__error_keys__']}
            indent += ind_interval
            ind = ''.ljust(indent, ' ')
            good_dict = {key: value for key, value in errors.items()
                         if key not in errors['__error_keys__']
                         and not key.startswith("__")}
        for attr, value in curr_err.items():
            msg = ''
            val = ''
            if not value.get('items'):
                val = "[{}] error: ".format(
                        colors.lcyan(value.get("value", "None")))
                msg = colors.warning(value.get("msg", value.get("reason")))

            parts.append(msg_str.format(indent=ind,
                                        attr=colors.fail(attr),
                                        val=val,
                                        msg=msg))
            if value.get('items'):
                if isinstance(value['items'], list):
                    for item in value['items']:
                        parts += self.__format_err_summary__(item,
                                indent + ind_interval,
                                False)
                elif isinstance(value['items'], dict):
                    sub_ind = ''.ljust(indent + ind_interval, ' ')
                    for key, value in value['items'].items():
                        val = "[{}] error: ".format(
                                colors.lcyan(value.get("value", "None")))
                        msg = colors.warning(value.get("msg",
                                                       value.get("reason")))
                        parts.append(msg_str.format(indent=sub_ind,
                                                    val=val,
                                                    attr=colors.fail(key),
                                                    msg=msg))
        for attr, value in good_dict.items():
            parts.append(msg_str.format(indent=ind,
                                        val=colors.blue(value),
                                        msg="",
                                        attr=colors.blue(attr)))
        if initial:
            return "\n".join(parts)
        else:
            return parts


    def __format_save_config__(self, obj, attr_reqs, initial=True, **kwargs):
        """
        Formats the current configuration for saving to file

        args:
            obj: the config object
            initial: bool argument for recursive call catching

        kwargs:
            indent: the indent level in number of spaces
        """

        ind_interval = 5
        ind = ''.ljust(kwargs.get('indent', 0), ' ')
        ind2 = ind + ''.ljust(ind_interval, ' ')

        parts = []
        curr_obj = copy.deepcopy(obj)
        # comment_kwargs = copy.deepcopy(kwargs)
        # comment_kwargs['prepend'] = "# "
        attr_str = "{cmt}{attr} = {value}"
        good_dict = {}
        pp_kwargs = {key: value for key, value in kwargs.items()
                     if key in ['indent', 'depth']}
        for attr, req in attr_reqs.items():
            if req.get("description"):
                parts.append(format_multiline(req['description'],
                                              prepend="## ",
                                              max_width=78,
                                              **pp_kwargs))
            value = obj.get(attr, req.get('standard', req.get('default')))
            if attr in obj:
                parts.append(attr_str.format(attr=attr,
                                             value=pprint.pformat(value,
                                                                  **pp_kwargs),
                                             cmt=''))
            else:
                parts.append(attr_str.format(attr=attr,
                                             value=str(value),
                                             cmt='# '))
        parts.append("\n#! *** non specified attributes ***\n")
        for attr, value in obj.items():
            if attr not in attr_reqs:
                parts.append(attr_str.format(attr=attr,
                                             value=pprint.pformat(value,
                                                                  **pp_kwargs),
                                             cmt=''))
        return "\n\n".join(parts)




__MSGS__ = {
    "initial": [colors.warning("***** CONFIGURATION ERRORS *****"),
                colors.hd("""Below are a list of errors found in the current
                          configuration:"""),
                '{err_msg}'],
    "resolve_options": ['',
                        "Select from the below options:",
                        "1 - resolve through series of questions",
                        "2 - exit and manually correct the configuration file",
                        "    * These errors will be written to 'config_errors.txt'",
                        "      in the same directory as the configuration file",
                        """ *** if option 1 you will have a chance to save the
                            the results of process into a new configuration
                            file""",
                        "Enter option ([1]/2):"],
    "exit": ["***** CONFIGURATION ERRORS *****",
             'Generated at: {time}',
             '{err_msg}',
             '',
             '',
             "***** CONFIG FILE PATH *****",
             '{cfg_path}',
             "***** ERROR MESSAGE FILE PATH *****",
             '{err_path}'],
    "save": [colors.warning("Select the save option for the new config!"),
             colors.green("1 - Save over current file"),
             colors.warning("2 - enter new save file path"),
             colors.fail("3 - do not save changes. Changes lost on exit. "),
             '',
             colors.warning("Enter option number(1/2/3) -> ")]
}



def test_attr(attr, req, parent_attr=None):
    """ tests the validity of the attribute supplied in the config

    args:
        attr: the name of tha attribute
        reg: the requirement definition
        config: the config obj
    """

    def test_format(attr_val, fmat):
        """ test an attribute value to see if it matches the required
        format

        args:
            attr_val: the attribute value to test
            fmat: the required format
        """
        rtn_obj = {"reason": "format"}
        if fmat == 'url':
            if not reg_patterns.url.match(attr_val):
                if reg_patterns.url_no_http.match(attr_val):
                    return "missing http or https"
                return "invalid url format"
        if fmat == "namespace":
            uri = clean_iri(attr_val)
            if not reg_patterns.url.match(uri):
                return "invalid uri format"
            elif uri.strip()[-1] not in ["/", "#"]:
                return "does not end with / or #"
        if fmat == "directory":
            env = 'win'
            if os.path.sep == '/':
                env = 'linux'
            if env == 'linux':
                if not reg_patterns.dir_linux.match(attr_val):
                    if not reg_patterns.dir_win.match(attr_val):
                        return "invalid directory path"
                    log.warning("linux/mac env: windows directory path %s",
                                attr_val)
            if env == 'win':
                if not reg_patterns.dir_win.match(attr_val):
                    if not reg_patterns.dir_linux.match(attr_val):
                        return "invalid directory path"
                    log.warning("windows env: linux/mac directory path %s",
                                attr_val)
        return None

    rtn_obj = {}
    if req.get("required") and attr is None:
        if "default" in req:
            rtn_obj["set"] = req['default']
            rtn_obj["reason"] = "using default"
        else:
            rtn_obj["reason"] = "missing"
        return rtn_obj
    if attr is None:
        return {}
    if not isinstance(attr, req['type']):
        rtn_obj.update({"reason": "type",
                        "msg": "should be of type %s" % req['type']})
        return rtn_obj

    if req['type'] == list:
        error_list = []
        if req['item_type'] == str and req.get("format"):
            fmat = req['format']
            for item in attr:
                msg = test_format(item, fmat)
                if msg:
                    error_list.append(msg)
        elif req['item_type'] == dict:
            for idx, item in enumerate(attr):
                item_errors = []
                dict_errors = {}
                for key, item_req in req['item_dict'].items():
                    msg = test_attr(item.get(key), item_req, item)
                    if msg:
                        msg['value'] = item.get(key)
                        dict_errors[key] = msg
                if dict_errors:

                    item_copy = copy.deepcopy(item)
                    item_copy.update(dict_errors)
                    item_copy['__list_idx__'] = idx
                    item_copy['__error_keys__'] = list(dict_errors)
                    error_list.append(item_copy)
            # if item_errors:
            #     error_list.append(item_errors)

        req_key = None
        req_values = []
        if req.get("req_items"):
             #determine the matching key
            req_key = [key for key in req['req_items'][0].keys()
                       if key != "description"][0]
            for item in req['req_items']:

                value = item[req_key]
                req_values.append(value)
                if not value in [item[req_key] for item in attr]:
                    error_item = {
                            "__list_idx__": None,
                            "__msg__": "'%s: %s' is a required item" % \
                                    (req_key, value),
                            "__error_keys__":
                                [ky for ky, val in
                                        req['item_dict'].items()
                                 if val.get("required")
                                 and ky != req_key]}
                    missing_dict = {"msg": "required",
                                    "reason": "missing",
                                    "value": None }
                    error_req = {ky: missing_dict
                                 for ky, val in req['item_dict'].items()
                                 if val.get("required")}
                    error_req[req_key] = value
                    error_item.update(error_req)
                    error_list.append(error_item)
        if req.get("optional_items"):
            if not req_key:
                req_key = [key for key in req['optional_items'][0].keys()
                           if key != "description"][0]
            optional_values = [item[req_key] for item in attr]
            optional_values = set(optional_values + req_values)
            cfg_values = set([item[req_key] for item in attr])
            not_allowed = cfg_values.difference(optional_values)
            if not_allowed:
                for name in not_allowed:
                    idx, item = [(i, val) for i, val in enumerate(attr)
                                 if val[req_key] == name][0]
                    error_item = {
                            "__list_idx__": idx,
                            "__msg__": "'%s:%s' is not an allowed item. "
                                       "Allowed items are: " % \
                                       (req_key, name, list(optional_values)),
                            "__error_keys__":
                                [ky for ky, val in
                                        req['item_dict'].items()
                                 if val.get("required")
                                 and ky != key]}
                    missing_dict = {"msg": "Not an allowed option",
                                    "reason": "not_allowed",
                                    "value": None }
                    error_req = {ky: missing_dict
                                 for ky, val in req['item_dict'].items()
                                 if val.get("required")}
                    error_req[key] = value
                    error_item.update(error_req)
                    error_list.append(error_item)

        if error_list:
            rtn_obj.update({"reason": "list_error",
                            "items": error_list})
            return rtn_obj
        return rtn_obj
    if req['type'] == dict:
        if req['item_type'] == str and req.get("format"):
            fmat = req['format']
            # error_list = []
            error_dict = {}
            for key, item in attr.items():
                msg = test_format(item, fmat)
                if msg:
                    error_dict[key] = {"value": item,
                                       "msg": msg}
                    # error_list.append({key: msg})
        elif req['item_type'] == dict:
            for item, value in attr.items():
                item_errors = []
                for key, item_req in req['item_dict'].items():
                    msg = test_attr(value.get(key), item_req, value)
                    if msg:
                        item_errors.append({value.get(key): msg})
            if item_errors:
                error_list.append({item: item_errors})

        if error_dict:
            rtn_obj.update({"reason": "dict_error",
                            "items": error_dict})
            return rtn_obj
        return
    if req.get("format"):
        fmat = req['format']
        rtn_obj["reason"] = "format"
        msg = test_format(attr, fmat)
        if msg:
            rtn_obj.update({"msg": msg})
            return rtn_obj
    if req.get("options"):
        options = get_options_from_str(req['options'],**parent_attr)
        msg = None
        if not attr in options:
            msg = "'%s' is not an allowed option, choose from %s" % (
                    attr,
                    options)
        if msg:
            rtn_obj.update({"msg": msg})
            return rtn_obj

def get_options_from_str(obj_str, **kwargs):
    """
    Returns a list of options from a python object string

    args:
        obj_str: python object path expamle
                    "rdfframework.connections.ConnManager[{param1}]"

    kwargs:
        * kwargs used to format the 'obj_str'
    """
    obj = get_obj_frm_str(obj_str, **kwargs)
    if obj:
        return list(obj)
    return []

def get_obj_frm_str(obj_str, **kwargs):
    """
    Returns a python object from a python object string

    args:
        obj_str: python object path expamle
                    "rdfframework.connections.ConnManager[{param1}]"

    kwargs:
        * kwargs used to format the 'obj_str'
    """
    obj_str = obj_str.format(**kwargs)
    args = []
    kwargs = {}
    params = []
    # parse the call portion of the string
    if "(" in obj_str:
        call_args = obj_str[obj_str.find("("):]
        obj_str = obj_str[:obj_str.find("(")]
        call_args = call_args[1:-1]
        if call_args:
            call_args = call_args.split(",")
        else:
            call_args = []
        call_args = [arg.strip() for arg in call_args]

        for arg in call_args:
            if "=" in arg:
                parts = arg.split("=")
                kwargs[parts[0]] = parts[1]
            else:
                args.append(arg)
    # parse a the __getitem__ portion of the string
    if "[" in obj_str:
        params = obj_str[obj_str.find("["):]
        obj_str = obj_str[:obj_str.find("[")]
        params = [part.replace("[", "").replace("]", "")
                  for part in params.split("][")]
    obj = pydoc.locate(obj_str)
    if params:
        for part in params:
            obj = get_attr(obj, part)
    if args or kwargs:
        if kwargs:
            obj = obj.__call__(*args, **kwargs)
        else:
            obj = obj.__call__(*args)
    return obj

def strip_errors(obj):
    """
    Reads through and error object and replaces the error dict with the
    value

    args:
        obj: the error object/dictionary
    """
    rtn_obj = copy.deepcopy(obj)
    try:
        del rtn_obj["__error_keys__"]
    except KeyError:
        pass
    for key in obj.get('__error_keys__', []):
        rtn_obj[key] = rtn_obj[key]['value']
    return rtn_obj


# class ConfigReq():
#     """ a requirement for a configuration attribute

#     args:
#         name: the name of the requirement
#         requirement: the requirement dictionary
#         kw_req: a kwarg requirement arguement *optional
#     """
#     def __init__(self, name, requirement, kw_req=None, **kwargs):
#         self.attr_name = name
#         self.__merge_req__(requirement, kw_req, **kwargs)


#     def __merge_req__(self, requirement, kw_req=None, **kwargs):
#         """ merges a requirement with a passed in kwarg requirement """
#         new_req = copy.deepcopy(requirement)
#         if kw_req:
#             requirement.update(kw_req)
#         self.req_def = requirement

#     def validate(self, value):
#         pass
