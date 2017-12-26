import pdb

class DatatypeRegistryMeta(type):
    """ Registry metaclass for a 'key' lookup specified as an attribute of a
    class inheriting from the base class using this metaclass

    Calling the base class by baseclase[key] will return the inherited class
    that is specified by the 'key'

    The base class needs to have defined a class attribute of

    _registry

    """
    def __new__(meta, name, bases, class_dict):
        def __get_idx_attrs__(cls, reg_cls, name, force=False):
            """ get the list of attrs that should be used as an index in the
            registry

            args:
                cls: the new class
                name: the attribute name storing the list of attributes names
                force: for the creation of the attribute 'name' if it is not
                       found
            """
            def hashable(value):
                """Determine whether `value` can be hashed."""
                try:
                    hash(value)
                except TypeError:
                    return False
                return True

            try:
                return getattr(reg_cls, name)
            except AttributeError:
                if force:
                    # select all attribute namees that are non callable and
                    # that are not reserved attributes
                    options = [attr for attr in dir(cls)
                               if not attr.startswith("__")
                               and not callable(getattr(cls, attr))
                               and type(getattr(cls, attr)) != property
                               and hashable(getattr(cls, attr))]
                    setattr(reg_cls, name, set(options))
                    return set(options)
                else:
                    return set()
        # pdb.set_trace()
        cls = super(DatatypeRegistryMeta, meta).__new__(meta,
                                                        name,
                                                        bases,
                                                        class_dict)
        reg_cls = [base for base in cls.__bases__ \
                       if base not in [object, str, int]]
        try:
            reg_cls = reg_cls[-1]
        except IndexError:
            cls.__reg_cls__ = cls
            reg_cls = cls
        if cls == reg_cls:
            if not hasattr(reg_cls, "__registry__"):
                cls.__registry__ = {}
            return cls
        # get all of the attributes that should be used as registry indexes
        req_attrs = __get_idx_attrs__(cls,
                                      reg_cls,
                                      '__required_idx_attrs__',
                                      True)
        if not req_attrs:
            err_msg = " ".join( ["Unable to determine what attributes should",
                                 "be used as registry indexes. Specify a class",
                                 "attribute '__required_idx_attrs__' as a",
                                 "set() of attribute names in",
                                 "class '%s'" % cls.__bases__[-1]])
            raise AttributeError(err_msg)
        opt_attrs = __get_idx_attrs__(cls,
                                      reg_cls,
                                      '__optional_idx_attrs__')

        cls_attrs = set(cls.__dict__)
        if (req_attrs - cls_attrs):
            raise AttributeError("'%s' is missing these required class attributes %s" \
                    % (cls, req_attrs - cls_attrs))
        attr_vals = set([getattr(cls, attr) \
                         for attr in req_attrs.union(opt_attrs) \
                         if cls.__dict__.get(attr)])
        registry = reg_cls.__registry__
        registered = [attr_val for attr_val in attr_vals \
                      if registry.get(attr_val)]
        if hasattr(reg_cls, "__special_idx_attrs__"):
            for spec_attr in reg_cls.__special_idx_attrs__:
                for key, value in spec_attr.items():
                    if hasattr(cls, key):
                        for item in value:
                            if registry.get(getattr(getattr(cls, key), item)):
                                registered.append(getattr(getattr(cls, key),
                                                          item))
        if registered:
            err_msg = " ".join(["'%s' is trying to register these" % cls,
                                "indexes that have already been assigned:\n"])
            err_items = ["idx '%s' in class '%s'" % (item, registry[item]) \
                         for item in registered]
            raise LookupError(err_msg + "\n".join(err_items))
        for attr in req_attrs.union(opt_attrs):
            if hasattr(cls, attr):
                attr_val = getattr(cls, attr)
                registry[attr_val] = cls
        if hasattr(reg_cls, "__special_idx_attrs__"):
            for spec_attr in reg_cls.__special_idx_attrs__:
                for key, value in spec_attr.items():
                    if hasattr(cls, key):
                        for item in value:
                            registry[getattr(getattr(cls, key), item)] = cls

        # for xsd_class in xsd_class_list:
        #     attr_list = ["type", "py_type", "class_type"]
        #     for attr in attr_list:
        #         if hasattr(xsd_class, attr):
        #             DT_LOOKUP[getattr(xsd_class, attr)] = xsd_class
        #         elif hasattr(xsd_class, '__wrapped__') and \
        #                 hasattr(xsd_class.__wrapped__, attr):
        #             DT_LOOKUP[getattr(xsd_class.__wrapped__, attr)] = xsd_class
        #     if hasattr(xsd_class, "datatype"):
        #         DT_LOOKUP[xsd_class.datatype.sparql] = xsd_class
        #         DT_LOOKUP[xsd_class.datatype.sparql_uri] = xsd_class
        #         DT_LOOKUP[xsd_class.datatype.pyuri] = xsd_class
        #         DT_LOOKUP[xsd_class.datatype.clean_uri] = xsd_class
        #         DT_LOOKUP[xsd_class.datatype] = xsd_class
        #     DT_LOOKUP[xsd_class] = xsd_class
        if not '__registry__' in cls.__dict__:
            cls.__registry__ = None
        return cls

    def __getitem__(cls, key):
        if cls != cls.__reg_cls__:
            raise TypeError("'%s' object is not subscriptable" % cls)
        try:
            return cls.__registry__[key]
        except KeyError:
            raise KeyError("key '%s' has no associated class" % key)
        # except AttributeError:
        #     try:
        #         return cls.__registry__[key]
        #     except KeyError:
        #         raise LookupError("key '%s' has no associated class" % key)

    def keys(cls):
        if cls.__bases__[0] == object:
            return cls.__registry__.keys()
        raise AttributeError("%s has not attribute 'keys'" % cls)

    def values(cls):
        if cls.__bases__[0] == object:
            return cls.__registry__.values()
        raise AttributeError("%s has not attribute 'values'" % cls)


