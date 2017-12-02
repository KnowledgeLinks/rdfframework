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
