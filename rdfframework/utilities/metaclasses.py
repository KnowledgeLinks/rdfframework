import pdb
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
