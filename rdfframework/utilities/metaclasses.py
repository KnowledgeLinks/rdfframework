import pdb

class KeyRegistryMeta(type):
    """ Registry metaclass for a 'key' lookup specified as an attribute of a
    class inheriting from the base class using this metaclass

    Calling the base class by baseclase[key] will return the inherited class
    that is specified by the 'key'

    The base class needs to have defined a class attribute of


    __registry__

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
                options = getattr(reg_cls, name)
                if not isinstance(options, (set, list)):
                    raise TypeError("'%s' must be a set or list" % name)
                return set(getattr(reg_cls, name))
            except AttributeError:
                # if the reg_cls does not have the set of attibutes listed
                # attempt to create a list of keys if force is passed as true
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

        cls = super(KeyRegistryMeta, meta).__new__(meta,
                                                        name,
                                                        bases,
                                                        class_dict)
        reg_cls = [base for base in cls.__bases__
                   if base not in [object, str, int]]
        try:
            reg_cls = reg_cls[-1]
            if hasattr(reg_cls, "__reg_cls__"):
                reg_cls = reg_cls.__reg_cls__
        except IndexError:
            # if there are now classes use the current class as the
            # class for registration
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

        cls_attrs = set(dir(cls))
        cls_attrs.add("__name__")
        if (req_attrs - cls_attrs):
            raise AttributeError("'%s' is missing these required class attributes %s" \
                    % (cls, req_attrs - cls_attrs))
        # nested attributes should be removed from required attrs so that
        # they do not error out since we expect a mulitple classes using the
        # same nested value
        nested_attrs = set()
        if hasattr(reg_cls, "__nested_idx_attrs__"):
            nested_attrs = set(reg_cls.__nested_idx_attrs__)
        req_attrs -= nested_attrs
        attr_vals = set([getattr(cls, attr) \
                         for attr in req_attrs.union(opt_attrs) \
                         if hasattr(cls, attr)])
                         #if cls.__dict__.get(attr)])

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
        reg_vals = []
        for attr in req_attrs.union(opt_attrs):
            if hasattr(cls, attr):
                attr_val = getattr(cls, attr)
                registry[attr_val] = cls
                reg_vals.append(attr_val)
        if hasattr(reg_cls, "__special_idx_attrs__"):
            for spec_attr in reg_cls.__special_idx_attrs__:
                for key, value in spec_attr.items():
                    if hasattr(cls, key):
                        for item in value:
                            val = getattr(getattr(cls, key), item)
                            registry[val] = cls
                            reg_vals.append(val)
        for attr in nested_attrs:
            if hasattr(cls, attr):
                attr_val = getattr(cls, attr)
                if not registry.get(attr_val):
                    registry[attr_val] = {}
                for val in reg_vals:
                    registry[attr_val][val] = cls
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

    def __iter__(cls):
        if cls != cls.__reg_cls__:
            raise TypeError("'%s' object is not iterable" % cls)
        return iter(cls.__registry__)

    def keys(cls):
        if cls == cls.__reg_cls__:
            return cls.__registry__.keys()
        raise AttributeError("%s has not attribute 'keys'" % cls)

    def values(cls):
        if cls == cls.__reg_cls__:
            return cls.__registry__.values()
        raise AttributeError("%s has not attribute 'values'" % cls)

    @property
    def nested(cls):
        if cls == cls.__reg_cls__:
            return {key: value for key, value in cls.__registry__.items()
                    if isinstance(value, dict)}
        raise AttributeError("%s has not attribute 'nested'" % cls)

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

class PerformanceMeta(type):
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

class RegInstanceMeta(KeyRegistryMeta, InstanceCheckMeta):
    pass

class RegPerformInstanceMeta(PerformanceMeta, RegInstanceMeta):
    pass