class InstanceCheckMeta(type):
    """ metaclass to check to see if the arg is an instance of the class.

    returns: the arg if is an instance or calls the class
    """
    def __call__(cls, *args, **kwargs):
        # if the argument is already an instance of the cls return the
        # argument without instanctiating a new instance
        # pdb.set_trace()
        try:
            if isinstance(args[0], cls):
                return args[0]
        except IndexError:
            pass
        # pdb.set_trace()
        return super(InstanceCheckMeta, cls).__call__(*args, **kwargs)

class PerformanceMeta(InstanceCheckMeta):
    """ metaclass to remove property attributes so that they can be set during
        class instanciation.

    returns: the arg if is an instance or calls the class
    """
    # def __call__(cls, *args, **kwargs):
    #     super(PerformanceMeta, cls).__call__(*args, **kwargs)

    def __new__(mcs, cls, bases, clsdict, **kwds):
        # if performance mode is set rename the performace attributes
        # and break the inheritance of those attributes so that they can be
        # assigned during instanciation
        if clsdict.get('performance_mode', False):
            for attr in clsdict['performance_attrs']:
                try:
                    clsdict["__%s__" % attr] = clsdict.pop(attr)
                except KeyError:
                    pass
                clsdict[attr] = None
        return super(PerformanceMeta, mcs).__new__(mcs, cls, bases, clsdict)

class KeyRegistryMeta(type):
    """ Registry metaclass for a 'key' lookup specified as an attribute of a
    class inheriting from the base class using this metaclass

    Calling the base class by baseclase[key] will return the inherited class
    that is specified by the 'key'

    The base class needs to have defined a class attribute of

    _registry

    """
    def __new__(meta, name, bases, class_dict):
        cls = super(KeyRegistryMeta, meta).__new__(meta, name, bases, class_dict)

        if not bases:
            if not hasattr(cls, "__registry__"):
                cls.__registry__ = {}
                # raise AttributeError("base class '%s' requires a class attribute called '_registry' used to lookup registered keys" % \
                #                      name)
            return cls
        if not hasattr(cls, "key"):
            raise AttributeError("define 'key' at class level for your processor")
        elif cls.__bases__[-1].__registry__.get(cls.key):
            raise AttributeError("'key' has already been used with class %s" %
                                 cls.__bases__[-1].__registry__.get(cls.key))
        cls.__bases__[-1].__registry__[cls.key] = cls
        if not '__registry__' in cls.__dict__:
            cls.__registry__ = None
        return cls

    def __getitem__(cls, key):
        if cls.__bases__[0] != object:
            raise TypeError("'%s' object is not subscriptable" % cls)
        try:
            return cls.__bases__[-1].__registry__[key]
        except KeyError:
            raise LookupError("key '%s' has no associated class" % key)
        except AttributeError:
            try:
                return cls.__registry__[key]
            except KeyError:
                raise LookupError("key '%s' has no associated class" % key)

    def keys(cls):
        if cls.__bases__[0] == object:
            return cls.__registry__.keys()
        raise AttributeError("%s has not attribute 'keys'" % cls)

    def values(cls):
        if cls.__bases__[0] == object:
            return cls.__registry__.values()
        raise AttributeError("%s has not attribute 'values'" % cls)

class TestMeta(DatatypeRegistryMeta, InstanceCheckMeta):
    pass

class TestMeta2(PerformanceMeta, TestMeta):
    pass
