import pdb
# class Meta(type):
#     @classmethod
#     def __prepare__(mcs, name, bases, **kwargs):
#         print('  Meta.__prepare__(\n\t\tmcs=%s,\n\t\tname=%r,\n\t\tbases=%s,\n\t\t**%s)' % (
#             mcs, name, bases, kwargs
#         ))
#         def test_conv(self, name, value):
#             setattr(self, name, value)
#         return {} #{'prep_test':1, 'next_prep':2, 'prep_func': test_conv}

#     def __new__(mcs, name, bases, attrs, **kwargs):
#         print('  Meta.__new__(\n\t\tmcs=%s,\n\t\tname=%r,\n\t\tbases=%s,\n\t\tattrs=[%s],\n\t\t**%s)' % (
#             mcs, name, bases, ', '.join(attrs), kwargs
#         ))
#         # return super().__new__(mcs, name, bases, attrs)
#         return super(Meta, mcs).__new__(mcs, name, bases, attrs)

#     def __init__(cls, name, bases, attrs, **kwargs):
#         print('  Meta.__init__(\n\t\tcls=%s,\n\t\tname=%r,\n\t\tbases=%s,\n\t\tattrs=[%s],\n\t\t**%s)' % (
#             cls, name, bases, ', '.join(attrs), kwargs
#         ))
#         return super().__init__(name, bases, attrs)

#     def __call__(cls, *args, **kwargs):
#         print('  Meta.__call__(\n\t\tcls=%s,\n\t\targs=%s,\n\t\tkwargs=%s)' % (
#             cls, args, kwargs
#         ))
#         return super().__call__(*args, **kwargs)

# class Class(metaclass=Meta, extra=1):
#     def __new__(cls, ):
#         print('  Class.__new__(\n\t\tcls=%s,\n\t\tmyarg=%s)' % (
#             cls, myarg
#         ))
#         return super().__new__(cls)

#     def __init__(self, myarg):
#         print('  Class.__init__(self=%s,\n\t\tmyarg=%s)' % (
#             self, myarg
#         ))
#         self.myarg = myarg
#         return super().__init__()

#     def __str__(self):
#         return "<instance of Class; myargs=%s>" % (
#             getattr(self, 'myarg', 'MISSING'),
#         )
from rdfframework.utilities import RdfConfigManager
CFG = RdfConfigManager()

def p_args(args, kwargs={}):
    return "\n\t\t".join(["args[%s] = %s" % (i, v) for i, v in enumerate(args)]) + \
           "\n\t\tkwargs = %s" % kwargs

class Meta(type):
    @classmethod
    def __prepare__(*args, **kwargs):
        print('  Meta.__prepare__(\n\t\t%s)' % (p_args(args, kwargs)))
        # pdb.set_trace()
        return CFG.rdf_class_defs.get(args[1],{})
#{'prep_test':1, 'next_prep':2, 'prep_func': test_conv}

    def __new__(*args, **kwargs):
        print('  Meta.__new__(\n\t\t%s)' % (p_args(args, kwargs)))
        # return super().__new__(mcs, name, bases, attrs)
        return super(Meta, args[0]).__new__(*args)

    # def __init__(cls, name, bases, attrs, **kwargs):
    def __init__(*args, **kwargs):
        print('  Meta.__init__(\n\t\t%s)' % (p_args(args, kwargs)))
        return super(Meta, args[0]).__init__(args[1:])

    def __call__(cls, *args, **kwargs):
        print('  Meta.__call__(\n\t\t%s)' % (p_args(args, kwargs)))
        return super().__call__(*args, **kwargs)

class Class(metaclass=Meta, extra=1):
    def __new__(cls, *args, **kwargs ):
        print('  Class.__new__(\n\t\t%s)' % (p_args(args, kwargs)))
        return super().__new__(cls)

    def __init__(self, test, **kwargs):
        print('  Class.__init__(\n\t\t%s)' % (p_args((test,), kwargs)))
        return super().__init__()


# from pprint import pprint

# class Tag1: pass
# class Tag2: pass
# class Tag3:
#     def tag3_method(self): pass

# class MetaBase(type):
#     def __new__(mcl, name, bases, nmspc):
#         print('MetaBase.__new__\n')
#         return super(MetaBase, mcl).__new__(mcl, name, bases, nmspc)

#     def __init__(cls, name, bases, nmspc):
#         print('MetaBase.__init__\n')
#         super(MetaBase, cls).__init__(name, bases, nmspc)

# class MetaNewVSInit(MetaBase):
#     def __new__(mcl, name, bases, nmspc):
#         # First argument is the metaclass ``MetaNewVSInit``
#         print('MetaNewVSInit.__new__')
#         for x in (mcl, name, bases, nmspc): pprint(x)
#         print('')
#         # These all work because the class hasn't been created yet:
#         if 'foo' in nmspc: nmspc.pop('foo')
#         name += '_x'
#         bases += (Tag1,)
#         nmspc['baz'] = 42
#         return super(MetaNewVSInit, mcl).__new__(mcl, name, bases, nmspc)

#     def __init__(cls, name, bases, nmspc):
#         # First argument is the class being initialized
#         print('MetaNewVSInit.__init__')
#         for x in (cls, name, bases, nmspc): pprint(x)
#         print('')
#         if 'bar' in nmspc: nmspc.pop('bar') # No effect
#         name += '_y' # No effect
#         bases += (Tag2,) # No effect
#         nmspc['pi'] = 3.14159 # No effect
#         super(MetaNewVSInit, cls).__init__(name, bases, nmspc)
#         # These do work because they operate on the class object:
#         cls.__name__ += '_z'
#         cls.__bases__ += (Tag3,)
#         cls.e = 2.718

# class Test(object, metatclass=MetaNewVSInit):
#     def __init__(self):
#         print('Test.__init__')
#     def foo(self): print('foo still here')
#     def bar(self): print('bar still here')

# t = Test()
# print('class name: ' + Test.__name__)
# print('base classes: ', [c.__name__ for c in Test.__bases__])
# print([m for m in dir(t) if not m.startswith("__")])
# t.bar()
# print(t.e)